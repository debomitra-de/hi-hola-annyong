import json
import re
import urllib.error
import urllib.request
from difflib import SequenceMatcher
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TutorMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["prompt", "feedback", "explanation", "system"]
    es: str
    en: str
    items: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_caption_text(self) -> "TutorMessage":
        # en is intentionally empty for bilingual messages where es carries both languages
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
        temperature: float = 0.2,
    ) -> None:
        self.model = model
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

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
            "options": {"temperature": self.temperature},
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


def _extract_lesson_items(chapter_text: str, max_items: int = 6) -> list[str]:
    """Pull unique Spanish words (4+ chars) from chapter text as lesson targets."""
    words = re.findall(r"[a-záéíóúüñ]{4,}", chapter_text.lower())
    seen: dict[str, None] = {}
    for w in words:
        seen[w] = None
        if len(seen) >= max_items:
            break
    return list(seen.keys())


def _closest_word(heard: str, candidates: list[str]) -> str | None:
    """Return the candidate most similar to any word in heard, or None."""
    heard_words = re.findall(r"[a-záéíóúüña-z]{3,}", heard.lower())
    best_word, best_score = None, 0.0
    for hw in heard_words:
        for cand in candidates:
            score = SequenceMatcher(None, hw, cand.lower()).ratio()
            if score > best_score:
                best_score, best_word = score, cand
    return best_word if best_score >= 0.4 else None


_SYSTEM_PROMPT = """\
You are Hernando, a bilingual Spanish tutor. Level: {level}.

Your ONLY job: teach the CURRENT WORD by mixing Spanish and English in one short sentence.

STRICT RULES:
1. ALWAYS mention the CURRENT WORD in your reply. Never ignore it.
2. Max 10 words total. One idea only.
3. Mix Spanish and English naturally. Example: "Try saying 'quiero' — means I want!"
4. Never start a new topic. Never ask about books, movies, or anything off-topic.
5. If learner is off-topic: ignore it, return to CURRENT WORD immediately.

{state_block}

Output JSON. `es` = your bilingual sentence (max 10 words). `en` = "".
<chapter>{chapter_excerpt}</chapter>"""


