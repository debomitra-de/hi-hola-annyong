"""End-to-end voice test: pick a chapter → tutor teaches it → optional quiz."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["TUTOR_ADAPTER_MODE"] = "real"

import interfaces
from books.ingest import ingest_book, list_chapters, process_chapter
from books.quiz import generate_quiz
from memory.database import Database

LEVEL = "A1"
VOICE = "ef_dora"
PDF_PATH = "scripts/spanish_dummy.pdf"
DB_PATH = "data/tutor.db"


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

    # Tutor speaks first
    print("\n=== Spanish Voice Tutor — Chapter lesson starting ===\n")
    opener = interfaces.generate_tutor_response("start")
    print(f"Tutor ES : {opener['es']}")
    print(f"Tutor EN : {opener['en']}")
    if opener["es"]:
        interfaces.speak(opener["es"], VOICE)
        from audio.pipeline import play_wav
        play_wav(interfaces.speak(opener["es"], VOICE))

    print("\nPress ENTER to speak, ENTER again to stop. Type 'quiz' for a quiz. Ctrl+C to quit.\n")

    turn = 0
    while True:
        cmd = input("[ Press ENTER to speak  |  type 'quiz' + ENTER for quiz ] ").strip().lower()

        if cmd == "quiz":
            if not chapter_text.strip():
                print("No chapter loaded — upload a PDF first.\n")
                continue
            print("Generating quiz from chapter...\n")
            questions = generate_quiz(chapter_text, n_questions=3, level=LEVEL)
            if not questions:
                print("Could not generate quiz (is Ollama running?).\n")
                continue
            score = 0
            for i, q in enumerate(questions, 1):
                print(f"Q{i}: {q['question']}")
                answer = input("Your answer: ").strip()
                correct = q["answer"].strip().casefold()
                if answer.strip().casefold() == correct:
                    print("✓ Correct!\n")
                    score += 1
                else:
                    print(f"✗ Correct answer: {q['answer']}\n")
            print(f"Score: {score}/{len(questions)}\n")
            continue

        print("Recording... press ENTER to stop.")
        interfaces.start_voice_answer()
        input()

        print("Processing...")
        result = interfaces.stop_voice_answer(level=LEVEL, voice=VOICE, play_response=True)

        if not result["learner_text"]:
            print("(no audio detected)\n")
            continue

        turn += 1
        print(f"\nYou said : {result['learner_text']}")
        print(f"Tutor ES : {result['tutor_message']['es']}")
        print(f"Tutor EN : {result['tutor_message']['en']}")
        print()


if __name__ == "__main__":
    main()
