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
