import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get_root() -> Path:
    raw = os.getenv("CUTDIRECTIVE_ROOT", "/home/ubuntu/CutDirective")
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


ROOT = _get_root()
DATA_DIR = Path(os.getenv("DATA_DIR", "/home/ubuntu/repos/cutdirective-ai/data")).expanduser().resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'cutdirective.db'}")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
FFPROBE_PATH = os.getenv("FFPROBE_PATH", "ffprobe")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

VOSK_MODEL_DIR = Path(os.getenv("VOSK_MODEL_DIR", str(DATA_DIR / "vosk-models"))).expanduser().resolve()
VOSK_MODEL_DIR.mkdir(parents=True, exist_ok=True)
VOSK_MODEL_NAME = os.getenv("VOSK_MODEL_NAME", "vosk-model-small-en-us-0.15")
VOSK_MODEL_URL = os.getenv(
    "VOSK_MODEL_URL",
    "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
)

# AI Director
AI_PROVIDER = os.getenv("AI_PROVIDER", "local")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o")
AI_API_KEY = os.getenv("AI_API_KEY", "")

# Delivery / notifications
DELIVERY_ROOT = Path(os.getenv("DELIVERY_ROOT", str(ROOT / "Deliveries"))).expanduser().resolve()
DELIVERY_ROOT.mkdir(parents=True, exist_ok=True)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "cutdirective@localhost")
NOTIFICATION_CHANNELS = os.getenv("NOTIFICATION_CHANNELS", "in_app").split(",")
