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
    notification_recipients: Optional[List[str]] = []


class ProjectOut(BaseModel):
    id: str
    name: str
    client_name: Optional[str]
    workspace_path: str
    status: str
    preset: str
    approval_mode: str
    brief: Dict[str, Any]
    notification_recipients: Optional[List[str]] = []
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
    notification_recipients: Optional[List[str]] = None


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


class BriefRequest(BaseModel):
    brief: Dict[str, Any]


class BriefCheckResponse(BaseModel):
    ok: bool
    warnings: List[str]
    defaults_applied: Dict[str, Any]


class PlanRequest(BaseModel):
    target_seconds: Optional[float] = None
    output_resolution: Optional[str] = None


class EditPlanOut(BaseModel):
    id: str
    version: int
    plan_version: str
    project_id: str
    source_fingerprints: List[str]
    intent: Dict[str, Any]
    assumptions: List[str]
    timeline: List[Dict[str, Any]]
    audio: Dict[str, Any]
    graphics: Dict[str, Any]
    exports: List[Dict[str, Any]]
    expected_qa: List[str]
    confidence: float
    review_flags: List[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RenderRequest(BaseModel):
    plan_id: Optional[str] = None
    plan: Optional[Dict[str, Any]] = None
    output_name: Optional[str] = "output.mp4"
    preview: bool = False


class NotificationOut(BaseModel):
    id: str
    project_id: str
    job_id: Optional[str]
    channel: str
    recipient: Optional[str]
    subject: str
    body: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    channel: str = "in_app"
    recipient: Optional[str] = None
    subject: str
    body: str = ""


class PresetCreate(BaseModel):
    name: str
    kind: str
    data: Dict[str, Any]


class PresetOut(BaseModel):
    id: str
    name: str
    kind: str
    data: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class SettingOut(BaseModel):
    key: str
    value: Dict[str, Any]
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettingUpdate(BaseModel):
    value: Dict[str, Any]


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


class AuditEventOut(BaseModel):
    id: str
    project_id: Optional[str]
    job_id: Optional[str]
    action: str
    actor: str
    details: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