class ConversationEngine:
    def __init__(
        self,
        llm: LLMAdapter,
        level: str = "A1",
        max_history_turns: int = 20,
        chapter_text: str = "",
    ) -> None:
        if level not in {"A1", "A2", "B1"}:
            raise ValueError("level must be A1, A2, or B1")
        if max_history_turns < 1:
            raise ValueError("max_history_turns must be positive")
        self.llm = llm
        self.level = level
        self.max_history_turns = max_history_turns
        self.summary = ""

        # lesson state
        self._lesson_items: list[str] = _extract_lesson_items(chapter_text) if chapter_text.strip() else []
        self._current_index: int = 0
        self._taught: list[str] = []
        self._mistakes: dict[str, int] = {}
        self._chapter_excerpt: str = chapter_text.strip()[:1200] if chapter_text.strip() else ""

        # clarification state — set when STT was unclear last turn
        self._awaiting_confirmation: str | None = None  # target word we asked about

        self.history: list[dict[str, str]] = []
        self._reset_system()

    def _state_block(self) -> str:
        current = self._lesson_items[self._current_index] if self._lesson_items and self._current_index < len(self._lesson_items) else "free conversation"
        taught = ", ".join(self._taught) if self._taught else "none yet"
        mistakes = "; ".join(f'"{w}" x{n}' for w, n in self._mistakes.items() if n > 0) or "none"
        remaining = self._lesson_items[self._current_index + 1:] if self._lesson_items else []
        not_yet = ", ".join(remaining[:5]) or "none"
        return (
            f"CURRENT WORD: {current}\n"
            f"TAUGHT: {taught}\n"
            f"KNOWN MISTAKES: {mistakes}\n"
            f"NOT YET TAUGHT (do not use): {not_yet}"
        )

    def _reset_system(self) -> None:
        system_content = _SYSTEM_PROMPT.format(
            level=self.level,
            state_block=self._state_block(),
            chapter_excerpt=self._chapter_excerpt or "(no chapter — free conversation)",
        )
        if self.history and self.history[0]["role"] == "system":
            self.history[0]["content"] = system_content
        else:
            self.history.insert(0, {"role": "system", "content": system_content})

    def _advance_lesson(self) -> None:
        current = self._lesson_items[self._current_index] if self._current_index < len(self._lesson_items) else None
        if current and current not in self._taught:
            self._taught.append(current)
        if self._current_index < len(self._lesson_items) - 1:
            self._current_index += 1

    def trim_history(self) -> None:
        system = self.history[0] if self.history and self.history[0]["role"] == "system" else None
        conversation = self.history[1:] if system else list(self.history)
        if len(conversation) <= self.max_history_turns * 2:
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

        self.history = ([system] if system else []) + (
            [{"role": "system", "content": f"Conversation summary: {self.summary}"}]
            if self.summary else []
        ) + recent

    def template_message(self) -> TutorMessage:
        return TutorMessage(
            kind="prompt",
            es="¿Podemos intentarlo otra vez?",
            en="Can we try it again?",
            items=[],
        )

    def handle_unclear(self, heard_text: str) -> tuple[TutorMessage, str | None]:
        """Called when STT confidence is low.

        Returns (TutorMessage, target_word_to_speak_slow).
        target_word is the word Kokoro should speak slowly after the message.
        """
        all_vocab = self._taught + self._lesson_items
        current = self._lesson_items[self._current_index] if self._lesson_items and self._current_index < len(self._lesson_items) else None
        closest = _closest_word(heard_text, all_vocab) if heard_text.strip() else None
        target = closest or current

        if target:
            # reflect back closest match, ask for confirmation
            self._awaiting_confirmation = target
            heard_fragment = re.findall(r"\S+", heard_text)[-1] if heard_text.strip() else "..."
            return (
                TutorMessage(
                    kind="feedback",
                    es=f"¿{heard_fragment}? ¿Quisiste decir '{target}'?",
                    en=f"Hmm, did you mean '{target}'? Listen and try again.",
                    items=[target],
                ),
                target,
            )

        # nothing to match — just ask to try again
        self._awaiting_confirmation = None
        return (
            TutorMessage(
                kind="system",
                es="",
                en="I didn't catch that. Try once more?",
                items=[],
            ),
            None,
        )

    def _is_confirmation(self, text: str) -> bool:
        return bool(re.search(r"\b(sí|si|yes|yeah|correct|yep|exacto|claro)\b", text.lower()))

    def _is_rejection(self, text: str) -> bool:
        return bool(re.search(r"\b(no|nope|not|wrong|nah)\b", text.lower()))

    def _validate(self, msg: TutorMessage) -> str | None:
        word_count = len(msg.es.split())
        if word_count > 12:
            return f"`es` has {word_count} words; max is 12. Shorten it."
        return None

    def chat(self, learner_text: str) -> TutorMessage:
        if not learner_text.strip():
            return TutorMessage(
                kind="system",
                es="",
                en="Please enter or say an answer.",
                items=[],
            )

        # handle confirmation turn after an unclear STT
        if self._awaiting_confirmation:
            target = self._awaiting_confirmation
            self._awaiting_confirmation = None
            if self._is_confirmation(learner_text):
                # they confirmed — treat it as if they said the target word correctly
                return TutorMessage(
                    kind="feedback",
                    es=target,
                    en=f"Great! Say it with me: '{target}'.",
                    items=[target],
                )
            elif self._is_rejection(learner_text):
                return TutorMessage(
                    kind="prompt",
                    es=f"¿{target}?",
                    en=f"No worries — the word is '{target}'. Give it another try!",
                    items=[target],
                )
            # else fall through — treat as a new attempt
        if not learner_text.strip():
            return TutorMessage(
                kind="system",
                es="",
                en="Please enter or say an answer.",
                items=[],
            )

        # update mistake counter
        if self._lesson_items and self._current_index < len(self._lesson_items):
            current_word = self._lesson_items[self._current_index]
            if current_word not in learner_text.lower():
                self._mistakes[current_word] = self._mistakes.get(current_word, 0) + 1
            else:
                # learner used the word correctly — advance lesson
                self._mistakes[current_word] = 0
                self._advance_lesson()

        # refresh system prompt with updated lesson state
        self._reset_system()

        self.history.append({"role": "user", "content": learner_text.strip()})
        self.trim_history()

        last_error: str | None = None
        for attempt in range(3):
            messages = list(self.history)
            if last_error and attempt > 0:
                # append a non-saved correction nudge
                messages.append({"role": "user", "content": f"[Fix this before replying: {last_error}]"})
            try:
                payload = self.llm.chat_json(messages, ConversationResponse.model_json_schema())
                response = ConversationResponse.model_validate(payload)
                error = self._validate(response.message)
                if error:
                    last_error = error
                    continue
                # save full JSON to history so model sees its own explanations
                self.history.append({
                    "role": "assistant",
                    "content": json.dumps({"es": response.message.es, "en": response.message.en}),
                })
                self.trim_history()
                return response.message
            except (RuntimeError, ValueError):
                continue

        fallback = self.template_message()
        self.history.append({"role": "assistant", "content": fallback.es})
        self.trim_history()
        return fallback



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
        chapter_text: str = "",
    ) -> None:
        if level not in {"A1", "A2", "B1"}:
            raise ValueError("level must be A1, A2, or B1")
        if max_history_turns < 1:
            raise ValueError("max_history_turns must be positive")
        self.llm = llm
        self.level = level
        self.max_history_turns = max_history_turns

        chapter_instruction = ""
        if chapter_text.strip():
            # Give LLM only the first 1500 chars per "section" so it doesn't skip material
            excerpt = chapter_text.strip()[:1500]
            level_guide = {
                "A1": "Use very simple Spanish. Max 8 words per sentence. One idea at a time.",
                "A2": "Use simple Spanish. Max 12 words per sentence.",
                "B1": "Use natural Spanish. Sentences can be moderate length.",
            }[level]
            chapter_instruction = (
                f"\n\nYou are teaching from this chapter. {level_guide} "
                "Pick 3-4 key words or phrases from the material below. "
                "Introduce ONE word at a time: say it, give a simple example, then ask the learner to use it. "
                "Do NOT summarise or explain the whole chapter. Teach like a patient human teacher, not a textbook. "
                "Correct mistakes gently. Move to the next word only after the learner practises the current one.\n\n"
                f"Chapter material:\n{excerpt}"
            )

        self.history: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    f"You are a friendly Spanish (Spain) tutor. The learner's level is {level}. "
                    "Your job: correct mistakes gently, introduce new vocabulary, and keep the "
                    "conversation moving with a follow-up question or prompt in Spanish. "
                    "Never just repeat what the learner said. "
                    "If the learner speaks English, reply in Spanish and encourage them to try in Spanish. "
                    f"{chapter_instruction}"
                    "Respond in valid JSON only — no extra text outside the JSON."
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
