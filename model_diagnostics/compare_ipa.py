from phonemizer import phonemize

SENTENCES = [
    "Hola, ¿cómo estás?",
    "Me llamo Ana y estoy aprendiendo español.",
    "Quiero mejorar mi pronunciación todos los días.",
]

for i, sentence in enumerate(SENTENCES, start=1):
    reference = phonemize(
        sentence,
        language="es",
        backend="espeak",
        strip=True,
        preserve_punctuation=False,
        with_stress=True,
    )

    print(f"Clip {i}")
    print(f"Text:      {sentence}")
    print(f"eSpeak:    {reference}")
    print()
