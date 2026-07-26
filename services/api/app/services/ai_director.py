from typing import Any, Dict, List, Optional

from app.models import AnalysisResult, Asset, Project


DEFAULT_PRESETS = {
    "instagram_reel": {
        "platform": "instagram_reel",
        "ratio": "9:16",
        "resolution": "1080x1920",
        "target_seconds": 45,
    },
    "horizontal_social": {
        "platform": "horizontal_social",
        "ratio": "16:9",
        "resolution": "1920x1080",
        "target_seconds": 60,
    },
    "custom": {
        "platform": "custom",
        "ratio": "9:16",
        "resolution": "1080x1920",
        "target_seconds": 30,
    },
}


class LocalAIDirector:
    """Rule-based AI Director that works without external API keys."""

    def __init__(self, project: Project, assets: List[Asset], analyses: List[AnalysisResult]):
        self.project = project
        self.assets = sorted(assets, key=lambda a: a.filename)
        self.analyses = {a.asset_id: a for a in analyses}

    def _resolve_intent(self, overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        brief = self.project.brief or {}
        preset = DEFAULT_PRESETS.get(self.project.preset, DEFAULT_PRESETS["custom"])
        target = overrides.get("target_seconds") if overrides else None
        resolution = overrides.get("output_resolution") if overrides else None
        return {
            "platform": brief.get("platform") or preset["platform"],
            "ratio": brief.get("ratio") or preset["ratio"],
            "resolution": resolution or brief.get("resolution") or preset["resolution"],
            "target_seconds": target or brief.get("target_seconds") or preset["target_seconds"],
            "goal": brief.get("goal", "Create a polished edit from the supplied footage"),
            "audience": brief.get("audience", "General audience"),
        }

    def _usable_start(self, asset: Asset) -> float:
        analysis = self.analyses.get(asset.id)
        if not analysis:
            return 0.0
        black = analysis.quality.get("black_frames", [])
        freeze = analysis.quality.get("freeze_frames", [])
        start = 0.0
        for seg in black + freeze:
            if seg["start"] <= start < seg["end"]:
                start = seg["end"]
        return start

    def _select_segment(self, asset: Asset, intent: Dict[str, Any], budget: float) -> Optional[Dict[str, Any]]:
        meta = asset.metadata_json.get("video", {})
        duration = float(meta.get("duration") or 0)
        if duration <= 0:
            return None
        start = self._usable_start(asset)
        end = min(start + budget, duration)
        if end - start < 0.5:
            return None
        analysis = self.analyses.get(asset.id)
        scenes = analysis.scenes if analysis else []
        reason = "Selected from first usable moment"
        if scenes and start <= scenes[0] < end:
            end = min(scenes[0] + budget, duration)
            reason = f"Selected around first scene change at {scenes[0]:.2f}s"
        return {
            "asset_id": asset.id,
            "source_in": round(start, 3),
            "source_out": round(end, 3),
            "speed": 1.0,
            "crop": {"mode": "center", "fallback": "center"},
            "transition_out": {"type": "hard_cut"},
            "reason": reason,
        }

    def generate_plan(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        intent = self._resolve_intent(overrides)
        target = intent["target_seconds"]
        total_budget = target
        asset_budget = total_budget / max(len(self.assets), 1)

        timeline: List[Dict[str, Any]] = []
        review_flags: List[str] = []
        if not self.assets:
            review_flags.append("No assets available for editing")
        if not any(self.analyses.get(a.id) for a in self.assets):
            review_flags.append("Media analysis not run; plan is based on metadata only")

        for asset in self.assets:
            segment = self._select_segment(asset, intent, max(asset_budget, 2.0))
            if segment:
                timeline.append(segment)
            else:
                review_flags.append(f"Could not select usable segment from {asset.filename}")

        if not timeline:
            review_flags.append("Timeline is empty")

        actual_duration = sum(s["source_out"] - s["source_in"] for s in timeline)
        confidence = 0.7
        if timeline and len(timeline) == len(self.assets):
            confidence = 0.85
        if review_flags:
            confidence = max(0.4, confidence - 0.1 * len(review_flags))

        exports = [
            {
                "name": "main",
                "ratio": intent["ratio"],
                "resolution": intent["resolution"],
                "container": "mp4",
                "video_codec": "h264",
            }
        ]
        if intent["platform"] in ("instagram_reel", "custom"):
            exports.append({
                "name": "alternate_16x9",
                "ratio": "16:9",
                "resolution": "1920x1080",
                "container": "mp4",
                "video_codec": "h264",
            })

        assumptions = [
            "Uses first usable moment of each asset after skipping detected black/frozen frames.",
            "Hard cuts are used because no transition style was specified.",
            f"Target duration was set to {target}s based on preset or brief.",
            "Center-crop is used for vertical/horizontal reframing unless brief specifies otherwise.",
        ]

        fingerprints = [a.sha256 for a in self.assets]

        return {
            "plan_version": "1.0",
            "project_id": self.project.id,
            "source_fingerprints": fingerprints,
            "intent": intent,
            "assumptions": assumptions,
            "timeline": timeline,
            "audio": {
                "dialogue_target_lufs": -16,
                "music_ducking_db": -12,
            },
            "graphics": {
                "captions_enabled": True,
                "sidecar_formats": ["srt"],
            },
            "exports": exports,
            "expected_qa": [
                "Output file exists and is readable",
                "Duration is within target tolerance",
                "Resolution matches export preset",
            ],
            "confidence": round(confidence, 2),
            "review_flags": review_flags,
        }
