import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app import config
from app.services.workspace import allowed_path


def package_project(project_name: str, project_path: Path) -> Dict[str, Any]:
    """Create a delivery archive from final exports, captions, and thumbnails."""
    workspace = Path(project_path)
    if not allowed_path(workspace):
        raise ValueError("Project path escapes approved workspace")

    sources = [
        workspace / "06_Final-Exports",
        workspace / "07_Captions",
        workspace / "08_Thumbnails",
    ]

    archive_dir = workspace / "10_Archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    existing = list(archive_dir.glob(f"{project_name}_delivery_*.zip"))
    version = len(existing) + 1
    archive_name = f"{project_name}_delivery_v{version:02d}.zip"
    archive_path = archive_dir / archive_name

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src in sources:
            if not src.exists():
                continue
            for f in src.rglob("*"):
                if f.is_file():
                    zf.write(f, arcname=str(f.relative_to(workspace)))

    return {
        "archive_path": str(archive_path),
        "archive_name": archive_name,
        "version": version,
        "created_at": datetime.utcnow().isoformat(),
    }


def deliver_to_local_drive(project_name: str, project_path: Path) -> Dict[str, Any]:
    """Copy final exports to the configured delivery root (local hard drive / delivery folder)."""
    workspace = Path(project_path)
    if not allowed_path(workspace):
        raise ValueError("Project path escapes approved workspace")

    final_dir = workspace / "06_Final-Exports"
    if not final_dir.exists():
        raise ValueError("No final exports to deliver")

    delivery_dir = config.DELIVERY_ROOT / project_name
    delivery_dir.mkdir(parents=True, exist_ok=True)

    existing = list(delivery_dir.glob("*_v*.mp4"))
    version = len(existing) + 1
    delivery_subdir = delivery_dir / f"v{version:02d}"
    delivery_subdir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for f in final_dir.iterdir():
        if f.is_file():
            dst = delivery_subdir / f.name
            shutil.copy2(str(f), str(dst))
            copied.append(str(dst))

    return {
        "delivery_path": str(delivery_subdir),
        "version": version,
        "copied_files": copied,
    }
