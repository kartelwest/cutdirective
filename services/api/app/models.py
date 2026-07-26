import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text

from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    client_name = Column(String, nullable=True)
    workspace_path = Column(String, nullable=False)
    status = Column(String, default="DRAFT")
    preset = Column(String, default="custom")
    approval_mode = Column(String, default="plan_preview")
    brief = Column(JSON, default=dict)
    notification_recipients = Column(JSON, default=list)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    workspace_path = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    asset_type = Column(String, default="video")
    status = Column(String, default="PENDING")
    metadata_json = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=now_utc)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    stage = Column(String, default="DRAFT")
    status = Column(String, default="PENDING")
    payload = Column(JSON, nullable=True)
    worker_id = Column(String, nullable=True)
    progress = Column(Float, default=0.0)
    outputs = Column(JSON, default=list)
    logs = Column(Text, default="")
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String, primary_key=True, default=_uuid)
    asset_id = Column(String, ForeignKey("assets.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    status = Column(String, default="PENDING")
    transcript = Column(JSON, default=dict)
    scenes = Column(JSON, default=list)
    audio_events = Column(JSON, default=dict)
    quality = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now_utc)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    channel = Column(String, default="in_app")
    recipient = Column(String, nullable=True)
    subject = Column(String, nullable=False)
    body = Column(Text, default="")
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=now_utc)


class Preset(Base):
    __tablename__ = "presets"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False, unique=True)
    kind = Column(String, nullable=False)
    data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now_utc)


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)


class EditPlan(Base):
    __tablename__ = "edit_plans"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    version = Column(Integer, default=1)
    status = Column(String, default="DRAFT")
    plan_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now_utc)
    approved_at = Column(DateTime, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    action = Column(String, nullable=False)
    actor = Column(String, default="system")
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now_utc)
