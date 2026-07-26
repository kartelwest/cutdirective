import hashlib
import shutil
from datetime import date
from pathlib import Path
from typing import Tuple

from app.config import ROOT
from app.services.ffmpeg import probe


SANITIZE_CHARS = set('<>:"/\\|?*')


def sanitize(name: str) -> str:
    return "".join(c if c not in SANITIZE_CHARS and c.isprintable() else "_" for c in name).strip()


def create_project_workspace(project_name: str) -> Path:
    today = date.today().isoformat()
    folder_name = f"{today}_{sanitize(project_name)}"
    workspace = ROOT / "Projects" / folder_name
    for sub in [
        "01_Originals",
        "02_Assets",
        "03_Analysis",
        "04_Edit-Plans",
        "05_Previews",
        "06_Final-Exports",
        "07_Captions",
        "08_Thumbnails",
        "09_Logs",
        "10_Archive",
    ]:
        (workspace / sub).mkdir(parents=True, exist_ok=True)
    return workspace


def copy_and_fingerprint(src: Path, dst_folder: Path) -> Tuple[Path, str, dict]:
    dst_folder = Path(dst_folder)
    dst = dst_folder / src.name
    counter = 1
    while dst.exists():
        stem = src.stem
        suffix = src.suffix
        dst = dst_folder / f"{stem}_{counter}{suffix}"
        counter += 1
    shutil.copy2(str(src), str(dst))

    sha = hashlib.sha256()
    with open(dst, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    fingerprint = sha.hexdigest()

    probe_data = probe(dst)
    return dst, fingerprint, probe_data


def allowed_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
        root = ROOT.resolve()
        return root in resolved.parents or resolved == root
    except Exception:
        return False
