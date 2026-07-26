from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import Asset, Project
from app.services.workspace import allowed_path


def check_brief(project: Project) -> Dict[str, Any]:
    """Check brief for missing or contradictory instructions and propose defaults."""
    brief = project.brief or {}
    defaults: Dict[str, Any] = {}
    warnings: List[str] = []

    if not brief.get("goal"):
        defaults["goal"] = "Create a polished edit from the supplied footage"
        warnings.append("No goal specified; using default.")
    if not brief.get("audience"):
        defaults["audience"] = "General audience"
        warnings.append("No audience specified; using default.")
    if not brief.get("platform"):
        defaults["platform"] = project.preset or "custom"
        warnings.append("No platform specified; using project preset.")
    if not brief.get("target_seconds"):
        defaults["target_seconds"] = 30
        warnings.append("No target duration specified; using 30s default.")

    return {"ok": len(warnings) == 0, "warnings": warnings, "defaults_applied": defaults}


def validate_plan(plan: Dict[str, Any], project: Project, db: Session) -> List[str]:
    """Validate a generated edit plan against real assets and safe ranges."""
    errors: List[str] = []
    assets = {a.id: a for a in db.query(Asset).filter(Asset.project_id == project.id).all()}
    timeline = plan.get("timeline", [])
    seen_ids = set()

    if not timeline:
        errors.append("Plan has no timeline selections")

    for i, sel in enumerate(timeline):
        asset_id = sel.get("asset_id")
        if not asset_id:
            errors.append(f"Selection {i} missing asset_id")
            continue
        if asset_id in seen_ids:
            errors.append(f"Selection {i} duplicates asset_id {asset_id}")
        seen_ids.add(asset_id)
        asset = assets.get(asset_id)
        if not asset:
            errors.append(f"Unknown asset {asset_id} in selection {i}")
            continue
        if not allowed_path(Path(asset.workspace_path)):
            errors.append(f"Asset path escapes workspace: {asset_id}")
        start = float(sel.get("source_in", 0))
        end = float(sel.get("source_out", 0))
        if end <= start:
            errors.append(f"Selection {i} has invalid time range")

    for exp in plan.get("exports", []):
        res = exp.get("resolution", "")
        if "x" not in res:
            errors.append(f"Export {exp.get('name')} has invalid resolution {res}")

    return errors


def log_audit(db: Session, action: str, project_id: Optional[str] = None, job_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None, actor: str = "system") -> None:
    from app.models import AuditEvent
    event = AuditEvent(
        project_id=project_id,
        job_id=job_id,
        action=action,
        actor=actor,
        details=details or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
