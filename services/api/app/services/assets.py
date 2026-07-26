from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Asset
from app.services.workspace import allowed_path, copy_and_fingerprint


def ingest_asset(db: Session, project, local_path: Path, asset_type: str = "video") -> Asset:
    if not allowed_path(local_path):
        raise ValueError("Asset path is outside approved workspace")

    originals = Path(project.workspace_path) / "01_Originals"
    dst, fingerprint, probe_data = copy_and_fingerprint(local_path, originals)

    asset = Asset(
        project_id=project.id,
        filename=dst.name,
        original_path=str(local_path),
        workspace_path=str(dst),
        sha256=fingerprint,
        asset_type=asset_type,
        status="READY" if probe_data.get("readable") else "CORRUPT",
        metadata_json=probe_data,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
