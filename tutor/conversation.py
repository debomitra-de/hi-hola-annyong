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
                "es": "Muy bien. Prueba otra vez con calma.",
                "en": "Nicely done. Try it once more, slowly.",
                "items": [],
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
        timeout_seconds: float = 30,
        temperature: float = 0.3,
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
                    "turns. Preserve learner level, current topic, mistakes, "
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


# Phrase plans for topic-only sessions. Keys are lowercased topic keywords.
_TOPIC_PLANS: dict[str, list[str]] = {
    "introduccion": [
        "Me llamo …",
        "Soy de …",
        "Tengo … años.",
        "Soy estudiante.",
        "Mucho gusto.",
    ],
    "introduction": [
        "Me llamo …",
        "Soy de …",
        "Tengo … años.",
        "Soy estudiante.",
        "Mucho gusto.",
    ],
    "saludos": [
        "Hola, ¿cómo estás?",
        "Muy bien, gracias.",
        "¿Y tú?",
        "Hasta luego.",
        "Nos vemos.",
    ],
    "greetings": [
        "Hola, ¿cómo estás?",
        "Muy bien, gracias.",
        "¿Y tú?",
        "Hasta luego.",
        "Nos vemos.",
    ],
    "numeros": ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"],
    "numbers": ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"],
    "colores": ["rojo", "azul", "verde", "amarillo", "blanco", "negro", "gris", "naranja"],
    "colors": ["rojo", "azul", "verde", "amarillo", "blanco", "negro", "gris", "naranja"],
    "comida": ["el desayuno", "el almuerzo", "la cena", "tengo hambre", "me gusta …", "no me gusta …"],
    "food": ["el desayuno", "el almuerzo", "la cena", "tengo hambre", "me gusta …", "no me gusta …"],
    "familia": ["mi madre", "mi padre", "mi hermano", "mi hermana", "mis abuelos", "mi familia"],
    "family": ["mi madre", "mi padre", "mi hermano", "mi hermana", "mis abuelos", "mi familia"],
}

_DEFAULT_TOPIC_PLAN = [
    "Me llamo …",
    "Soy de …",
    "Tengo … años.",
    "Me gusta aprender español.",
    "Mucho gusto.",
]


def _topic_lesson_items(topic: str) -> list[str]:
    topic_lower = topic.lower()
    for key, items in _TOPIC_PLANS.items():
        if key in topic_lower:
            return items
    return _DEFAULT_TOPIC_PLAN


_STOPWORDS = {
    "este", "esta", "estos", "estas", "capítulo", "aprenderemos", "para", "como",
    "pero", "porque", "cuando", "donde", "también", "todo", "todos", "cada",
    "puede", "tienen", "hacer", "entre", "sobre", "desde", "hasta", "después",
}

def _extract_lesson_items(chapter_text: str, max_items: int = 6) -> list[str]:
    words = re.findall(r"[a-záéíóúüñ]{4,}", chapter_text.lower())
    seen: dict[str, None] = {}
    for word in words:
        if word in _STOPWORDS:
            continue
        seen.setdefault(word, None)
        if len(seen) >= max_items:
            break
    return list(seen)


def _normalize(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"[^a-záéíóúüñ]+", " ", text)
    return " ".join(text.split())


def _closest_word(heard: str, candidates: list[str]) -> str | None:
    heard_words = re.findall(r"[a-záéíóúüñ]{3,}", heard.lower())
    best_word: str | None = None
    best_score = 0.0
    for heard_word in heard_words:
        for candidate in candidates:
            score = SequenceMatcher(None, heard_word, candidate.lower()).ratio()
            if score > best_score:
                best_score = score
                best_word = candidate
    return best_word if best_score >= 0.55 else None


_SYSTEM_PROMPT_CHAPTER = """\
You are Hernando, a friendly bilingual Spanish tutor. Level: {level}. Topic: {topic}.

Teach the learner using the chapter text below. Each reply:
- Pick ONE word or phrase from the text that hasn't come up yet in the conversation.
- Give its meaning, then ask the learner to repeat or use it.
- If they get it right, praise briefly and move to the next word.
- If they get it wrong, show the correct form and ask them to try again.
- Answer any question they ask in simple Spanish + English.
- Keep `es` under 12 words.

<lesson>{chapter_excerpt}</lesson>

Return JSON only. `es` = Spanish reply, `en` = English note, `items` = [word just taught]."""

