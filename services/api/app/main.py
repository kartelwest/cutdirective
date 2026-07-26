import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import config, schemas
from app.database import SessionLocal, engine, Base
from app.models import AnalysisResult, Asset, Job, Notification, Preset, Project, Setting
from app.schemas import (
    AnalysisResultOut,
    AssetOut,
    EditPlanOut,
    HealthOut,
    JobOut,
    NotificationCreate,
    NotificationOut,
    PlanRequest,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    RenderRequest,
    WorkerHeartbeatOut,
)
from app.services.ai_director import LocalAIDirector
from app.services.analysis import analyze_asset
from app.services.assets import ingest_asset
from app.services.captions import write_caption_sidecar
from app.services.delivery import deliver_to_local_drive, package_project
from app.services.ffmpeg import generate_thumbnail, probe, render_concat
from app.services.notifications import create_notification, notify_render_complete
from app.services.qa import run_qa
from app.services.workspace import allowed_path, create_project_workspace

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CutDirective AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)):
    ffmpeg_ok = shutil.which(config.FFMPEG_PATH) is not None
    ffprobe_ok = shutil.which(config.FFPROBE_PATH) is not None
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    workspace_ok = config.ROOT.exists() and config.ROOT.is_dir()
    free = shutil.disk_usage(config.ROOT).free / (1024 ** 3)
    return HealthOut(
        status="ok",
        ffmpeg=ffmpeg_ok,
        ffprobe=ffprobe_ok,
        database=db_ok,
        workspace=workspace_ok,
        free_gb=round(free, 2),
    )


@app.get("/worker/health", response_model=WorkerHeartbeatOut)
def worker_health():
    return WorkerHeartbeatOut(
        worker_id="worker-001",
        timestamp=datetime.now(timezone.utc).isoformat(),
        status="idle",
    )


