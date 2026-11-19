import hashlib

import pymupdf
import pytest

from books.ingest import (
    PdfIngestionError,
    ingest_book,
    list_chapters,
    process_chapter,
)
from memory.database import Database


@pytest.fixture
def db(tmp_path):
    return Database(db_path=str(tmp_path / "test_tutor.db"))


def _create_text_pdf(path, toc=False):
    doc = pymupdf.open()
    first = doc.new_page()
    first.insert_text((72, 72), "Chapter 1 - Hola")
    first.insert_text((72, 96), "Hola amigo. Vamos a aprender español.")
    second = doc.new_page()
    second.insert_text((72, 72), "Chapter 2 - Viaje")
    second.insert_text((72, 96), "Quiero reservar una mesa.")
    if toc:
        doc.set_toc([
            [1, "Chapter 1 - Hola", 1],
            [1, "Chapter 2 - Viaje", 2],
        ])
    doc.save(path)
    doc.close()


def test_hash_dedupe_and_chapter_listing(tmp_path, db):
    pdf_path = tmp_path / "spanish.pdf"
    _create_text_pdf(pdf_path, toc=True)

    first_id = ingest_book(str(pdf_path), db)
    second_id = ingest_book(str(pdf_path), db)

    assert first_id == second_id
    chapters = list_chapters(first_id, db)
    assert [chapter["title"] for chapter in chapters] == [
        "Chapter 1 - Hola",
        "Chapter 2 - Viaje",
    ]
    assert sum(1 for _ in chapters) == 2


def test_process_chapter_is_cached(tmp_path, db):
    pdf_path = tmp_path / "spanish.pdf"
    _create_text_pdf(pdf_path, toc=True)
    book_id = ingest_book(str(pdf_path), db)
    chapter = list_chapters(book_id, db)[0]

    processed = process_chapter(chapter["id"], db)
    processed_again = process_chapter(chapter["id"], db)

    assert processed["processed_at"]
    assert processed_again["processed_at"] == processed["processed_at"]
    assert "Hola" in processed["cleaned_text"]
    assert hashlib.sha256(pdf_path.read_bytes()).hexdigest()


def test_image_only_pdf_is_rejected(tmp_path, db):
    pdf_path = tmp_path / "scanned.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    with pytest.raises(PdfIngestionError, match="no readable text layer"):
        ingest_book(str(pdf_path), db)

    assert db.get_book_by_hash(hashlib.sha256(pdf_path.read_bytes()).hexdigest()) is None
