from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import config
from app.models import AnalysisResult, Asset, EditPlan, Job, Project
from app.services.captions import write_caption_sidecar
from app.services.ffmpeg import generate_thumbnail, probe, render_concat
from app.services.notifications import notify_render_complete
from app.services.plan_validator import log_audit
from app.services.qa import run_qa
from app.services.workspace import allowed_path


def _load_plan(db: Session, payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not payload:
        return None
    plan_id = payload.get("plan_id")
    if plan_id:
        record = db.query(EditPlan).filter(EditPlan.id == plan_id).first()
        if record:
            return record.plan_json
    return payload.get("plan")


def run_render_job(db: Session, job: Job) -> None:
    """Execute a queued render job and update its record."""
    project = db.query(Project).filter(Project.id == job.project_id).first()
    if not project:
        raise ValueError(f"Project {job.project_id} not found")

    payload = job.payload or {}
    plan = _load_plan(db, payload)
    if not plan:
        raise ValueError("Job payload is missing a plan")

    output_name = payload.get("output_name") or "output"
    preview = payload.get("preview", False)

    job.stage = "PREVIEW" if preview else "RENDERING"
    job.status = "RUNNING"
    job.worker_id = config.WORKER_ID
    db.commit()

    try:
        selections = plan.get("timeline", [])
        if not selections:
            raise ValueError("Edit plan has no timeline selections")

        assets_by_id = {a.id: a for a in db.query(Asset).filter(Asset.project_id == project.id).all()}
        mapped = []
        for sel in selections:
            asset_id = sel.get("asset_id")
            asset = assets_by_id.get(asset_id)
            if not asset:
                raise ValueError(f"Unknown asset {asset_id}")
            workspace_path = asset.workspace_path
            if not allowed_path(Path(workspace_path)):
                raise ValueError(f"Asset path escapes workspace: {workspace_path}")
            mapped.append({**sel, "workspace_path": workspace_path})

        exports = plan.get("exports", [{}])
        if preview:
            exports = exports[:1]

        base_name = output_name
        if base_name.endswith(".mp4"):
            base_name = base_name[:-4]

        graphics = plan.get("graphics", {})
        captions_enabled = graphics.get("captions_enabled", False)

        analyses_by_asset = {
            a.asset_id: a
            for a in db.query(AnalysisResult).filter(AnalysisResult.project_id == project.id).all()
        }

        outputs: List[Dict[str, Any]] = []
        for idx, export in enumerate(exports):
            res = export.get("resolution", "1080x1920")
            width, height = 1080, 1920
            if "x" in res:
                width, height = map(int, res.split("x"))

            crf = 23
            bitrate: Optional[str] = None
            if preview:
                width = max(width // 2, 320)
                height = max(height // 2, 480)
                crf = 28
                bitrate = "2M"

            folder = "05_Previews" if preview else "06_Final-Exports"
            export_name = export.get("name") or f"export_{idx}"
            out_dir = Path(project.workspace_path) / folder
            out_dir.mkdir(parents=True, exist_ok=True)

            existing = list(out_dir.glob(f"{base_name}_{export_name}_v*.mp4"))
            version = len(existing) + 1
            _output_name = f"{base_name}_{export_name}_v{version:02d}.mp4"
            output_path = out_dir / _output_name

            render_concat(mapped, output_path, width=width, height=height, crf=crf, video_bitrate=bitrate)

            qa = probe(output_path)
            if not qa.get("readable"):
                raise RuntimeError(f"Rendered output is not readable: {output_path}")

            output_entry = {
                "name": _output_name,
                "path": str(output_path),
                "resolution": f"{width}x{height}",
                "duration": float(qa.get("format", {}).get("duration", 0) or 0),
                "kind": "preview" if preview else "final",
            }

            thumb_dir = Path(project.workspace_path) / "08_Thumbnails"
            thumb_dir.mkdir(parents=True, exist_ok=True)
            thumb_path = thumb_dir / f"{_output_name}_thumb.jpg"
            try:
                generate_thumbnail(output_path, thumb_path, "1")
                output_entry["thumbnail_path"] = str(thumb_path)
            except Exception:
                pass

            if captions_enabled:
                srt_segments: List[Dict[str, Any]] = []
                cursor = 0.0
                for sel in selections:
                    offset = float(sel.get("source_in", 0))
                    duration = float(sel.get("source_out", 0)) - offset
                    ana = analyses_by_asset.get(sel.get("asset_id"))
                    if ana and ana.transcript:
                        for seg in ana.transcript.get("segments", []):
                            start = max(0.0, float(seg.get("start", 0)) - offset) + cursor
                            end = max(0.0, float(seg.get("end", 0)) - offset) + cursor
                            text = seg.get("text", "").strip()
                            if text:
                                srt_segments.append({"start": start, "end": end, "text": text})
                    cursor += duration
                if srt_segments:
                    srt_dir = Path(project.workspace_path) / "07_Captions"
                    srt_dir.mkdir(parents=True, exist_ok=True)
                    srt_path = srt_dir / f"{_output_name}.srt"
                    write_caption_sidecar(srt_segments, srt_path)
                    output_entry["caption_path"] = str(srt_path)

            expected_duration = sum(
                float(sel.get("source_out", 0)) - float(sel.get("source_in", 0))
                for sel in selections
            )
            output_entry["qa"] = run_qa(output_path, expected_duration, f"{width}x{height}")

            outputs.append(output_entry)
            job.progress = round((idx + 1) / len(exports), 2)
            db.commit()

        job.stage = "QA"
        job.progress = 1.0
        if all(o["qa"].get("ok") for o in outputs):
            job.status = "COMPLETED"
            project.status = "COMPLETED" if not preview else project.status
        else:
            job.status = "COMPLETED_WITH_WARNINGS"
            project.status = "COMPLETED_WITH_WARNINGS"
        job.outputs = outputs
        job.logs = f"Rendered {len(outputs)} outputs; QA complete"

        notify_render_complete(db, project.id, job.id, outputs, project.notification_recipients or [config.SMTP_FROM])
        log_audit(db, "render_complete", project_id=project.id, job_id=job.id, details={"outputs": [o["name"] for o in outputs]})
    except Exception as exc:
        job.status = "FAILED"
        job.logs = str(exc)
        project.status = "FAILED"
        log_audit(db, "render_failed", project_id=project.id, job_id=job.id, details={"error": str(exc)})

    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
