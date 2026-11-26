"""Tests for api.py FastAPI endpoints."""

import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api
from api import app
from memory.database import Database


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db = Database(db_path=str(tmp_path / "test.db"))
    monkeypatch.setattr(api, "_db", db)
    return db


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


def test_create_session(client):
    resp = client.post("/sessions", json={"source_type": "topic", "source_ref": "greetings", "level": "A1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] >= 1
    assert data["level"] == "A1"


def test_create_session_bad_level(client):
    resp = client.post("/sessions", json={"source_type": "topic", "source_ref": "x", "level": "C2"})
    assert resp.status_code == 422


def test_checkpoint_404_for_missing(client):
    resp = client.get("/sessions/9999/checkpoint")
    assert resp.status_code == 404


def test_checkpoint_roundtrip(client):
    sid_resp = client.post("/sessions", json={"source_type": "topic", "source_ref": "foo", "level": "A1"})
    sid = sid_resp.json()["session_id"]

    plan_resp = client.post(f"/sessions/{sid}/plan", params={"source_text": "food", "level": "A1"})
    assert plan_resp.status_code == 200

    ckpt = client.get(f"/sessions/{sid}/checkpoint")
    assert ckpt.status_code == 200
    assert ckpt.json()["session_id"] == sid


# ---------------------------------------------------------------------------
# Text turn
# ---------------------------------------------------------------------------


def test_text_turn(client, monkeypatch):
    monkeypatch.setenv("TUTOR_ADAPTER_MODE", "fake")
    sid = client.post("/sessions", json={"source_type": "topic", "source_ref": "food", "level": "A1"}).json()["session_id"]

    resp = client.post(
        f"/sessions/{sid}/turns/text",
        json={"session_id": sid, "learner_text": "Hola", "level": "A1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["learner_text"] == "Hola"
    assert data["tutor_message"]["es"]
    assert data["tutor_message"]["en"]


def test_text_turn_empty_text(client):
    sid = client.post("/sessions", json={"source_type": "topic", "source_ref": "food", "level": "A1"}).json()["session_id"]
    resp = client.post(
        f"/sessions/{sid}/turns/text",
        json={"session_id": sid, "learner_text": "   ", "level": "A1"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Voice turn
# ---------------------------------------------------------------------------


def test_voice_turn(client, monkeypatch):
    monkeypatch.setenv("TUTOR_ADAPTER_MODE", "fake")
    sid = client.post("/sessions", json={"source_type": "topic", "source_ref": "food", "level": "A1"}).json()["session_id"]

    resp = client.post(
        f"/sessions/{sid}/turns/voice",
        files={"audio": ("audio.wav", b"fake_wav_bytes", "audio/wav")},
        params={"level": "A1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["learner_text"]
    assert data["audio_b64"]  # base64 encoded
    import base64
    assert base64.b64decode(data["audio_b64"])  # decodable


# ---------------------------------------------------------------------------
# Placement test
# ---------------------------------------------------------------------------


def test_placement_full_flow(client):
    start = client.post("/placement/start").json()
    pid = start["placement_id"]
    assert start["question"]

    result = None
    for _ in range(5):
        resp = client.post(f"/placement/{pid}/answer", json={"answer": "soy de madrid"})
        result = resp.json()

    assert result["complete"] is True
    assert result["level"] in {"A1", "A2", "B1"}


def test_placement_404_bad_id(client):
    resp = client.post("/placement/nonexistent/answer", json={"answer": "hola"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Lesson planning
# ---------------------------------------------------------------------------


def test_plan_lesson(client, monkeypatch):
    monkeypatch.setenv("TUTOR_ADAPTER_MODE", "fake")
    sid = client.post("/sessions", json={"source_type": "topic", "source_ref": "food", "level": "A1"}).json()["session_id"]

    resp = client.post(f"/sessions/{sid}/plan", params={"source_text": "food", "level": "A1"})
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["level"] == "A1"
    assert plan["conversation_goals"]


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------


def test_upload_non_pdf(client):
    resp = client.post(
        "/books",
        files={"file": ("notes.txt", b"some text", "text/plain")},
    )
    assert resp.status_code == 422


def test_upload_and_list_chapters(client, tmp_path, fresh_db):
    import pymupdf

    pdf_path = tmp_path / "spanish.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Chapter 1 - Hola")
    page.insert_text((72, 96), "Hola amigo. Vamos a aprender.")
    doc.set_toc([[1, "Chapter 1 - Hola", 1]])
    doc.save(str(pdf_path))
    doc.close()

    pdf_bytes = pdf_path.read_bytes()
    resp = client.post(
        "/books",
        files={"file": ("spanish.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200
    book_id = resp.json()["book_id"]

    Path(fresh_db.get_book(book_id)["stored_path"]).unlink()
    reupload = client.post(
        "/books",
        files={"file": ("spanish.pdf", pdf_bytes, "application/pdf")},
    )
    assert reupload.status_code == 200
    assert reupload.json()["book_id"] == book_id

    chapters = client.get(f"/books/{book_id}/chapters").json()
    assert isinstance(chapters, list)
    assert len(chapters) >= 1
    processed = client.post(f"/chapters/{chapters[0]['id']}/process")
    assert processed.status_code == 200
    assert "Hola amigo" in processed.json()["cleaned_text"]


def test_get_chapters_404_unknown_book(client):
    resp = client.get("/books/9999/chapters")
    assert resp.status_code == 404


def test_generating_session_quiz_fallback_is_spanish(client, fresh_db, monkeypatch):
    session_id = fresh_db.create_session(
        source_type="topic",
        source_ref="normal conversation",
        level="A1",
    )
    monkeypatch.setitem(api._quiz_cache, session_id, None)

    questions = client.get(f"/sessions/{session_id}/quiz").json()

    assert all(question["question"].startswith("¿") for question in questions)


# ---------------------------------------------------------------------------
# Vocabulary / spaced repetition
# ---------------------------------------------------------------------------


def test_vocabulary_add_and_due(client):
    resp = client.post(
        "/vocabulary",
        json={"lemma": "hablar", "surface": "hablar", "kind": "word", "gloss_en": "to speak", "source": "topic"},
    )
    assert resp.status_code == 200
    item_id = resp.json()["item_id"]

    due = client.get("/vocabulary/due").json()
    assert any(item["id"] == item_id for item in due)


def test_vocabulary_bad_kind(client):
    resp = client.post(
        "/vocabulary",
        json={"lemma": "x", "surface": "x", "kind": "emoji", "gloss_en": "x", "source": "topic"},
    )
    assert resp.status_code == 422


def test_vocab_result_correct(client):
    item_id = client.post(
        "/vocabulary",
        json={"lemma": "comer", "surface": "comer", "kind": "word", "gloss_en": "to eat", "source": "topic"},
    ).json()["item_id"]

    resp = client.post(f"/vocabulary/{item_id}/result", params={"correct": "true"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Quiz evaluation
# ---------------------------------------------------------------------------


def test_quiz_evaluate_correct(client):
    resp = client.post(
        "/quiz/evaluate",
        json={"question": "¿Qué es hablar?", "user_answer": "to speak", "correct_answer": "To Speak"},
    )
    assert resp.status_code == 200
    assert resp.json()["correct"] is True


def test_quiz_evaluate_incorrect(client):
    resp = client.post(
        "/quiz/evaluate",
        json={"question": "¿Qué es hablar?", "user_answer": "to run", "correct_answer": "to speak"},
    )
    assert resp.json()["correct"] is False


# ---------------------------------------------------------------------------
# Pronunciation score
# ---------------------------------------------------------------------------


def test_pronunciation_score_disabled(client):
    resp = client.post(
        "/pronunciation/score",
        files={"audio": ("a.wav", b"fake", "audio/wav")},
        data={"target_text": "hola"},
    )
    assert resp.status_code == 200
    assert resp.json()["score"] is None  # PRONUNCIATION_ENABLED=False by default


def test_pronunciation_missing_target(client):
    resp = client.post(
        "/pronunciation/score",
        files={"audio": ("a.wav", b"fake", "audio/wav")},
    )
    assert resp.status_code == 422
