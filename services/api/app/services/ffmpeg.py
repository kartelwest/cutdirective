import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from app.config import FFMPEG_PATH, FFPROBE_PATH


def probe(path: Path) -> Dict[str, Any]:
    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
        if result.returncode != 0:
            return {"error": result.stderr, "readable": False}
        data = json.loads(result.stdout)
        data["readable"] = True
        return data
    except Exception as exc:
        return {"error": str(exc), "readable": False}


def extract_video_meta(probe_data: Dict[str, Any]) -> Dict[str, Any]:
    meta = {
        "container": probe_data.get("format", {}).get("format_name"),
        "duration": float(probe_data.get("format", {}).get("duration", 0) or 0),
        "bitrate": int(probe_data.get("format", {}).get("bit_rate", 0) or 0),
        "width": None,
        "height": None,
        "frame_rate": None,
        "codec": None,
        "audio_codec": None,
        "sample_rate": None,
        "channels": None,
    }
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "video" and meta["width"] is None:
            meta["width"] = stream.get("width")
            meta["height"] = stream.get("height")
            meta["codec"] = stream.get("codec_name")
            r_frame_rate = stream.get("r_frame_rate", "")
            if "/" in str(r_frame_rate):
                num, den = r_frame_rate.split("/")
                meta["frame_rate"] = round(float(num) / float(den), 3) if float(den) else None
            else:
                meta["frame_rate"] = float(r_frame_rate) if r_frame_rate else None
        elif stream.get("codec_type") == "audio" and meta["audio_codec"] is None:
            meta["audio_codec"] = stream.get("codec_name")
            meta["sample_rate"] = stream.get("sample_rate")
            meta["channels"] = stream.get("channels")
    return meta


def render_concat(
    selections: List[Dict[str, Any]],
    output_path: Path,
    width: int = 1080,
    height: int = 1920,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    inputs: List[str] = []
    filters: List[str] = []
    for idx, sel in enumerate(selections):
        src = Path(sel["workspace_path"])
        start = float(sel["source_in"])
        end = float(sel["source_out"])
        duration = end - start
        inputs.extend(["-ss", str(start), "-t", str(duration), "-i", str(src)])
        filters.append(
            f"[{idx}:v]setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[v{idx}];"
        )
    v_concats = "".join(f"[v{idx}]" for idx in range(len(selections)))
    filters.append(f"{v_concats}concat=n={len(selections)}:v=1:a=0[outv]")
    filter_complex = "".join(filters)

    # Build final command: video inputs only with deterministic concat.
    # Audio mixing will be added once the operation registry is expanded.
    cmd = [FFMPEG_PATH, "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "23",
        "-movflags", "+faststart",
        str(output_path),
    ])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")
