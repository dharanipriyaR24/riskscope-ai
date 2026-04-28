import os

import requests

_base = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_URL = f"{_base}/api/generate"
MODEL = os.environ.get("OLLAMA_MODEL", "phi3:latest")


def run_copilot(prompt: str) -> str:
    payload = {"model": MODEL, "prompt": prompt, "stream": False}

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        return (data.get("response") or "").strip() or "No response from model."
    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama at http://localhost:11434. Is Ollama running?"
    except requests.exceptions.Timeout:
        return (
            "ERROR: Ollama timed out. The model may be loading—try again (first run can be slow)."
        )
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"
