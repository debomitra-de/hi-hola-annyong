# Development Setup

## Python environment

Install Python 3.12 using your platform's package manager, then create and
activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## macOS

Install the native dependencies used by audio processing and phonemization:

```bash
brew install python@3.12 pkg-config ffmpeg
brew install espeak-ng
```

If Python 3.12 is not the default interpreter:

```bash
$(brew --prefix python@3.12)/bin/python3.12 -m venv .venv
```

## Ubuntu

The GitHub Actions workflow installs the native dependencies with:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg pkg-config espeak-ng
```

## Optional Ollama

```bash
brew install --cask ollama
ollama pull qwen2.5:3b
ollama run qwen2.5:3b
```

## Tests and linting

```bash
python -m pytest -q
python -m ruff check .
```

Run the CNAM phonemizer diagnostic from the repository root:

```bash
python -m model_diagnostics.cnam_diagnostic
```
