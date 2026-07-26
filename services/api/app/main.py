import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import config, schemas
from app.database import SessionLocal
from app.models import AnalysisResult, Asset, AuditEvent, EditPlan, Job, Notification, Preset, Project, Setting
from app.schemas import (
    AnalysisResultOut,
    AssetOut,
    AuditEventOut,
    BriefCheckResponse,
    BriefRequest,
    EditPlanOut,
    HealthOut,
    JobOut,
    NotificationCreate,
    NotificationOut,
    PlanRequest,
    PresetCreate,
    PresetOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    RenderRequest,
    SettingOut,
    SettingUpdate,
    WorkerHeartbeatOut,
)
from app.services.ai_director import get_ai_director
from app.services.analysis import analyze_asset
from app.services.assets import ingest_asset
from app.services.captions import write_caption_sidecar
from app.services.delivery import deliver_to_local_drive, package_project
from app.services.ffmpeg import generate_thumbnail, probe, render_concat
from app.services.notifications import create_notification, notify_render_complete
from app.services.plan_validator import check_brief, log_audit, validate_plan
from app.services.qa import run_qa
from app.services.workspace import allowed_path, create_project_workspace


@asynccontextmanager
async def lifespan(app: FastAPI):
    alembic_cfg = AlembicConfig("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    yield


app = FastAPI(title="CutDirective AI API", version="0.1.0", lifespan=lifespan)

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


def _plan_to_out(plan: EditPlan) -> Dict[str, Any]:
    data = dict(plan.plan_json)
    data["id"] = plan.id
    data["version"] = plan.version
    data["status"] = plan.status
    data["created_at"] = plan.created_at.isoformat() if plan.created_at else None
    data["approved_at"] = plan.approved_at.isoformat() if plan.approved_at else None
    return data


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
        notification_recipients=payload.notification_recipients or [],
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    log_audit(db, "project_created", project_id=project.id)
    return project


@app.get("/projects", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


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


@app.post("/projects/{project_id}/archive")
def archive_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = "ARCHIVED"
    db.commit()
    log_audit(db, "project_archived", project_id=project.id)
    return {"status": "ARCHIVED"}


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
    log_audit(db, "asset_ingested", project_id=project.id, details={"asset_id": asset.id, "filename": asset.filename})
    return asset


@app.get("/projects/{project_id}/assets", response_model=List[AssetOut])
def list_assets(project_id: str, db: Session = Depends(get_db)):
    return db.query(Asset).filter(Asset.project_id == project_id).all()


@app.get("/projects/{project_id}/assets/{asset_id}", response_model=AssetOut)
def get_asset(project_id: str, asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.project_id == project_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@app.post("/projects/{project_id}/brief", response_model=ProjectOut)
def update_brief(project_id: str, request: BriefRequest, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.brief = request.brief
    db.commit()
    db.refresh(project)
    log_audit(db, "brief_updated", project_id=project.id)
    return project


@app.post("/projects/{project_id}/brief/check", response_model=BriefCheckResponse)
def check_project_brief(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return check_brief(project)


@app.post("/projects/{project_id}/analyze", response_model=JobOut)
def analyze_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "ANALYZING"
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
        log_audit(db, "analysis_complete", project_id=project.id, job_id=job.id)
    except Exception as exc:
        project.status = "FAILED"
        job.status = "FAILED"
        job.logs = str(exc)
        log_audit(db, "analysis_failed", project_id=project.id, job_id=job.id, details={"error": str(exc)})

    db.commit()
    db.refresh(job)
    return job


@app.post("/projects/{project_id}/plan", response_model=EditPlanOut)
def generate_plan(project_id: str, request: PlanRequest = PlanRequest(), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    assets = db.query(Asset).filter(Asset.project_id == project_id).all()
    analyses = db.query(AnalysisResult).filter(AnalysisResult.project_id == project_id).all()
    director = get_ai_director(project, assets, analyses)
    plan_data = director.generate_plan(request.model_dump(exclude_unset=True))

    errors = validate_plan(plan_data, project, db)
    if errors:
        plan_data["validation_errors"] = errors
        plan_data["review_flags"].extend(errors)

    version = db.query(EditPlan).filter(EditPlan.project_id == project_id).count() + 1
    plan_record = EditPlan(
        project_id=project_id,
        version=version,
        status="DRAFT",
        plan_json=plan_data,
    )
    db.add(plan_record)
    db.commit()
    db.refresh(plan_record)
    project.status = "PLAN_READY"
    db.commit()

    log_audit(db, "plan_generated", project_id=project.id, details={"plan_id": plan_record.id, "version": version, "confidence": plan_data.get("confidence")})
    return _plan_to_out(plan_record)


@app.get("/projects/{project_id}/plans", response_model=List[EditPlanOut])
def list_project_plans(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plans = db.query(EditPlan).filter(EditPlan.project_id == project_id).order_by(EditPlan.created_at.desc()).all()
    return [_plan_to_out(p) for p in plans]


@app.get("/plans/{plan_id}", response_model=EditPlanOut)
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = db.query(EditPlan).filter(EditPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_to_out(plan)


@app.post("/plans/{plan_id}/approve", response_model=EditPlanOut)
def approve_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = db.query(EditPlan).filter(EditPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.status = "APPROVED"
    plan.approved_at = datetime.now(timezone.utc)
    db.commit()
    log_audit(db, "plan_approved", project_id=plan.project_id, details={"plan_id": plan.id})
    return _plan_to_out(plan)


@app.post("/plans/{plan_id}/reject", response_model=EditPlanOut)
def reject_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = db.query(EditPlan).filter(EditPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.status = "REJECTED"
    db.commit()
    log_audit(db, "plan_rejected", project_id=plan.project_id, details={"plan_id": plan.id})
    return _plan_to_out(plan)


@app.post("/plans/{plan_id}/revise", response_model=EditPlanOut)
def revise_plan(plan_id: str, request: PlanRequest = PlanRequest(), db: Session = Depends(get_db)):
    plan = db.query(EditPlan).filter(EditPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    project = db.query(Project).filter(Project.id == plan.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    assets = db.query(Asset).filter(Asset.project_id == project.id).all()
    analyses = db.query(AnalysisResult).filter(AnalysisResult.project_id == project.id).all()
    director = get_ai_director(project, assets, analyses)
    new_data = director.generate_plan(request.model_dump(exclude_unset=True))

    version = db.query(EditPlan).filter(EditPlan.project_id == project.id).count() + 1
    new_plan = EditPlan(
        project_id=project.id,
        version=version,
        status="DRAFT",
        plan_json=new_data,
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    log_audit(db, "plan_revised", project_id=project.id, details={"parent_plan": plan_id, "new_plan": new_plan.id})
    return _plan_to_out(new_plan)


@app.post("/projects/{project_id}/render", response_model=JobOut)
def render_project(project_id: str, request: RenderRequest, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    plan_data: Optional[Dict[str, Any]] = None
    plan_record: Optional[EditPlan] = None

    if request.plan_id:
        plan_record = db.query(EditPlan).filter(EditPlan.id == request.plan_id).first()
        if not plan_record:
            raise HTTPException(status_code=404, detail="Plan not found")
        plan_data = plan_record.plan_json
    elif request.plan:
        plan_data = request.plan
    else:
        raise HTTPException(status_code=400, detail="plan or plan_id required")

    # Approval gate for final renders
    if not request.preview:
        if plan_record and plan_record.status != "APPROVED":
            if project.approval_mode == "automatic" and plan_data.get("confidence", 0) >= 0.8:
                pass
            else:
                raise HTTPException(status_code=403, detail="Plan must be approved before final render")
        elif not plan_record:
            if not (project.approval_mode == "automatic" and plan_data.get("confidence", 0) >= 0.8):
                raise HTTPException(status_code=403, detail="Plan must be approved before final render")

    payload = {
        "plan_id": request.plan_id,
        "plan": plan_data if not request.plan_id else None,
        "output_name": request.output_name,
        "preview": request.preview,
    }
    job = Job(
        project_id=project.id,
        stage="QUEUED",
        status="PENDING",
        payload=payload,
        progress=0.0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if config.SYNC_RENDER:
        from app.services.renderer import run_render_job
        run_render_job(db, job)

    return job


@app.get("/jobs", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).limit(100).all()


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
        log_audit(db, "job_canceled", project_id=job.project_id, job_id=job.id)
    return job


@app.post("/jobs/{job_id}/retry", response_model=JobOut)
def retry_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.stage == "ANALYZING" and job.status == "FAILED":
        return analyze_project(job.project_id, db=db)
    if job.stage in ("RENDERING", "PREVIEW", "QA") and job.status == "FAILED":
        # Return last render job details for re-run from UI; actual re-render needs a plan
        job.status = "RUNNING"
        job.logs = "Retry requested; re-run render with the same plan."
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        return job
    raise HTTPException(status_code=400, detail="Job is not in a retryable state")


@app.get("/projects/{project_id}/analysis", response_model=List[AnalysisResultOut])
def list_analysis(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(AnalysisResult).filter(AnalysisResult.project_id == project_id).all()


@app.get("/projects/{project_id}/notifications", response_model=List[NotificationOut])
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
        log_audit(db, "project_packaged", project_id=project.id, details={"archive": str(result.get("archive_path"))})
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
        log_audit(db, "project_delivered", project_id=project.id, details={"delivery_path": str(result.get("delivery_path"))})
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/presets", response_model=List[PresetOut])
def list_presets(db: Session = Depends(get_db)):
    return db.query(Preset).order_by(Preset.created_at.desc()).all()


@app.post("/presets", response_model=PresetOut)
def create_preset(payload: PresetCreate, db: Session = Depends(get_db)):
    preset = Preset(name=payload.name, kind=payload.kind, data=payload.data)
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@app.patch("/presets/{preset_id}", response_model=PresetOut)
def update_preset(preset_id: str, payload: PresetCreate, db: Session = Depends(get_db)):
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    preset.name = payload.name
    preset.kind = payload.kind
    preset.data = payload.data
    db.commit()
    db.refresh(preset)
    return preset


@app.get("/settings", response_model=List[SettingOut])
def list_settings(db: Session = Depends(get_db)):
    return db.query(Setting).all()


@app.get("/settings/{key}", response_model=SettingOut)
def get_setting(key: str, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@app.patch("/settings/{key}", response_model=SettingOut)
def update_setting(key: str, payload: SettingUpdate, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        setting = Setting(key=key, value=payload.value)
        db.add(setting)
    else:
        setting.value = payload.value
    setting.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(setting)
    return setting


@app.get("/audit", response_model=List[AuditEventOut])
def list_audit(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(AuditEvent)
    if project_id:
        query = query.filter(AuditEvent.project_id == project_id)
    return query.order_by(AuditEvent.created_at.desc()).limit(200).all()


def main():
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)


if __name__ == "__main__":
    main()