_SYSTEM_PROMPT_TOPIC = """\
You are Hernando, a friendly bilingual Spanish tutor. Level: {level}. Topic: {topic}.

Teach the learner the phrases below IN ORDER. For each phrase:
- Say it yourself first, then ask them to repeat it.
- If wrong, show the correct phrase and ask again. NEVER just say "wrong" — always show the phrase.
- If right, praise and move to the next phrase.

{state_block}

Return JSON only. `es` = Spanish reply (≤12 words), `en` = English coaching note, `items` = [current phrase]."""


class ConversationEngine:
    def __init__(
        self,
        llm: LLMAdapter,
        level: str = "A1",
        max_history_turns: int = 20,
        chapter_text: str = "",
        topic: str = "conversation",
    ) -> None:
        if level not in {"A1", "A2", "B1"}:
            raise ValueError("level must be A1, A2, or B1")
        if max_history_turns < 1:
            raise ValueError("max_history_turns must be positive")

        self.llm = llm
        self.level = level
        self.max_history_turns = max_history_turns
        self.topic = topic.strip() or "conversation"
        self.summary = ""
        self._has_chapter = bool(chapter_text.strip())
        if self._has_chapter:
            # Chapter mode: teach content freely, no word-drill list
            self._lesson_items = []
            self._chapter_excerpt = chapter_text.strip()[:1200]
        else:
            # Topic mode: structured phrase plan
            self._lesson_items = _topic_lesson_items(topic)
            plan_lines = "\n".join(f"{i+1}. {p}" for i, p in enumerate(self._lesson_items))
            self._chapter_excerpt = f"LESSON PLAN — teach these phrases in order:\n{plan_lines}"
        self._current_index = 0
        self._taught: list[str] = []
        self._mistakes: dict[str, int] = {}
        self._awaiting_confirmation: str | None = None
        self._last_attempt = ""
        self._last_attempt_status: Literal["not_attempted", "success", "failed"] = "not_attempted"
        self.history: list[dict[str, str]] = []
        self._reset_system()

    def _current_target(self) -> str | None:
        if self._lesson_items and self._current_index < len(self._lesson_items):
            return self._lesson_items[self._current_index]
        return None

    def _state_block(self) -> str:
        # Only used by topic/phrase-plan mode
        target = self._current_target() or "free conversation"
        taught = ", ".join(self._taught) if self._taught else "none yet"
        mistakes = (
            "; ".join(f'"{w}" x{c}' for w, c in self._mistakes.items() if c > 0) or "none"
        )
        remaining = ", ".join(self._lesson_items[self._current_index + 1:][:5]) or "none"
        return (
            f"CURRENT PHRASE: {target}\n"
            f"TAUGHT: {taught}\n"
            f"MISTAKES: {mistakes}\n"
            f"REMAINING: {remaining}\n"
            f"LAST ATTEMPT: {self._last_attempt or 'none'}\n"
            f"ATTEMPT STATUS: {self._last_attempt_status}"
        )

    def _reset_system(self) -> None:
        if self._has_chapter:
            system_content = _SYSTEM_PROMPT_CHAPTER.format(
                level=self.level,
                topic=self.topic,
                chapter_excerpt=self._chapter_excerpt,
            )
        else:
            system_content = _SYSTEM_PROMPT_TOPIC.format(
                level=self.level,
                topic=self.topic,
                state_block=self._state_block(),
            )
        if self.history and self.history[0]["role"] == "system":
            self.history[0]["content"] = system_content
        else:
            self.history.insert(0, {"role": "system", "content": system_content})

    def _advance_lesson(self) -> None:
        target = self._current_target()
        if target and target not in self._taught:
            self._taught.append(target)
        if self._current_index < len(self._lesson_items) - 1:
            self._current_index += 1

    def _learner_matches_target(self, learner_text: str) -> bool:
        target = self._current_target()
        if not target:
            return True
        learner = _normalize(learner_text)
        expected = _normalize(target)
        if expected in learner:
            return True
        expected_words = expected.split()
        learner_words = learner.split()
        if len(expected_words) <= 2 and learner_words:
            return SequenceMatcher(None, learner, expected).ratio() >= 0.72
        return False

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

        summary_messages = (
            [{"role": "system", "content": f"Conversation summary: {self.summary}"}]
            if self.summary
            else []
        )
        self.history = ([system] if system else []) + summary_messages + recent

    def template_message(self) -> TutorMessage:
        target = self._current_target()
        if target:
            return TutorMessage(
                kind="prompt",
                es=f"Probemos otra vez: '{target}'.",
                en=f"Let's try again with '{target}'.",
                items=[target],
            )
        return TutorMessage(
            kind="prompt",
            es="¿Qué quieres practicar en español?",
            en="What would you like to practice in Spanish?",
            items=[],
        )

    def handle_unclear(self, heard_text: str) -> tuple[TutorMessage, str | None]:
        all_vocab = self._taught + self._lesson_items
        current = self._current_target()
        closest = _closest_word(heard_text, all_vocab) if heard_text.strip() else None
        target = closest or current
        if target:
            self._awaiting_confirmation = target
            heard_fragment = re.findall(r"\S+", heard_text)[-1] if heard_text.strip() else "..."
            return (
                TutorMessage(
                    kind="feedback",
                    es=f"¿Escuché '{heard_fragment}'? ¿Quisiste decir '{target}'?",
                    en=f"I heard '{heard_fragment}'. Did you mean '{target}'?",
                    items=[target],
                ),
                target,
            )
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

    @staticmethod
    def _looks_english(text: str) -> bool:
        # bail early if text has Spanish-specific characters
        if re.search(r"[áéíóúüñ¿¡]", text):
            return False
        english_markers = re.findall(
            r"\b(the|is|are|was|were|have|has|how|would|say|your|you|let|try|my|name"
            r"|what|again|that|this|with|and|for|not|but|can|do|it|a|an|in|to|of|at)\b",
            text.lower(),
        )
        words = text.split()
        return bool(words) and len(english_markers) / len(words) >= 0.35

    def _validate(self, message: TutorMessage) -> str | None:
        word_count = len(message.es.split())
        if message.kind != "system" and word_count > 12:
            return f"`es` has {word_count} words; max is 12. Shorten it."
        if message.kind != "system" and word_count < 2:
            return "`es` is too short to be a valid Spanish reply. Write a full sentence."
        if not message.en.strip():
            return "`en` cannot be empty."
        if message.kind != "system" and self._looks_english(message.es):
            return "`es` must be written in Spanish, not English."
        # Replies that are only praise must include a follow-up question or next phrase
        if message.kind != "system":
            is_pure_praise = bool(re.search(r"\b(bien|correcto|perfecto|excelente|bravo|genial|muy bien|bien hecho)\b", message.es.lower()))
            has_followup = "?" in message.es or word_count > 6
            if is_pure_praise and not has_followup:
                return "After praising, always add a follow-up question or the next phrase to practise."
        # Reject vague "wrong/try again" replies in phrase-plan mode only
        if not self._has_chapter and self._last_attempt_status == "failed" and self._current_target():
            target = self._current_target()
            target_norm = _normalize(target or "")
            es_norm = _normalize(message.es)
            if target_norm and target_norm not in es_norm:
                vague = re.search(r"\b(intenta|prueba|de nuevo|otra vez|incorrecto|correcto)\b", es_norm)
                if vague:
                    return f"You said the learner is wrong but didn't show the correct phrase. Include '{target}' in `es`."
        third_person_patterns = (
            r"\btu compañero\b",
            r"\btus compañeros\b",
            r"\bcon un compañero\b",
            r"\bel alumno\b",
            r"\bla alumna\b",
            r"\bthe learner\b",
        )
        if any(re.search(pattern, f"{message.es} {message.en}", re.IGNORECASE)
               for pattern in third_person_patterns):
            return "Speak directly to me; do not involve a partner or third person."
        return None

    def chat(self, learner_text: str) -> TutorMessage:
        learner_text = learner_text.strip()
        if not learner_text:
            return TutorMessage(
                kind="system",
                es="",
                en="Please enter or say an answer.",
                items=[],
            )

        # Opener: chapter mode lets LLM read the chapter and start teaching;
        # topic mode uses a deterministic phrase introduction
        if learner_text.lower() in ("start", "resume"):
            is_resume = learner_text.lower() == "resume"
            if self._has_chapter:
                cue = (
                    "resume — greet the learner briefly and immediately introduce "
                    "the first key word or phrase from the chapter with its meaning."
                    if is_resume else
                    "start — greet the learner and immediately introduce the first "
                    "key word or phrase from the chapter text with its Spanish meaning "
                    "and English translation, then ask them to repeat it or use it."
                )
                self._reset_system()
                self.history.append({"role": "user", "content": cue})
                # learner_text updated so the verdict_tag block below is skipped cleanly
                learner_text = cue
                # Jump straight to LLM call — skip confirmation/target logic below
            else:
                target = self._current_target() or "español"
                greeting = f"¡Bienvenido de nuevo! Continuemos: '{target}'" if is_resume else f"¡Hola! Repite conmigo: '{target}'"
                greeting_en = f"Welcome back! Let's continue where we left off. Repeat: '{target}'" if is_resume else f"Hi! Let's start. Repeat after me: '{target}'"
                self._reset_system()
                self.history.append({"role": "user", "content": learner_text})
                self.history.append({"role": "assistant", "content": json.dumps({"es": greeting, "en": greeting_en})})
                return TutorMessage(kind="prompt", es=greeting, en=greeting_en, items=[])

            # Chapter opener: skip confirmation/target-matching, go straight to LLM
            last_error: str | None = None
            for attempt in range(3):
                messages = list(self.history)
                if last_error and attempt > 0:
                    messages.append({"role": "user", "content": f"[Fix this before replying: {last_error}]"})
                try:
                    payload = self.llm.chat_json(messages, ConversationResponse.model_json_schema())
                    response = ConversationResponse.model_validate(payload)
                    error = self._validate(response.message)
                    if error:
                        last_error = error
                        continue
                    self.history.append({"role": "assistant", "content": json.dumps({"es": response.message.es, "en": response.message.en})})
                    return response.message
                except (RuntimeError, ValueError):
                    continue
            fallback = self.template_message()
            self.history.append({"role": "assistant", "content": fallback.es})
            return fallback
        if self._awaiting_confirmation:
            target = self._awaiting_confirmation
            self._awaiting_confirmation = None
            if self._is_confirmation(learner_text):
                self._last_attempt = target
                self._last_attempt_status = "success"
                self._advance_lesson()
                self._reset_system()
                return TutorMessage(
                    kind="feedback",
                    es=f"Perfecto. Practiquemos '{target}'.",
                    en=f"Perfect. Let's practice '{target}'.",
                    items=[target],
                )
            if self._is_rejection(learner_text):
                self._last_attempt = learner_text
                self._last_attempt_status = "failed"
                self._mistakes[target] = self._mistakes.get(target, 0) + 1
                self._reset_system()
                return TutorMessage(
                    kind="prompt",
                    es=f"Sin problema. Dime '{target}' despacio.",
                    en=f"No worries. Say '{target}' slowly.",
                    items=[target],
                )

        target = self._current_target()
        if target:
            if self._learner_matches_target(learner_text):
                self._last_attempt = learner_text
                self._last_attempt_status = "success"
                self._mistakes[target] = 0
                self._advance_lesson()
            else:
                self._last_attempt = learner_text
                self._last_attempt_status = "failed"
                self._mistakes[target] = self._mistakes.get(target, 0) + 1
        else:
            self._last_attempt = learner_text
            self._last_attempt_status = "success"

        self._reset_system()
        verdict_tag = f" [ATTEMPT STATUS: {self._last_attempt_status}]" if target else ""
        self.history.append({"role": "user", "content": learner_text + verdict_tag})
        self.trim_history()

        last_error: str | None = None
        for attempt in range(3):
            messages = list(self.history)
            if last_error and attempt > 0:
                messages.append(
                    {"role": "user", "content": f"[Fix this before replying: {last_error}]"}
                )
            try:
                payload = self.llm.chat_json(messages, ConversationResponse.model_json_schema())
                response = ConversationResponse.model_validate(payload)
                error = self._validate(response.message)
                if error:
                    last_error = error
                    continue
                self.history.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(
                            {"es": response.message.es, "en": response.message.en}
                        ),
                    }
                )
                # Track taught vocab in chapter mode from LLM-returned items
                if self._has_chapter:
                    for item in response.message.items:
                        if item and item not in self._taught:
                            self._taught.append(item)
                self.trim_history()
                return response.message
            except (RuntimeError, ValueError):
                continue

        fallback = self.template_message()
        self.history.append({"role": "assistant", "content": fallback.es})
        self.trim_history()
        return fallback
