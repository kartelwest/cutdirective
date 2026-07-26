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
    progress = Column(Float, default=0.0)
    status = Column(String, default="PENDING")
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
