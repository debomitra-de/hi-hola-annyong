# Hi Hola Annyong

Language-learning assistant prototype with speech, lesson, memory, and quiz
interfaces.

## Setup

See [the development setup guide](docs/setup.md) for platform-specific
dependencies and environment setup.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --locked
```

Install Ollama separately, then download and start Qwen:

```bash
ollama pull qwen2.5:3b
ollama serve
```

Run tests and lint:

```bash
uv run pytest -q
uv run ruff check .
```
