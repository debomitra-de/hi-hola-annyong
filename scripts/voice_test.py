"""End-to-end voice test: pick a chapter → tutor teaches it → optional quiz."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["TUTOR_ADAPTER_MODE"] = "real"

import interfaces
from audio.pipeline import play_wav
from books.ingest import ingest_book, list_chapters, process_chapter
from books.quiz import generate_quiz
from memory.database import Database

LEVEL = "A1"
VOICE = "ef_dora"
PDF_PATH = "scripts/spanish_dummy.pdf"
DB_PATH = "data/tutor.db"


import threading

def speak_then_print(es: str, en: str) -> None:
    """Speak the bilingual sentence, show it as caption."""
    wav = interfaces.speak(es, VOICE)
    threading.Thread(target=play_wav, args=(wav,), daemon=True).start()
    print(f"Hernando : {es}")
    if en:
        print(f"          ({en})")
    print()


def pick_chapter(db: Database) -> str:
    book_id = ingest_book(PDF_PATH, db)
    chapters = list_chapters(book_id, db)
    print("\nAvailable chapters:")
    for ch in chapters:
        print(f"  [{ch['id']}] {ch['title']}")
    chapter_id = int(input("\nEnter chapter id: ").strip())
    chapter = process_chapter(chapter_id, db)
    return chapter.get("cleaned_text") or ""


def main() -> None:
    db = Database(db_path=DB_PATH)
    chapter_text = pick_chapter(db)

    print("\nSetting up tutor (first run downloads models — may take a few minutes)...")
    interfaces.configure_conversation(mode="real", level=LEVEL, chapter_text=chapter_text)

    print("\n=== Spanish Voice Tutor — Chapter lesson starting ===\n")
    opener = interfaces.generate_tutor_response("start")
    if opener["es"]:
        speak_then_print(opener["es"], opener["en"])

    print("Press ENTER to speak, ENTER again to stop. Type 'quiz' for a quiz. Ctrl+C to quit.\n")

    while True:
        cmd = input("[ ENTER to speak  |  'quiz' for quiz ] ").strip().lower()

        if cmd == "quiz":
            print("Generating quiz...\n")
            questions = generate_quiz(chapter_text, n_questions=3, level=LEVEL)
            if not questions:
                print("Could not generate quiz (is Ollama running?).\n")
                continue
            score = 0
            for i, q in enumerate(questions, 1):
                print(f"Q{i}: {q['question']}")
                answer = input("Your answer: ").strip()
                if answer.casefold() == q["answer"].strip().casefold():
                    print("Correct!\n")
                    score += 1
                else:
                    print(f"Answer: {q['answer']}\n")
            print(f"Score: {score}/{len(questions)}\n")
            continue

        print("Recording... press ENTER to stop.")
        interfaces.start_voice_answer()
        input()

        print("Processing...")
        result = interfaces.stop_voice_answer(level=LEVEL, voice=VOICE, play_response=False)

        if not result["learner_text"]:
            print("(no audio detected)\n")
            continue

        print(f"\nYou    : {result['learner_text']}")

        if result.get("unclear"):
            # play the clarification audio (slow word), then show caption
            if result["response_wav"]:
                threading.Thread(target=play_wav, args=(result["response_wav"],), daemon=True).start()
            msg = result["tutor_message"]
            if msg["es"]:
                print(f"Hernando : {msg['es']}")
            print(f"          ({msg['en']})\n")
        else:
            speak_then_print(result["tutor_message"]["es"], result["tutor_message"]["en"])


if __name__ == "__main__":
    main()
