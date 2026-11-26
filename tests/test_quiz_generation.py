import json

from books import quiz


def test_prompt_requires_spanish_question_stems(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"response":"[]"}'

    def fake_urlopen(request, timeout):
        captured["prompt"] = json.loads(request.data)["prompt"]
        return Response()

    monkeypatch.setattr(quiz.urllib.request, "urlopen", fake_urlopen)

    quiz.generate_quiz("Hola, ¿cómo estás?", n_questions=1, level="A1")

    assert '"question": a clear, simple question written in Spanish' in captured["prompt"]
    assert "Write every question in Spanish, not English." in captured["prompt"]
