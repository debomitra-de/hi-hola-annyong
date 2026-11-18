
import sys
import time

import numpy as np
import soundfile as sf
from kokoro import KPipeline

VOICE = "ef_dora" 
SAMPLE_RATE = 24000

text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Enter Spanish text: ")

pipeline = KPipeline(lang_code="e")

start = time.time()
chunks = [audio for _, _, audio in pipeline(text, voice=VOICE)]
audio = np.concatenate(chunks)

output = "clip.wav"
sf.write(output, audio, SAMPLE_RATE)

duration = len(audio) / SAMPLE_RATE
print(f"PASS: {output} | Duration: {duration:.2f}s | Time: {time.time() - start:.2f}s")