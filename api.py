"""FastAPI backend for Spanish Voice Tutor."""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import interfaces
from books.ingest import PdfIngestionError, ingest_book, list_chapters, process_chapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
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
# None = still generating, list = ready, missing key = not started
_quiz_cache: dict[int, list[dict] | None] = {}


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


@app.get("/sessions")
def list_sessions(limit: int = 5) -> list[dict]:
    return _get_db().list_sessions(limit=limit)


def _bg_generate_quiz(session_id: int, text: str, level: str) -> None:
    """Background task: generate quiz, store in cache and persist to DB."""
    logging.info("BG quiz generation started for session %s", session_id)
    try:
        questions = generate_quiz(text, n_questions=5, level=level)
        result = questions if questions else _INTRO_QUIZ
        _quiz_cache[session_id] = result
        # Persist so it survives server restarts
        ckpt = _get_db().load_checkpoint(session_id)
        if ckpt:
            _get_db().save_checkpoint(
                session_id=session_id,
                current_turn=ckpt.get("current_turn", 0),
                plan_json=ckpt.get("plan_json", "{}"),
                mode=ckpt.get("mode", "lesson"),
                state_data=ckpt.get("state_data", ""),
                quiz_json=json.dumps(result),
            )
        logging.info("BG quiz done for session %s — %d questions, persisted to DB", session_id, len(result))
    except Exception as exc:
        logging.warning("BG quiz failed for session %s: %s", session_id, exc)
        _quiz_cache[session_id] = _INTRO_QUIZ


