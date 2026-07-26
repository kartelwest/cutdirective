from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models import AnalysisResult, Asset
from app.services.ffmpeg import (
    detect_black_frames,
    detect_freeze_frames,
    detect_scenes,
    detect_silence,
    extract_video_meta,
    has_audio_stream,
    probe,
    volume_detect,
)
from app.services.transcription import transcribe


def analyze_asset(db: Session, asset: Asset) -> AnalysisResult:
    path = Path(asset.workspace_path)
    probe_data = probe(path)
    meta = extract_video_meta(probe_data)

    asset.status = "READY" if probe_data.get("readable") else "CORRUPT"
    asset.metadata_json = {**asset.metadata_json, "video": meta}

    scenes = detect_scenes(path)
    black = detect_black_frames(path)
    freeze = detect_freeze_frames(path)

    audio: Dict[str, Any] = {}
    transcript_data: Dict[str, Any] = {}
    transcript_warnings: List[str] = []
    if has_audio_stream(probe_data):
        audio["silence"] = detect_silence(path)
        audio["volume"] = volume_detect(path)
        transcript_data, transcript_warnings = transcribe(path)
    else:
        transcript_warnings.append("No audio stream")

    quality: Dict[str, Any] = {
        "black_frames": black,
        "freeze_frames": freeze,
        "has_audio": has_audio_stream(probe_data),
        "duration": meta.get("duration"),
        "resolution": f"{meta.get('width')}x{meta.get('height')}",
        "transcript_warnings": transcript_warnings,
    }

    existing = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.asset_id == asset.id)
        .first()
    )
    if existing:
        result = existing
    else:
        result = AnalysisResult(asset_id=asset.id, project_id=asset.project_id)
        db.add(result)

    result.status = "COMPLETED" if asset.status == "READY" else "FAILED"
    result.transcript = transcript_data or {}
    result.scenes = scenes
    result.audio_events = audio
    result.quality = quality
    result.created_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(result)
    return result
