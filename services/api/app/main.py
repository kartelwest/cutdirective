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
from app.models import AnalysisResult, Asset, Job, Preset, Project, Setting
from app.schemas import (
    AnalysisResultOut,
    AssetOut,
    EditPlanOut,
    HealthOut,
    JobOut,
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
from app.services.ffmpeg import probe, render_concat
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

    job = Job(project_id=project.id, stage="RENDERING", status="RUNNING", progress=0.0)
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        plan = request.plan
        selections = plan.get("timeline", [])
        if not selections:
            raise ValueError("Edit plan has no timeline selections")

        # Map asset_id to workspace path
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

        export = plan.get("exports", [{}])[0]
        width, height = 1080, 1920
        res = export.get("resolution", "1080x1920")
        if "x" in res:
            width, height = map(int, res.split("x"))

        output_name = request.output_name
        if not output_name.endswith(".mp4"):
            output_name += ".mp4"
        output_path = Path(project.workspace_path) / "06_Final-Exports" / output_name

        render_concat(mapped, output_path, width=width, height=height)

        # Basic QA probe
        qa = probe(output_path)
        if not qa.get("readable"):
            raise RuntimeError("Rendered output is not readable after probing")

        output_entry = {
            "name": output_name,
            "path": str(output_path),
            "resolution": res,
            "duration": float(qa.get("format", {}).get("duration", 0) or 0),
        }

        job.stage = "QA"
        job.progress = 1.0
        job.status = "COMPLETED"
        job.outputs = [output_entry]
        job.logs = f"Rendered {output_name} at {output_path}"
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


def main():
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)


if __name__ == "__main__":
    main()
