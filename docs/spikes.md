# Development Setup and Spikes

This file collects development setup, testing, CI, and database notes, along
with experiment results for Ollama, Faster-Whisper, and the CNAM phonemizer.

## Python environment

Use the project virtual environment so packages are installed for the intended
Python interpreter:

```bash
python3.15 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Use `python -m pip` and `python -m pytest` instead of `pip3` and `pytest` so
the commands always use the active interpreter.

If a dependency has no Python 3.15 wheel, use Python 3.13:

```bash
brew install python@3.13
$(brew --prefix python@3.13)/bin/python3.13 -m venv .venv313
source .venv313/bin/activate
```

## Tests and linting

Run these commands from the repository root:

```bash
python -m pytest -q
python -m ruff check .
```

Pytest discovers files named `test_*.py` or `*_test.py`.

## GitHub Actions

The workflow is stored at `.github/workflows/ci.yml`. It uses Python 3.12,
installs dependencies, and runs:

```bash
python -m pip install pytest
python -m pytest -q
```

## Database

SQLite databases are stored under `data/`. The default database path is:

```text
data/tutor.db
```

`memory.database.Database` creates the directory automatically. Database files
are ignored by Git.

## Faster-whisper

On macOS, install the native dependencies required by PyAV:

```bash
brew install pkg-config ffmpeg
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install faster-whisper
```

If PyAV still builds from source and fails, use the Python 3.13 environment
described above. The package name is `ffmpeg`, not `ffm`.

## Ollama

Install Ollama with Homebrew:

```bash
brew install --cask ollama
```

Start the Ollama service if it is not already running:

```bash
ollama serve
```

Download and run the model used by this spike:

```bash
ollama pull qwen2.5:7b
ollama run qwen2.5:7b
```

The local API is available at `http://localhost:11434`. Test it with:

```bash
curl http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:7b","prompt":"Describe your day in Spanish.","stream":false}'
```

## Spike results

### Ollama

Model: `qwen2.5:7b`
Result: PASS  
Observed response time: 1.17 seconds

### Faster-whisper

Setup requires Homebrew's `pkg-config` and `ffmpeg` packages before installing`faster-whisper`.
Model: small
Detected language: es
Transcription: FSI spanish basic course unit 21 tape 3 replacement rails page 49 que les ha parecido la base que les ha parecido la baseparque que les ha parecido el parque que tal que tal les ha parecido el parque pareció que tal les pareció el parque ese que tal les pareció ese parque ciudad que tal les pareció esa ciudad que tal le pareció esa ciudad países que tal le parecieron esos países nosotros dimos una vuelta nosotros dimos una vuelta cheque nosotros dimos un cheque cambiamos nosotros cambiamos un cheque ellos ellos cambiaron un cheque recibieron ellos recibieron un cheque este ellos recibieron este cheque hicieron ellos hicieron este cheque yo yo hice este cheque yo solo anduve por el parque yo solo anduve por el parque ciudad yo solo anduve por la ciudad en yo solo anduve en la ciudad estuve yo solo estuve en la ciudad nosotros nosotros solo estuvimos en la ciudad esas nosotros solo estuvimos en esas ciudades apenas nosotros apenasestuvimos en esas ciudades tú tú apenas estuviste en esas ciudades
Time: 17.08 seconds
PASS

## 3. Cnam phonemizer
- Package: phonemizer
- Backend: espeak-ng
- Language: es
Input: Hola, ¿cómo estás?
IPA: ola komo estas
Time: 5.2829 seconds
PASS
