import os

from dotenv import load_dotenv

load_dotenv()


def _list(name: str, default: str = "") -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# Default list (probed 2026-11-04) so a missing env var does not silently disable OpenRouter.
_DEFAULT_MODELS = (
    "nvidia/nemotron-3.5-super-vl:free,nvidia/nemotron-3-ultra-550b-a55b:free,recursive/flint-v1.0:free,"
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free,dots-studio/dots-3-note-preview:free,"
    "google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free,xingchen-agi/xing4.0-29b-a4b:free,"
    "nvidia/nemotron-3.5-lightning:free"
)
OPENROUTER_MODELS = _list("OPENROUTER_MODELS", _DEFAULT_MODELS)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.8-flash")
ALLOWED_ORIGINS = _list("ALLOWED_ORIGINS", "http://localhost:5173")
DB_PATH = os.getenv("DB_PATH", "./alphadesk.db")
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "6"))

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

MAX_STEPS = 6
MAX_TOOL_CALLS = 3
MAX_REVISIONS = 2
MAX_CONCURRENCY = 2
CACHE_TTL = 600
HISTORY_MESSAGES = 6
SUMMARY_LIMIT = 5
