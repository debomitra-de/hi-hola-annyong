# Hi Hola Annyong

Language-learning assistant prototype with speech, lesson, memory, and quiz
interfaces.

## Setup

See [the development setup guide](docs/setup.md) for platform-specific
dependencies and environment setup.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

Run tests and lint:

```bash
python -m pytest -q
python -m ruff check .
```
