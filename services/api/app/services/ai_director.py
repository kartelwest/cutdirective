import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app import config
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
    "tiktok_9x16": {
        "platform": "tiktok_9x16",
        "ratio": "9:16",
        "resolution": "1080x1920",
        "target_seconds": 60,
    },
    "youtube_shorts": {
        "platform": "youtube_shorts",
        "ratio": "9:16",
        "resolution": "1080x1920",
        "target_seconds": 60,
    },
    "custom": {
        "platform": "custom",
        "ratio": "9:16",
        "resolution": "1080x1920",
        "target_seconds": 30,
    },
}


PLAN_SCHEMA = {
    "plan_version": "1.0",
    "intent": {
        "platform": "string",
        "ratio": "string",
        "resolution": "string (e.g. 1080x1920)",
        "target_seconds": "number",
        "goal": "string",
        "audience": "string",
    },
    "assumptions": ["list of strings"],
    "timeline": [
        {
            "asset_id": "asset UUID",
            "source_in": "number (seconds)",
            "source_out": "number (seconds)",
            "speed": 1.0,
            "crop": {"mode": "center|fit|fill"},
            "transition_out": {"type": "hard_cut|fade|none"},
            "reason": "string",
        }
    ],
    "audio": {
        "dialogue_target_lufs": -16,
        "music_ducking_db": -12,
    },
    "graphics": {
        "captions_enabled": True,
        "sidecar_formats": ["srt"],
    },
    "exports": [
        {
            "name": "main|alternate_16x9",
            "ratio": "9:16|16:9",
            "resolution": "1080x1920|1920x1080",
            "container": "mp4",
            "video_codec": "h264",
        }
    ],
    "expected_qa": ["list of strings"],
    "confidence": "number 0.0-1.0",
    "review_flags": ["list of strings"],
}


class BaseAIDirector(ABC):
    """Pluggable director that turns project context + media analysis into a structured edit plan."""

    def __init__(self, project: Project, assets: List[Asset], analyses: List[AnalysisResult]):
        self.project = project
        self.assets = sorted(
            [a for a in assets if a.asset_type == "video"],
            key=lambda a: a.filename,
        )
        self.analyses = {a.asset_id: a for a in analyses}

    @abstractmethod
    def generate_plan(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...


class LocalAIDirector(BaseAIDirector):
    """Rule-based AI Director that works without external API keys."""

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
        black = analysis.quality.get("black_frames", []) or []
        freeze = analysis.quality.get("freeze_frames", []) or []
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
        if intent["platform"] in ("instagram_reel", "custom", "tiktok_9x16", "youtube_shorts"):
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


class OpenAIDirector(BaseAIDirector):
    """AI Director backed by an OpenAI-compatible chat completion API."""

    def _build_prompt(self, overrides: Optional[Dict[str, Any]]) -> str:
        brief = self.project.brief or {}
        preset = DEFAULT_PRESETS.get(self.project.preset, DEFAULT_PRESETS["custom"])
        target = overrides.get("target_seconds") if overrides else None
        target = target or brief.get("target_seconds") or preset["target_seconds"]
        resolution = overrides.get("output_resolution") if overrides else None
        resolution = resolution or brief.get("resolution") or preset["resolution"]

        asset_summaries = []
        for asset in self.assets:
            meta = asset.metadata_json.get("video", {})
            analysis = self.analyses.get(asset.id)
            scenes = analysis.scenes if analysis else []
            transcript_text = ""
            if analysis and analysis.transcript:
                transcript_text = analysis.transcript.get("text", "")
            asset_summaries.append({
                "id": asset.id,
                "filename": asset.filename,
                "duration": meta.get("duration"),
                "resolution": meta.get("resolution"),
                "fps": meta.get("fps"),
                "scenes": scenes[:10],
                "transcript": transcript_text,
            })

        prompt = (
            "You are CutDirective AI Director, an expert video editor. "
            "Given a project brief and analyzed source media, produce a structured edit plan as JSON.\n\n"
            "Project brief:\n"
            f"- goal: {brief.get('goal', 'Create a polished edit from the supplied footage')}\n"
            f"- audience: {brief.get('audience', 'General audience')}\n"
            f"- platform: {brief.get('platform') or preset['platform']}\n"
            f"- preset: {self.project.preset}\n"
            f"- target duration: {target} seconds\n"
            f"- target resolution: {resolution}\n"
            f"- approval mode: {self.project.approval_mode}\n\n"
            "Source media summaries (id, duration, scenes, transcript excerpts):\n"
        )
        for summary in asset_summaries:
            prompt += f"- {json.dumps(summary, default=str)}\n"

        prompt += (
            "\nOutput a single JSON object matching this schema exactly:\n"
            f"{json.dumps(PLAN_SCHEMA, indent=2)}\n\n"
            "Rules:\n"
            "- Use the exact asset UUIDs from the summaries above for timeline.asset_id.\n"
            "- source_in and source_out must be within each asset's actual duration.\n"
            "- Trim silence/frozen/black frames if mentioned in the analysis context.\n"
            "- Confidence should reflect how well the brief can be met with the supplied footage.\n"
            "- Include any issues in review_flags.\n"
            "- Do not include markdown, commentary, or code fences.\n"
        )
        return prompt

    def _fallback(self, overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        director = LocalAIDirector(self.project, self.assets, list(self.analyses.values()))
        plan = director.generate_plan(overrides)
        plan["review_flags"].insert(0, "OpenAI provider unavailable or misconfigured; used local rule-based director as fallback.")
        plan["confidence"] = max(0.4, plan["confidence"] - 0.15)
        return plan

    def generate_plan(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            from openai import OpenAI
        except Exception:
            return self._fallback(overrides)

        if not config.AI_API_KEY:
            return self._fallback(overrides)

        client = OpenAI(api_key=config.AI_API_KEY, base_url=config.AI_BASE_URL)
        prompt = self._build_prompt(overrides)

        try:
            response = client.chat.completions.create(
                model=config.AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert video editor. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2048,
            )
            content = response.choices[0].message.content
            if not content:
                return self._fallback(overrides)

            plan = json.loads(content)
            # Inject required fields that the model may omit or alter
            plan["plan_version"] = plan.get("plan_version", "1.0")
            plan["project_id"] = self.project.id
            plan["source_fingerprints"] = [a.sha256 for a in self.assets]
            if "audio" not in plan:
                plan["audio"] = {"dialogue_target_lufs": -16, "music_ducking_db": -12}
            if "graphics" not in plan:
                plan["graphics"] = {"captions_enabled": True, "sidecar_formats": ["srt"]}
            if "expected_qa" not in plan:
                plan["expected_qa"] = [
                    "Output file exists and is readable",
                    "Duration is within target tolerance",
                    "Resolution matches export preset",
                ]
            return plan
        except Exception as exc:
            plan = self._fallback(overrides)
            plan["review_flags"].insert(0, f"OpenAI director failed: {exc}. Fallback used.")
            return plan


def get_ai_director(
    project: Project,
    assets: List[Asset],
    analyses: List[AnalysisResult],
) -> BaseAIDirector:
    """Factory that selects the configured director provider."""
    if config.AI_PROVIDER == "openai":
        return OpenAIDirector(project, assets, analyses)
    return LocalAIDirector(project, assets, analyses)
