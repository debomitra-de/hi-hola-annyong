"""FastAPI backend for Spanish Voice Tutor."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import interfaces
from books.ingest import PdfIngestionError, ingest_book, list_chapters, process_chapter
from books.quiz import generate_quiz
from memory.database import Database

app = FastAPI(title="Spanish Voice Tutor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_db: Database | None = None


def _get_db() -> Database:
    global _db
    if _db is None:
        db_path = os.getenv("TUTOR_DB_PATH", "data/tutor.db")
        _db = Database(db_path=db_path)
    return _db


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TextTurnRequest(BaseModel):
    session_id: int
    learner_text: str
    level: str = "A1"


class TextTurnResponse(BaseModel):
    learner_text: str
    tutor_message: dict[str, Any]


class VoiceTurnResponse(BaseModel):
    learner_text: str
    tutor_message: dict[str, Any]
    audio_b64: str  # base64-encoded WAV bytes for the tutor response
    stt_confidence: float | None


class SessionCreate(BaseModel):
    source_type: str = "topic"
    source_ref: str = "conversation"
    level: str = "A1"
    chapter_id: int | None = None  # if set, session is chapter-based


class SessionResponse(BaseModel):
    session_id: int
    source_type: str
    source_ref: str
    level: str


class PlacementAnswer(BaseModel):
    answer: str


class QuizAnswerRequest(BaseModel):
    question: str
    user_answer: str
    correct_answer: str


class LearnerItemCreate(BaseModel):
    lemma: str
    surface: str
    kind: str  # word | phrase | grammar
    gloss_en: str
    source: str = "topic"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


@app.post("/sessions", response_model=SessionResponse)
def create_session(body: SessionCreate) -> SessionResponse:
    db = _get_db()
    source_type = body.source_type
    source_ref = body.source_ref

    chapter_text = ""
    if body.chapter_id is not None:
        try:
            chapter = process_chapter(body.chapter_id, db)
        except (ValueError, Exception) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        chapter_text = chapter.get("cleaned_text") or ""
        source_type = "chapter"
        source_ref = str(body.chapter_id)

    try:
        sid = db.create_session(
            source_type=source_type,
            source_ref=source_ref,
            level=body.level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # store chapter_text in checkpoint so turns can reload it
    db.save_checkpoint(
        session_id=sid,
        current_turn=0,
        plan_json="{}",
        mode="lesson",
        state_data=json.dumps({"chapter_text": chapter_text, "level": body.level}),
    )

    # pre-configure the conversation engine with chapter context
    interfaces.configure_conversation(
        mode=interfaces.get_audio_adapter_mode(),
        level=body.level,
        chapter_text=chapter_text,
    )

    return SessionResponse(
        session_id=sid,
        source_type=source_type,
        source_ref=source_ref,
        level=body.level,
    )


@app.get("/sessions/{session_id}/checkpoint")
def get_checkpoint(session_id: int) -> dict:
    db = _get_db()
    state = db.load_checkpoint(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="No checkpoint found")
    return state


# ---------------------------------------------------------------------------
# Text conversation turn
# ---------------------------------------------------------------------------


def _chapter_text_for_session(session_id: int) -> str:
    """Load chapter_text from the session checkpoint's state_data."""
    ckpt = _get_db().load_checkpoint(session_id)
    if not ckpt:
        return ""
    try:
        return json.loads(ckpt.get("state_data") or "{}").get("chapter_text", "")
    except (json.JSONDecodeError, AttributeError):
        return ""


@app.post("/sessions/{session_id}/turns/text", response_model=TextTurnResponse)
def text_turn(session_id: int, body: TextTurnRequest) -> TextTurnResponse:
    if not body.learner_text.strip():
        raise HTTPException(status_code=422, detail="learner_text cannot be empty")

    interfaces.configure_conversation(
        mode=interfaces.get_audio_adapter_mode(),
        level=body.level,
        chapter_text=_chapter_text_for_session(session_id),
    )
    tutor_msg = interfaces.generate_tutor_response(body.learner_text)

    db = _get_db()
    db.record_turn(
        session_id=session_id,
        step=0,  # caller may supply step via query param if needed; 0 = auto
        exercise_json=json.dumps({"type": "text"}),
        answer_text=body.learner_text,
        stt_conf=None,
        correct=None,
        phoneme_json=None,
        feedback_json=json.dumps(tutor_msg),
    )

    return TextTurnResponse(learner_text=body.learner_text, tutor_message=tutor_msg)


# ---------------------------------------------------------------------------
# Voice conversation turn
# ---------------------------------------------------------------------------


