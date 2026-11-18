
import json
import time
import urllib.error
import urllib.request

MODEL = "qwen2.5:3b"
URL = "http://localhost:11434/api/chat"


def main():
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "Responde en español de España: ¿Qué hiciste ayer?"
            }
        ],
        "stream": False,
    }

    request = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

        elapsed = time.perf_counter() - start
        answer = result["message"]["content"]

        print(f"Model: {MODEL}")
        print(f"Response: {answer}")
        print(f"Time: {elapsed:.2f} seconds")
        print("PASS")

    except (urllib.error.URLError, urllib.error.HTTPError, KeyError) as error:
        elapsed = time.perf_counter() - start
        print(f"FAIL: {error}")
        print(f"Time: {elapsed:.2f} seconds")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
