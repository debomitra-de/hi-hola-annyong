"""
Usage:
    python scripts/test_pdf_quiz.py path/to/book.pdf

"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from books.ingest import ingest_book, list_chapters, process_chapter
from books.quiz import generate_quiz
from memory.database import Database

if len(sys.argv) < 2:
    print("Usage: python scripts/test_pdf_quiz.py <path_to_pdf>")
    sys.exit(1)

pdf_path = sys.argv[1]
db = Database()

print(f"Ingesting {pdf_path} ...")
book_id = ingest_book(pdf_path, db)
print(f"Book ID: {book_id}")

chapters = list_chapters(book_id, db)
if not chapters:
    print("No chapters found.")
    sys.exit(1)

print("\nChapters found:")
for ch in chapters:
    print(f"  [{ch['id']}] {ch['title']}  (pages {ch['page_start']}–{ch['page_end']}, {ch['word_count']} words)")

raw = input("\nEnter chapter ID to quiz: ").strip()
chapter_id = int(raw)

print("Processing chapter (extracting text + vocab) ...")
chapter = process_chapter(chapter_id, db)
print(f"  {chapter['word_count']} words, cached: {'yes' if chapter['processed_at'] else 'no'}")

print("\nGenerating quiz questions via Ollama ...")
questions = generate_quiz(chapter["cleaned_text"], n_questions=5)

if not questions:
    print("No questions returned. Is Ollama running with qwen2.5:7b?")
    sys.exit(1)

print(f"\n--- Quiz: {chapter['title']} ---\n")
for i, q in enumerate(questions, 1):
    print(f"Q{i} [{q.get('type', '?')}]: {q.get('question', '')}")
    input("  Press Enter to see answer ...")
    print(f"  Answer: {q.get('answer', '')}\n")

db.update_chapter_progress(chapter_id, mastery_delta=0.1)
print("Progress saved.")