@app.post("/sessions/{session_id}/turns/voice", response_model=VoiceTurnResponse)
async def voice_turn(session_id: int, audio: UploadFile = File(...), level: str = "A1") -> VoiceTurnResponse:
    wav = await audio.read()
    if not wav:
        raise HTTPException(status_code=422, detail="audio file is empty")

    interfaces.configure_conversation(
        mode=interfaces.get_audio_adapter_mode(),
        level=level,
        chapter_text=_chapter_text_for_session(session_id),
    )
    result = interfaces.process_voice_answer(wav, level=level, voice="ef_dora")

    stt_conf: float | None = None
    confs = result["transcript"].get("word_confidences", [])
    if confs:
        stt_conf = round(sum(confs) / len(confs), 4)

    db = _get_db()
    db.record_turn(
        session_id=session_id,
        step=0,
        exercise_json=json.dumps({"type": "voice"}),
        answer_text=result["learner_text"],
        stt_conf=stt_conf,
        correct=None,
        phoneme_json=None,
        feedback_json=json.dumps(result["tutor_message"]),
    )

    return VoiceTurnResponse(
        learner_text=result["learner_text"],
        tutor_message=result["tutor_message"],
        audio_b64=base64.b64encode(result["response_wav"]).decode(),
        stt_confidence=stt_conf,
    )


# ---------------------------------------------------------------------------
# Placement test
# ---------------------------------------------------------------------------

_placement_engines: dict[str, Any] = {}


@app.post("/placement/start")
def placement_start() -> dict:
    from tutor.lesson import PlacementEngine

    engine = PlacementEngine()
    import uuid

    placement_id = str(uuid.uuid4())
    _placement_engines[placement_id] = engine
    return {"placement_id": placement_id, "question": engine.current_question}


@app.post("/placement/{placement_id}/answer")
def placement_answer(placement_id: str, body: PlacementAnswer) -> dict:
    engine = _placement_engines.get(placement_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="Placement session not found")
    if engine.complete:
        raise HTTPException(status_code=409, detail="Placement already complete")

    correct = engine.submit_answer(body.answer)
    result: dict[str, Any] = {
        "correct": correct,
        "complete": engine.complete,
        "next_question": engine.current_question,
        "level": engine.level,
    }
    if engine.complete:
        del _placement_engines[placement_id]
    return result


# ---------------------------------------------------------------------------
# Lesson planning
# ---------------------------------------------------------------------------


@app.post("/sessions/{session_id}/plan")
def plan_lesson(session_id: int, source_text: str = "", level: str = "A1") -> dict:
    db = _get_db()
    due = db.get_due_items(limit=20)
    due_lemmas = [item["lemma"] for item in due]
    plan = interfaces.plan_lesson(source_text, level, due_lemmas)
    db.save_checkpoint(
        session_id=session_id,
        current_turn=0,
        plan_json=json.dumps(plan),
        mode="lesson",
    )
    return plan


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------


@app.post("/books")
async def upload_book(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are supported")

    import tempfile

    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        book_id = ingest_book(tmp_path, _get_db())
    except PdfIngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        os.unlink(tmp_path)

    return {"book_id": book_id}


@app.get("/books/{book_id}/chapters")
def get_chapters(book_id: int) -> list[dict]:
    chapters = list_chapters(book_id, _get_db())
    if not chapters:
        db = _get_db()
        if db.get_book(book_id) is None:
            raise HTTPException(status_code=404, detail="Book not found")
    return chapters


@app.post("/chapters/{chapter_id}/process")
def process_chapter_endpoint(chapter_id: int) -> dict:
    try:
        return process_chapter(chapter_id, _get_db())
    except (ValueError, PdfIngestionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/chapters/{chapter_id}/quiz")
def chapter_quiz(chapter_id: int, n_questions: int = 5, level: str = "B1") -> list[dict]:
    chapter = process_chapter(chapter_id, _get_db())
    text = chapter.get("cleaned_text") or ""
    if not text.strip():
        raise HTTPException(status_code=422, detail="Chapter has no processed text")
    return generate_quiz(text, n_questions=n_questions, level=level)


# ---------------------------------------------------------------------------
# Spaced repetition vocabulary
# ---------------------------------------------------------------------------


@app.get("/vocabulary/due")
def get_due_items(limit: int = 20) -> list[dict]:
    return _get_db().get_due_items(limit=limit)


@app.post("/vocabulary")
def add_vocabulary(body: LearnerItemCreate) -> dict:
    db = _get_db()
    try:
        item_id = db.add_learner_item(
            lemma=body.lemma,
            surface=body.surface,
            kind=body.kind,
            gloss_en=body.gloss_en,
            source=body.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"item_id": item_id}


@app.post("/vocabulary/{item_id}/result")
def record_vocab_result(item_id: int, correct: bool) -> dict:
    _get_db().record_result(item_id, correct)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Quiz evaluation (simple string match)
# ---------------------------------------------------------------------------


@app.post("/quiz/evaluate")
def evaluate_quiz_answer(body: QuizAnswerRequest) -> dict:
    normalise = lambda s: " ".join(s.strip().casefold().split())
    correct = normalise(body.user_answer) == normalise(body.correct_answer)
    return {"correct": correct, "question": body.question, "correct_answer": body.correct_answer}


# ---------------------------------------------------------------------------
# Pronunciation
# ---------------------------------------------------------------------------


@app.post("/pronunciation/score")
async def score_pronunciation(audio: UploadFile = File(...), target_text: str = Form("")) -> dict:
    if not target_text.strip():
        raise HTTPException(status_code=422, detail="target_text is required")
    wav = await audio.read()
    result = interfaces.score_pronunciation(wav, target_text)
    if result is None:
        return {"score": None, "message": "pronunciation scoring is disabled"}
    return {"score": result}
