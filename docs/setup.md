# Development Setup

## 1. Python environment

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

```bash
uv python install 3.12
uv sync --locked
```

## 2. System dependencies

### macOS

```bash
brew install pkg-config ffmpeg espeak-ng portaudio
```

### Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg pkg-config espeak-ng libportaudio2 portaudio19-dev
```

### Windows

**FFmpeg** — install via winget, or manually:

1. Download `ffmpeg-release-essentials.zip` from https://www.gyan.dev/ffmpeg/builds/
2. Extract it and note the inner `bin\` folder
3. Add that `bin\` folder to PATH:

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Users\<you>\ffmpeg\bin", "Machine")
```

4. Reopen your terminal and verify: `ffmpeg -version`

**eSpeak NG** — install with the official Windows installer and add it to PATH.
If `phonemizer` cannot locate it, set:

```powershell
$env:PHONEMIZER_ESPEAK_LIBRARY = "C:\Program Files\eSpeak NG\libespeak-ng.dll"
```

**PortAudio** is bundled with the `sounddevice` wheel — no separate install needed.

## 3. Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows (PowerShell)
irm https://ollama.com/install.ps1 | iex
```

Pull the default model and start the server:

```bash
ollama pull qwen2.5:3b
ollama serve
```

Keep `ollama serve` running in a separate terminal. On macOS and Windows, Ollama
may already run as a background service — skip `ollama serve` in that case.

The app calls Ollama at `http://localhost:11434`; no API key or cloud service is required.

Verify:

```bash
ollama list
curl http://localhost:11434/api/tags
```

## 4. Model downloads

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

## 5. Verification

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
