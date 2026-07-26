from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str
    client_name: Optional[str] = None
    preset: str = "custom"
    approval_mode: str = "plan_preview"
    brief: Dict[str, Any] = {}
    output_root: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    name: str
    client_name: Optional[str]
    workspace_path: str
    status: str
    preset: str
    approval_mode: str
    brief: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    client_name: Optional[str] = None
    preset: Optional[str] = None
    approval_mode: Optional[str] = None
    brief: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class AssetOut(BaseModel):
    id: str
    project_id: str
    filename: str
    original_path: str
    workspace_path: str
    sha256: str
    asset_type: str
    status: str
    metadata_json: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: str
    project_id: str
    stage: str
    progress: float
    status: str
    outputs: List[Dict[str, Any]]
    logs: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalysisResultOut(BaseModel):
    id: str
    asset_id: str
    project_id: str
    status: str
    transcript: Dict[str, Any]
    scenes: List[Any]
    audio_events: Dict[str, Any]
    quality: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class PlanRequest(BaseModel):
    target_seconds: Optional[float] = None
    output_resolution: Optional[str] = None


class EditPlanOut(BaseModel):
    plan_version: str
    project_id: str
    intent: Dict[str, Any]
    assumptions: List[str]
    timeline: List[Dict[str, Any]]
    audio: Dict[str, Any]
    graphics: Dict[str, Any]
    exports: List[Dict[str, Any]]
    expected_qa: List[str]
    confidence: float
    review_flags: List[str]


class HealthOut(BaseModel):
    status: str
    ffmpeg: bool
    ffprobe: bool
    database: bool
    workspace: bool
    free_gb: float


class WorkerHeartbeatOut(BaseModel):
    worker_id: str
    timestamp: str
    status: str


class RenderRequest(BaseModel):
    plan: Dict[str, Any]
    output_name: Optional[str] = "output.mp4"
    preview: bool = False
