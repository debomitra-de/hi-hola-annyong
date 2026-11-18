import soundfile as sf
from kokoro import KPipeline

from model_diagnostics.paths import fixture_path

TEXT = "Hola, ¿cómo estás?"
OUTPUT = fixture_path("audio", "english_accent.wav")

def main():
    pipeline = KPipeline(lang_code="a")

    generator = pipeline(
        TEXT,
        voice="af_heart",
        speed=1,
    )

    for _, _, audio in generator:
        sf.write(OUTPUT, audio, 24000)
        print("English voice recording saved.")
        break

if __name__ == "__main__":
    main()