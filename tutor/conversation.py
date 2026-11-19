import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TutorMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern=r"^(prompt|feedback|explanation|system)$")
    es: str
    en: str
    items: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_caption_text(self) -> "TutorMessage":
        if not self.en.strip():
            raise ValueError("en cannot be empty")
        if self.kind != "system" and not self.es.strip():
            raise ValueError("es cannot be empty for non-system messages")
        return self


class ConversationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: TutorMessage


class LLMAdapter(Protocol):
    def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
    ) -> dict[str, Any]: ...


class MockLLM:
    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = response

    def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        del messages, schema
        return self.response or {
            "message": {
                "kind": "prompt",
                "es": "¿Cómo te llamas?",
                "en": "What is your name?",
                "items": ["llamarse"],
            }
        }

    def summarize(self, messages: list[dict[str, str]]) -> str:
        del messages
        return "Learner practises Spanish with the tutor."


class OllamaLLM:
    def __init__(
        self,
        model: str = "qwen2.5:3b",
        url: str = "http://localhost:11434/api/chat",
        timeout_seconds: float = 120,
    ) -> None:
        self.model = model
        self.url = url
        self.timeout_seconds = timeout_seconds

    def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": schema,
            "keep_alive": "10m",
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Ollama request failed: {error}") from error

        content = data.get("message", {}).get("content")
        if not isinstance(content, str):
            raise RuntimeError("Ollama returned no message content")
        try:
            return json.loads(content)
        except json.JSONDecodeError as error:
            raise RuntimeError("Ollama returned invalid JSON") from error

    def summarize(self, messages: list[dict[str, str]]) -> str:
        schema = {
            "type": "object",
            "properties": {"summary": {"type": "string", "minLength": 1}},
            "required": ["summary"],
            "additionalProperties": False,
        }
        summary_messages = [
            {
                "role": "system",
                "content": (
                    "Summarize this Spanish tutoring conversation for future "
                    "turns. Preserve learner level, studied topics, mistakes, "
                    "corrections, vocabulary, and unfinished objectives. "
                    "Return only the JSON object."
                ),
            },
            *messages,
        ]
        payload = self.chat_json(summary_messages, schema)
        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise RuntimeError("Ollama returned no conversation summary")
        return summary.strip()


class ConversationEngine:
    def __init__(
        self,
        llm: LLMAdapter,
        level: str = "A1",
        max_history_turns: int = 20,
    ) -> None:
        if level not in {"A1", "A2", "B1"}:
            raise ValueError("level must be A1, A2, or B1")
        if max_history_turns < 1:
            raise ValueError("max_history_turns must be positive")
        self.llm = llm
        self.level = level
        self.max_history_turns = max_history_turns
        self.history: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are a Spanish Spain tutor. Respond in valid JSON only. "
                    f"The learner's level is {level}. Return a short Spanish "
                    "prompt and an accurate English caption."
                ),
            }
        ]
        self.summary = ""

    def trim_history(self) -> None:
        system = self.history[0] if self.history else None
        conversation = self.history[1:] if system else list(self.history)
        if len(conversation) <= self.max_history_turns * 2:
            self.history = ([system] if system else []) + conversation
            return

        keep_count = self.max_history_turns
        old_messages = conversation[:-keep_count]
        recent = conversation[-keep_count:]

        summarizer = getattr(self.llm, "summarize", None)
        if callable(summarizer):
            try:
                new_summary = summarizer(
                    [{"role": "system", "content": self.summary}, *old_messages]
                    if self.summary
                    else old_messages
                )
                if new_summary:
                    self.summary = new_summary
            except (RuntimeError, ValueError):
                pass

        if self.summary:
            summary_message = {
                "role": "system",
                "content": f"Conversation summary: {self.summary}",
            }
            self.history = (
                ([system] if system else [])
                + [summary_message]
                + recent
            )
        else:
            self.history = ([system] if system else []) + recent

    def template_message(self) -> TutorMessage:
        return TutorMessage(
            kind="prompt",
            es="¿Podemos intentarlo otra vez?",
            en="Can we try it again?",
            items=[],
        )

    def chat(self, learner_text: str) -> TutorMessage:
        if not learner_text.strip():
            return TutorMessage(
                kind="system",
                es="",
                en="Please enter or say an answer.",
                items=[],
            )

        self.history.append({"role": "user", "content": learner_text.strip()})
        self.trim_history()
        messages = list(self.history)

        for _ in range(2):
            try:
                payload = self.llm.chat_json(
                    messages,
                    ConversationResponse.model_json_schema(),
                )
                response = ConversationResponse.model_validate(payload)
                self.history.append(
                    {"role": "assistant", "content": response.message.es}
                )
                self.trim_history()
                return response.message
            except (RuntimeError, ValueError):
                continue

        fallback = self.template_message()
        self.history.append({"role": "assistant", "content": fallback.es})
        self.trim_history()
        return fallback
