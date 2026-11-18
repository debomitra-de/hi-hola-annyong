import time

from phonemizer import phonemize

TEXT = "Hola, ¿cómo estás?"


def main():
    start = time.perf_counter()

    try:
        result = phonemize(
            TEXT,
            language="es",
            backend="espeak",
            strip=True,
            preserve_punctuation=True,
            with_stress=True,
            language_switch="remove-flags",
            njobs=1,
        )

        elapsed = time.perf_counter() - start

        print(f"Input: {TEXT}")
        print(f"IPA: {result}")
        print(f"Time: {elapsed:.4f} seconds")
        print("PASS")

    except Exception as error:
        elapsed = time.perf_counter() - start
        print(f"FAIL: {error}")
        print(f"Time: {elapsed:.4f} seconds")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()