import soundfile as sf

from model_diagnostics.paths import fixture_path
from pronunciation.phonemizer import SpanishPhonemizer

audio, sample_rate = sf.read(
    fixture_path("audio", "native_spanish_2.wav")
)

phonemizer = SpanishPhonemizer()
ipa = phonemizer.transcribe(audio, sample_rate)

print("Native Spanish IPA:", ipa)