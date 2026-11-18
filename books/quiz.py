import json
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"

# qwen2.5:3b has a 32k token context window (~24k chars usable for prompt)
_CHAPTER_CHAR_LIMIT = 12000


def generate_quiz(chapter_text: str, n_questions: int = 5, level: str = "B1") -> list[dict]:
    """Send chapter text to Ollama, return list of quiz question dicts.

    Each dict has: question (str), answer (str), type (str).
    Returns [] if Ollama is unreachable or response is unparseable.
    """
    excerpt = chapter_text[:_CHAPTER_CHAR_LIMIT]
    prompt = (
        f"You are a Spanish language tutor at {level} level. "
        f"Based on the text below, generate exactly {n_questions} quiz questions "
        f"to test comprehension and vocabulary.\n\n"
        f"Return ONLY a valid JSON array. Each item must have:\n"
        f'  "question": the question in Spanish\n'
        f'  "answer": the correct answer\n'
        f'  "type": one of "comprehension", "vocabulary", "fill_blank"\n\n'
        f"Text:\n{excerpt}\n\nJSON array:"
    )

    payload = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"Ollama unreachable: {exc}")
        return []

    raw = result.get("response", "")
    start, end = raw.find("["), raw.rfind("]") + 1
    if start == -1 or end == 0:
        return []

    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return []
