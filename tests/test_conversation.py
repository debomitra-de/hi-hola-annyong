import json

from tutor.conversation import (
    ConversationEngine,
    ConversationResponse,
    MockLLM,
    OllamaLLM,
    TutorMessage,
)


def test_fake_conversation_returns_bilingual_message():
    engine = ConversationEngine(MockLLM(), level="A1")

    result = engine.chat("Hola")

    assert result.kind == "prompt"
    assert result.es
    assert result.en
    assert len(engine.history) >= 3


def test_invalid_model_output_retries_then_template_fallback():
    class InvalidLLM:
        def chat_json(
            self,
            messages,
            schema,
        ):
            del messages, schema
            return {"message": {"kind": "prompt", "es": "", "en": ""}}

    engine = ConversationEngine(InvalidLLM(), level="A2")

    result = engine.chat("¿Qué tal?")

    assert result.es
    assert result.en
    assert result.kind == "prompt"


def test_empty_learner_answer_does_not_add_history():
    engine = ConversationEngine(MockLLM(), level="A1")
    history_size = len(engine.history)

    result = engine.chat("   ")

    assert result.kind == "system"
    assert len(engine.history) == history_size


def test_wrong_attempt_is_grounded_and_keeps_current_target():
    engine = ConversationEngine(
        MockLLM(),
        level="A1",
        chapter_text="Hola casa comida.",
        topic="Ordering food",
    )
    target = engine._current_target()

    engine.chat("No entiendo nada")

    assert engine._last_attempt_status == "failed"
    assert engine._mistakes[target] == 1
    assert engine._current_target() == target
    assert "<topic>Ordering food</topic>" in engine.history[0]["content"]


def test_matching_attempt_advances_and_preserves_recent_mistakes():
    engine = ConversationEngine(
        MockLLM(),
        level="A1",
        chapter_text="Hola casa comida.",
    )
    first_target = engine._current_target()

    engine.chat(first_target)

    assert engine._last_attempt_status == "success"
    assert engine._mistakes[first_target] == 0


def test_third_person_practice_prompt_is_rejected():
    engine = ConversationEngine(MockLLM(), level="A1")
    message = TutorMessage(
        kind="prompt",
        es="Practica pedir comida con tu compañero.",
        en="Practice ordering food with your partner.",
        items=[],
    )

    error = engine._validate(message)

    assert error is not None
    assert "directly" in error


def test_conversation_history_is_bounded():
    engine = ConversationEngine(
        MockLLM(),
        level="B1",
        max_history_turns=2,
    )

    for turn in range(8):
        engine.chat(f"Turno {turn}")

    assert len(engine.history) <= 6


def test_conversation_history_is_compacted_with_summary():
    class SummarizingMock:
        def chat_json(self, messages, schema):
            del messages, schema
            return {
                "message": {
                    "kind": "prompt",
                    "es": "Hola.",
                    "en": "Hello.",
                    "items": [],
                }
            }

        def summarize(self, messages):
            del messages
            return "The learner practised restaurant vocabulary."

    engine = ConversationEngine(
        SummarizingMock(),
        level="A1",
        max_history_turns=2,
    )

    for turn in range(4):
        engine.chat(f"Turno {turn}")

    assert engine.summary == "The learner practised restaurant vocabulary."
    assert any(
        "Conversation summary:" in message["content"]
        for message in engine.history
    )
    assert len(engine.history) <= 6


def test_conversation_response_schema_accepts_valid_payload():
    payload = {
        "message": {
            "kind": "feedback",
            "es": "Muy bien.",
            "en": "Very good.",
            "items": ["muy bien"],
        }
    }

    response = ConversationResponse.model_validate(payload)

    assert response.message.es == "Muy bien."


def test_ollama_payload_uses_keep_alive(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "message": {
                                    "kind": "prompt",
                                    "es": "¿Qué hiciste?",
                                    "en": "What did you do?",
                                    "items": [],
                                }
                            }
                        )
                    }
                }
            ).encode("utf-8")

    def mock_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(
        "tutor.conversation.urllib.request.urlopen",
        mock_urlopen,
    )
    llm = OllamaLLM(timeout_seconds=15)

    result = llm.chat_json(
        [{"role": "user", "content": "Ayer estudié."}],
        {"type": "object"},
    )

    payload = json.loads(captured["request"].data)
    assert payload["keep_alive"] == "10m"
    assert payload["stream"] is False
    assert captured["timeout"] == 15
    assert result["message"]["es"] == "¿Qué hiciste?"