@app.post("/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    workspace = create_project_workspace(payload.name)
    project = Project(
        name=payload.name,
        client_name=payload.client_name,
        workspace_path=str(workspace),
        preset=payload.preset,
        approval_mode=payload.approval_mode,
        brief=payload.brief,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()


@app.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@app.post("/projects/{project_id}/assets", response_model=AssetOut)
def add_asset(
    project_id: str,
    file: UploadFile = File(...),
    asset_type: str = Form("video"),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    upload_root = config.ROOT / "_uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    temp_path = upload_root / file.filename
    with open(temp_path, "wb") as f:
        f.write(file.file.read())

    asset = ingest_asset(db, project, temp_path, asset_type=asset_type)
    try:
        temp_path.unlink()
    except Exception:
        pass
    return asset


@app.get("/projects/{project_id}/assets")
def list_assets(project_id: str, db: Session = Depends(get_db)):
    return db.query(Asset).filter(Asset.project_id == project_id).all()


@app.get("/projects/{project_id}/assets/{asset_id}", response_model=AssetOut)
def get_asset(project_id: str, asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.project_id == project_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/jobs/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("COMPLETED", "FAILED"):
        job.status = "CANCELED"
        job.logs = "Canceled by user"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
    return job


@app.get("/projects/{project_id}/analysis", response_model=list[AnalysisResultOut])
def list_analysis(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(AnalysisResult).filter(AnalysisResult.project_id == project_id).all()


@app.post("/projects/{project_id}/plan", response_model=EditPlanOut)
def generate_plan(project_id: str, request: PlanRequest = PlanRequest(), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    assets = db.query(Asset).filter(Asset.project_id == project_id).all()
    analyses = db.query(AnalysisResult).filter(AnalysisResult.project_id == project_id).all()
    director = LocalAIDirector(project, assets, analyses)
    plan = director.generate_plan(request.model_dump(exclude_unset=True))
    return plan


@app.post("/projects/{project_id}/render", response_model=JobOut)
def render_project(
    project_id: str,
    request: RenderRequest,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stage = "PREVIEW" if request.preview else "RENDERING"
    job = Job(project_id=project.id, stage=stage, status="RUNNING", progress=0.0)
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        plan = request.plan
        selections = plan.get("timeline", [])
        if not selections:
            raise ValueError("Edit plan has no timeline selections")

        assets_by_id = {a.id: a for a in db.query(Asset).filter(Asset.project_id == project_id).all()}
        mapped = []
        for sel in selections:
            asset_id = sel.get("asset_id")
            asset = assets_by_id.get(asset_id)
            if not asset:
                raise ValueError(f"Unknown asset {asset_id}")
            workspace_path = asset.workspace_path
            if not allowed_path(Path(workspace_path)):
                raise ValueError(f"Asset path escapes workspace: {workspace_path}")
            mapped.append({
                **sel,
                "workspace_path": workspace_path,
            })

        exports = plan.get("exports", [{}])
        if request.preview:
            exports = exports[:1]

        base_name = request.output_name or "output"
        if base_name.endswith(".mp4"):
            base_name = base_name[:-4]

        graphics = plan.get("graphics", {})
        captions_enabled = graphics.get("captions_enabled", False)

        analyses_by_asset = {
            a.asset_id: a
            for a in db.query(AnalysisResult).filter(AnalysisResult.project_id == project_id).all()
        }

        outputs: list[dict] = []
        for idx, export in enumerate(exports):
            res = export.get("resolution", "1080x1920")
            width, height = 1080, 1920
            if "x" in res:
                width, height = map(int, res.split("x"))

            crf = 23
            bitrate: str | None = None
            if request.preview:
                width = max(width // 2, 320)
                height = max(height // 2, 480)
                crf = 28
                bitrate = "2M"

            folder = "05_Previews" if request.preview else "06_Final-Exports"
            export_name = export.get("name") or f"export_{idx}"
            out_dir = Path(project.workspace_path) / folder
            out_dir.mkdir(parents=True, exist_ok=True)

            existing = list(out_dir.glob(f"{base_name}_{export_name}_v*.mp4"))
            version = len(existing) + 1
            output_name = f"{base_name}_{export_name}_v{version:02d}.mp4"
            output_path = out_dir / output_name

            render_concat(mapped, output_path, width=width, height=height, crf=crf, video_bitrate=bitrate)

            qa = probe(output_path)
            if not qa.get("readable"):
                raise RuntimeError(f"Rendered output is not readable: {output_path}")

            output_entry = {
                "name": output_name,
                "path": str(output_path),
                "resolution": f"{width}x{height}",
                "duration": float(qa.get("format", {}).get("duration", 0) or 0),
                "kind": "preview" if request.preview else "final",
            }

            thumb_dir = Path(project.workspace_path) / "08_Thumbnails"
            thumb_dir.mkdir(parents=True, exist_ok=True)
            thumb_path = thumb_dir / f"{output_name}_thumb.jpg"
            try:
                generate_thumbnail(output_path, thumb_path, "1")
                output_entry["thumbnail_path"] = str(thumb_path)
            except Exception:
                pass

            if captions_enabled:
                srt_segments: list[dict] = []
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
                    srt_path = srt_dir / f"{output_name}.srt"
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
        else:
            job.status = "COMPLETED_WITH_WARNINGS"
        job.outputs = outputs
        job.logs = f"Rendered {len(outputs)} outputs; QA complete"

        notify_render_complete(db, project.id, job.id, outputs)
    except Exception as exc:
        job.status = "FAILED"
        job.logs = str(exc)
    finally:
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
    return job


@app.post("/projects/{project_id}/analyze", response_model=JobOut)
def analyze_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = Job(project_id=project_id, stage="ANALYZING", status="RUNNING", progress=0.0)
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        assets = db.query(Asset).filter(Asset.project_id == project_id).all()
        for asset in assets:
            analyze_asset(db, asset)
        project.status = "ANALYZED"
        job.status = "COMPLETED"
        job.stage = "ANALYZED"
        job.progress = 1.0
    except Exception as exc:
        job.status = "FAILED"
        job.logs = str(exc)

    db.commit()
    db.refresh(job)
    return job


@app.get("/projects/{project_id}/notifications", response_model=list[NotificationOut])
def list_notifications(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Notification).filter(Notification.project_id == project_id).order_by(Notification.created_at.desc()).all()


@app.post("/projects/{project_id}/notifications", response_model=NotificationOut)
def create_project_notification(
    project_id: str,
    payload: NotificationCreate,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return create_notification(
        db,
        project_id=project_id,
        job_id=None,
        channel=payload.channel,
        recipient=payload.recipient or config.SMTP_FROM,
        subject=payload.subject,
        body=payload.body,
    )


@app.post("/projects/{project_id}/package")
def package_for_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        result = package_project(project.name, Path(project.workspace_path))
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/projects/{project_id}/deliver")
def deliver_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        result = deliver_to_local_drive(project.name, Path(project.workspace_path))
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def main():
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)


if __name__ == "__main__":
    main()
