import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
USER_AGENT = "GPAtlasAU/1.0 (+https://github.com/HassanCodesIt)"
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
DB_PATH = Path(os.getenv("DB_PATH", str(ROOT / "clinic_data.db")))
AI_CACHE_TTL = int(os.getenv("AI_CACHE_TTL", "900"))
SEARCH_CACHE_TTL = int(os.getenv("SEARCH_CACHE_TTL", "900"))
FETCH_CACHE_TTL = int(os.getenv("FETCH_CACHE_TTL", "900"))


def require_groq_key() -> str:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Copy .env.example to .env and add your Groq API key."
        )
    return GROQ_API_KEY
