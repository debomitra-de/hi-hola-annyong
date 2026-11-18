import time
from io import BytesIO

import soundfile as sf

from audio.pipeline import KokoroSynthesizer
from model_diagnostics.paths import fixture_path

VOICE = "ef_dora"
SAMPLE_RATE = 24000

SENTENCES = {
    "clip_1": "Hola, ¿cómo estás?",
    "clip_2": "Me llamo Ana y estoy aprendiendo español.",
    "clip_3": "Quiero mejorar mi pronunciación todos los días.",
}

OUTPUT_DIR = fixture_path("generated")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

synthesizer = KokoroSynthesizer(voice=VOICE, lang_code="e", sample_rate=SAMPLE_RATE)

for filename, text in SENTENCES.items():
    start = time.time()

    wav_bytes = synthesizer.speak(text)
    audio, _ = sf.read(BytesIO(wav_bytes), dtype="float32")
    output = str(OUTPUT_DIR / f"{filename}.wav")

    sf.write(output, audio, SAMPLE_RATE)

    duration = len(audio) / SAMPLE_RATE

    print(
        f"PASS: {output} | "
        f"Duration: {duration:.2f}s | "
        f"Time: {time.time() - start:.2f}s"
    )
