# Hi Hola Annyong

Language-learning assistant prototype with speech, lesson, memory, and quiz
interfaces.

## Setup

```bash
brew install python@3.12
$(brew --prefix python@3.12)/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run tests and lint:

```bash
python -m pytest -q
python -m ruff check .
```

## Optional Ollama

```bash
brew install --cask ollama
ollama pull qwen2.5:3b
ollama run qwen2.5:3b
```