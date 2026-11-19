# Development Setup

## Python environment

Install uv, Python 3.12, and the project dependencies:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
uv sync --locked
```

## macOS

Install native audio and phoneme dependencies:

```bash
brew install pkg-config ffmpeg espeak-ng portaudio
```

## Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg pkg-config espeak-ng libportaudio2 portaudio19-dev
```

## Windows

Windows setup requires PowerShell and winget:

```powershell
winget install --id astral-sh.uv -e
winget install --id Ollama.Ollama -e
winget install --id Gyan.FFmpeg -e
```

UV:

```powershell
uv python install 3.12
uv sync --locked
```

Install eSpeak NG with the official Windows installer and add it to `PATH`.
If `phonemizer` cannot locate it, set `PHONEMIZER_ESPEAK_LIBRARY` to the
installed `libespeak-ng.dll` path.

PortAudio is bundled with `sounddevice`'s supported Windows wheel. No separate
PortAudio package is normally required.

## Ollama

Install Ollama for the current platform, then start the server:

```bash
ollama pull qwen2.5:3b
ollama serve
```

Keep `ollama serve` running in a separate terminal. If Ollama is already
running as a macOS or Windows background service, do not start it again.

Qwen 2.5 3B is a local system model. It is not installed by `uv sync`.
The app calls Ollama at `http://localhost:11434`; no API key or cloud service
is required.

Check Ollama from any platform:

```bash
ollama list
curl http://localhost:11434/api/tags
```

## Kokoro and CNAM model downloads

Models are downloaded by their libraries on first real use:

- Kokoro: the `hexgrad/Kokoro-82M` assets are resolved by Kokoro during the first
  `KokoroSynthesizer.speak()` call.
- CNAM: `Cnam-LMSSC/wav2vec2-spanish-phonemizer` is downloaded by Transformers
  during the first `SpanishPhonemizer()` construction.
- Qwen: `qwen2.5:3b` is downloaded by `ollama pull`.

All models are cached locally after the first successful download. Internet
access is only needed for initial model installation; a session can run offline
afterward.

CI never downloads or runs these models.

## Verification

Run the repository checks:

```bash
uv run pytest -q
uv run ruff check .
```

Run the fixture-based Whisper diagnostic:

```bash
uv run python -m model_diagnostics.whisper_demo
```

Run live push-to-talk transcription:

```bash
uv run python -m model_diagnostics.push_to_talk_diagnostic
```

Run real TTS generation:

```bash
uv run python -m model_diagnostics.kokoro_demo
```

Test the public real adapters:

```bash
TUTOR_ADAPTER_MODE=real uv run python - <<'PY'
from pathlib import Path
import interfaces

wav = Path("tests/fixtures/audio/spanish_sample.mp3").read_bytes()
print(interfaces.transcribe(wav)["text"])
print(len(interfaces.speak("Hola, ¿cómo estás?", "ef_dora")))
PY
```

Run the CNAM diagnostic after Kokoro generated the three fixture clips:

```bash
uv run python -m model_diagnostics.cnam_diagnostic
```
