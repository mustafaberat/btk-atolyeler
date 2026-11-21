"""Ollama hazır mı? stdlib only — Vercel / web yolunda langchain çekmesin."""
from __future__ import annotations

from urllib.request import urlopen

from config import OLLAMA_URL


def ollama_ready() -> bool:
    try:
        with urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False
