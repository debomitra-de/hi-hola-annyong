import hashlib
import json
import re
from pathlib import Path

import fitz  # PyMuPDF

from memory.database import Database


def _compute_hash(pdf_path: str) -> str:
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


_SKIP_TITLES = re.compile(
    r"^(introduction|introducción|conclusion|conclusión|translation|traducción|"
    r"preface|prefacio|foreword|index|índice|appendix|apéndice|about the author|"
    r"acknowledgements?)\b",
    re.IGNORECASE,
)


def _is_content_chapter(title: str) -> bool:
    return not _SKIP_TITLES.match(title.strip())


def _detect_chapters(doc: fitz.Document) -> list[dict]:
    """Detect chapters from PDF outline first, then heading patterns."""
    chapters = []

    toc = doc.get_toc()
    if toc:
        top_level = [(title, page) for level, title, page in toc if level == 1]
        for i, (title, page) in enumerate(top_level):
            end_page = top_level[i + 1][1] - 1 if i + 1 < len(top_level) else len(doc)
            chapters.append({"title": title, "page_start": page, "page_end": end_page})
        if chapters:
            return chapters

    # Fallback: scan first line of each page for chapter/unit headings
    heading_re = re.compile(r"^(chapter|capítulo|unit|unidad|lección)\s+\d+", re.IGNORECASE)
    for page_num in range(len(doc)):
        first_line = doc[page_num].get_text("text").strip().split("\n")[0].strip()
        if heading_re.match(first_line):
            chapters.append({"title": first_line, "page_start": page_num + 1, "page_end": page_num + 1})

    for i in range(len(chapters) - 1):
        chapters[i]["page_end"] = chapters[i + 1]["page_start"] - 1
    if chapters:
        chapters[-1]["page_end"] = len(doc)

    # Last resort: treat entire document as one chapter
    if not chapters:
        chapters = [{"title": Path(doc.name).stem, "page_start": 1, "page_end": len(doc)}]

    return chapters


def ingest_book(pdf_path: str, db: Database) -> int:
    """Hash the PDF, skip if already stored, index chapters. Returns book_id."""
    file_hash = _compute_hash(pdf_path)
    existing = db.get_book_by_hash(file_hash)
    if existing:
        return existing["id"]

    book_id = db.insert_book(
        file_hash=file_hash,
        original_filename=Path(pdf_path).name,
        stored_path=str(Path(pdf_path).resolve()),
    )

    doc = fitz.open(pdf_path)
    content_chapters = [ch for ch in _detect_chapters(doc) if _is_content_chapter(ch["title"])]
    for idx, ch in enumerate(content_chapters):
        text = "".join(
            doc[p].get_text("text")
            for p in range(ch["page_start"] - 1, min(ch["page_end"], len(doc)))
        )
        db.insert_chapter(
            book_id=book_id,
            index=idx,
            title=ch["title"],
            page_start=ch["page_start"],
            page_end=ch["page_end"],
            word_count=len(text.split()),
        )
    doc.close()
    return book_id


def list_chapters(book_id: int, db: Database) -> list[dict]:
    return db.get_chapters(book_id)


def process_chapter(chapter_id: int, db: Database) -> dict:
    """Extract and cache chapter text + vocab. Idempotent — returns cache on repeat calls."""
    chapter = db.get_chapter(chapter_id)
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")
    if chapter["processed_at"]:
        return chapter

    book = db.get_book(chapter["book_id"])
    doc = fitz.open(book["stored_path"])
    text = "".join(
        doc[p].get_text("text")
        for p in range(chapter["page_start"] - 1, min(chapter["page_end"], len(doc)))
    )
    doc.close()

    # Top-100 unique Spanish words (4+ chars) as vocab list
    words = re.findall(r"[a-záéíóúüñ]{4,}", text.lower())
    vocab = list(dict.fromkeys(words))[:100]

    db.update_chapter_processed(
        chapter_id=chapter_id,
        cleaned_text=text.strip(),
        vocab_json=json.dumps(vocab),
    )
    return db.get_chapter(chapter_id)
