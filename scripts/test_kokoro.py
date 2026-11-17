
from kokoro import KPipeline
import soundfile as sf
import numpy as np
import time

TEXT = "Hola, ¿cómo estás?"
VOICE = "ef_dora"

start = time.time()

pipeline = KPipeline(lang_code="e")

audio_chunks = []

for _, _, audio in pipeline(TEXT, voice=VOICE):
    audio_chunks.append(audio)

audio = np.concatenate(audio_chunks)

sf.write("hola_kokoro.wav", audio, 24000)

print(f"PASS: hola_kokoro.wav generated")
print(f"Duration: {len(audio) / 24000:.2f} seconds")
print(f"Time: {time.time() - start:.2f} seconds")
