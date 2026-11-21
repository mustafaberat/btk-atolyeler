"""EKAP Radar yerel ayarlar."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SEED_PATH = DATA_DIR / "seed_ilanlar.json"
CHROMA_DIR = ROOT / "chroma_ekap"
COLLECTION = "ekap_ilanlar_v1"

# Vercel'de dosya sistemi salt okunur; yazılabilir DB /tmp altında.
if os.getenv("VERCEL"):
    DB_PATH = Path("/tmp/ekap-radar.db")
else:
    DB_PATH = DATA_DIR / "app.db"

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "embeddinggemma")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5:1.5b")

DEFAULT_PROFILE = {
    "sehirler": ["İstanbul", "Ankara", "İzmir"],
    "anahtarlar": ["yazılım", "web", "mobil", "python", "geliştirme", "destek"],
    "sirket_var_mi": False,
    "notlar": "Bireysel geliştirici; alt yüklenici / freelance hedefi.",
}