@app.post("/sessions", response_model=SessionResponse)
def create_session(body: SessionCreate, background_tasks: BackgroundTasks) -> SessionResponse:
    logging.info("POST /sessions — source_type=%s source_ref=%s level=%s chapter_id=%s",
                 body.source_type, body.source_ref, body.level, body.chapter_id)
    db = _get_db()
    source_type = body.source_type
    source_ref = body.source_ref

    chapter_text = ""
    if body.chapter_id is not None:
        logging.info("Processing chapter id=%s …", body.chapter_id)
        try:
            chapter = process_chapter(body.chapter_id, db)
        except (ValueError, Exception) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        chapter_text = chapter.get("cleaned_text") or ""
        source_type = "chapter"
        source_ref = str(body.chapter_id)
        logging.info("Chapter processed — %d chars of text", len(chapter_text))

    try:
        sid = db.create_session(
            source_type=source_type,
            source_ref=source_ref,
            level=body.level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    logging.info("Session created — id=%s", sid)

    db.save_checkpoint(
        session_id=sid,
        current_turn=0,
        plan_json="{}",
        mode="lesson",
        state_data=json.dumps({
            "chapter_text": chapter_text,
            "level": body.level,
            "topic": source_ref,
        }),
    )

    interfaces.configure_conversation(
        mode=interfaces.get_audio_adapter_mode(),
        level=body.level,
        chapter_text=chapter_text,
        topic=source_ref,
        session_id=sid,
    )
    logging.info("Conversation engine configured — mode=%s", interfaces.get_audio_adapter_mode())

    # Kick off quiz generation in background so it's ready when the session ends
    _quiz_cache[sid] = None  # mark as "generating"
    quiz_text = chapter_text if chapter_text.strip() else f"Topic: {source_ref}\nLevel: {body.level}"
    background_tasks.add_task(_bg_generate_quiz, sid, quiz_text, body.level)

    return SessionResponse(
        session_id=sid,
        source_type=source_type,
        source_ref=source_ref,
        level=body.level,
    )


class OpenerResponse(BaseModel):
    tutor_message: dict[str, Any]
    audio_b64: str


class OpenerRequest(BaseModel):
    input: str = "start"  # "start" for new session, "resume" for returning


@app.post("/sessions/{session_id}/opener", response_model=OpenerResponse)
def session_opener(session_id: int, background_tasks: BackgroundTasks, body: OpenerRequest = OpenerRequest()) -> OpenerResponse:
    """Generate Hernando's opening line for a session and return TTS audio."""
    logging.info("POST /sessions/%s/opener — input=%s", session_id, body.input)
    t0 = time.monotonic()

    context = _session_context(session_id)
    interfaces.configure_conversation(
        mode=interfaces.get_audio_adapter_mode(),
        level=context["level"],
        chapter_text=context["chapter_text"],
        topic=context["topic"],
        session_id=session_id,
    )

    # On resume, only regenerate quiz if neither cache nor DB has it
    if body.input == "resume" and session_id not in _quiz_cache:
        ckpt = _get_db().load_checkpoint(session_id)
        has_saved_quiz = bool(ckpt and ckpt.get("quiz_json"))
        if not has_saved_quiz:
            quiz_text = context["chapter_text"] if context["chapter_text"].strip() else f"Topic: {context['topic']}\nLevel: {context['level']}"
            _quiz_cache[session_id] = None
            background_tasks.add_task(_bg_generate_quiz, session_id, quiz_text, context["level"])
            logging.info("Resume: kicked off BG quiz generation for session %s", session_id)
        else:
            logging.info("Resume: quiz already in DB for session %s — skipping regeneration", session_id)

    try:
        tutor_msg = interfaces.generate_tutor_response(body.input)
    except Exception as exc:
        logging.error("Opener LLM call failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Could not generate opener: {exc}") from exc

    logging.info("Opener LLM done in %.1fs — es=%r", time.monotonic() - t0, tutor_msg.get("es", ""))

    try:
        wav = interfaces.speak(tutor_msg["es"], "ef_dora")
        audio_b64 = base64.b64encode(wav).decode()
        logging.info("Opener TTS done — %d bytes audio", len(wav))
    except Exception as exc:
        logging.warning("Opener TTS failed (%s) — returning silent response", exc)
        audio_b64 = ""

    return OpenerResponse(tutor_message=tutor_msg, audio_b64=audio_b64)


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


def _session_context(session_id: int) -> dict[str, Any]:
    ckpt = _get_db().load_checkpoint(session_id)
    if not ckpt:
        return {"chapter_text": "", "topic": "conversation", "level": "A1"}
    try:
        state = json.loads(ckpt.get("state_data") or "{}")
    except (json.JSONDecodeError, AttributeError):
        state = {}
    return {
        "chapter_text": state.get("chapter_text", ""),
        "topic": state.get("topic", "conversation"),
        "level": state.get("level", "A1"),
    }


def _next_turn_step(session_id: int) -> int:
    ckpt = _get_db().load_checkpoint(session_id)
    if not ckpt:
        return 1
    try:
        return int(ckpt.get("step", 0)) + 1
    except (TypeError, ValueError):
        return 1


@app.post("/sessions/{session_id}/turns/text", response_model=TextTurnResponse)
def text_turn(session_id: int, body: TextTurnRequest) -> TextTurnResponse:
    if not body.learner_text.strip():
        raise HTTPException(status_code=422, detail="learner_text cannot be empty")

    context = _session_context(session_id)
    interfaces.configure_conversation(
        mode=interfaces.get_audio_adapter_mode(),
        level=body.level,
        chapter_text=context["chapter_text"],
        topic=context["topic"],
        session_id=session_id,
    )
    tutor_msg = interfaces.generate_tutor_response(body.learner_text)

    db = _get_db()
    db.record_turn(
        session_id=session_id,
        step=_next_turn_step(session_id),
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
    logging.info("POST /sessions/%s/turns/voice — level=%s", session_id, level)
    t0 = time.monotonic()

    wav = await audio.read()
    if not wav:
        raise HTTPException(status_code=422, detail="audio file is empty")
    logging.info("Audio received — %d bytes", len(wav))

    context = _session_context(session_id)
    interfaces.configure_conversation(
        mode=interfaces.get_audio_adapter_mode(),
        level=level,
        chapter_text=context["chapter_text"],
        topic=context["topic"],
        session_id=session_id,
    )

    logging.info("Calling process_voice_answer …")
    result = interfaces.process_voice_answer(wav, level=level, voice="ef_dora")
    logging.info("process_voice_answer done in %.1fs — learner=%r unclear=%s",
                 time.monotonic() - t0, result.get("learner_text", ""), result.get("unclear"))

    stt_conf: float | None = None
    confs = result["transcript"].get("word_confidences", [])
    if confs:
        stt_conf = round(sum(confs) / len(confs), 4)

    db = _get_db()
    db.record_turn(
        session_id=session_id,
        step=_next_turn_step(session_id),
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


_INTRO_QUIZ: list[dict] = [
    {
        "question": "How do you say 'My name is…' in Spanish?",
        "options": ["Me llamo …", "Soy de …", "Tengo … años.", "Me gusta …"],
        "answer": "Me llamo …",
    },
    {
        "question": "How do you say 'I am from…' in Spanish?",
        "options": ["Me llamo …", "Soy de …", "Tengo … años.", "Mucho gusto."],
        "answer": "Soy de …",
    },
    {
        "question": "How do you say 'Hello' in Spanish?",
        "options": ["Adiós", "Gracias", "Hola", "Por favor"],
        "answer": "Hola",
    },
    {
        "question": "How do you say 'Nice to meet you' in Spanish?",
        "options": ["Hasta luego", "Mucho gusto", "Lo siento", "De nada"],
        "answer": "Mucho gusto",
    },
    {
        "question": "What does '¿Cómo te llamas?' mean in English?",
        "options": ["Where are you from?", "How old are you?", "What is your name?", "How are you?"],
        "answer": "What is your name?",
    },
]


@app.get("/sessions/{session_id}/quiz")
def session_quiz(session_id: int) -> list[dict]:
    """Return the pre-generated quiz for this session (ready instantly)."""
    # 1. In-memory cache hit
    cached = _quiz_cache.get(session_id)
    if cached is None and session_id in _quiz_cache:
        logging.info("GET /sessions/%s/quiz — still generating, returning fallback", session_id)
        return _INTRO_QUIZ
    if cached:
        logging.info("GET /sessions/%s/quiz — serving %d cached questions", session_id, len(cached))
        return cached
    # 2. Cache cold (server restarted) — try DB
    ckpt = _get_db().load_checkpoint(session_id)
    if ckpt and ckpt.get("quiz_json"):
        try:
            questions = json.loads(ckpt["quiz_json"])
            if questions:
                _quiz_cache[session_id] = questions  # warm the cache
                logging.info("GET /sessions/%s/quiz — loaded %d questions from DB", session_id, len(questions))
                return questions
        except (json.JSONDecodeError, TypeError):
            pass
    # 3. Nothing persisted — fallback
    logging.info("GET /sessions/%s/quiz — no quiz found, returning fallback", session_id)
    return _INTRO_QUIZ


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
