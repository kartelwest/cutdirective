from pathlib import Path
from typing import Any, Dict, List

from app.services.ffmpeg import detect_black_frames, detect_freeze_frames, has_audio_stream, probe


def run_qa(video_path: Path, expected_duration: float | None, expected_resolution: str | None) -> Dict[str, Any]:
    """Run a QA suite on a rendered output and return pass/warn/error details."""
    result: Dict[str, Any] = {"passed": [], "warnings": [], "errors": []}
    if not video_path.exists():
        result["errors"].append("Output file does not exist")
        return result

    data = probe(video_path)
    if not data.get("readable"):
        result["errors"].append("Output file is not readable by ffprobe")
        return result

    format_info = data.get("format", {})
    streams = data.get("streams", [])
    duration = float(format_info.get("duration") or 0)
    bitrate = int(format_info.get("bit_rate") or 0)

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    width = video_stream.get("width")
    height = video_stream.get("height")
    codec = video_stream.get("codec_name")
    pix_fmt = video_stream.get("pix_fmt")

    result["duration"] = duration
    result["resolution"] = f"{width}x{height}" if width and height else None
    result["codec"] = codec
    result["pix_fmt"] = pix_fmt
    result["bitrate"] = bitrate
    result["has_audio"] = has_audio_stream(data)

    if expected_duration is not None:
        diff = abs(duration - expected_duration)
        if diff > 1.0:
            result["errors"].append(f"Duration mismatch: {duration:.2f}s vs expected {expected_duration:.2f}s")
        elif diff > 0.5:
            result["warnings"].append(f"Duration slightly off: {duration:.2f}s vs expected {expected_duration:.2f}s")
        else:
            result["passed"].append("Duration within tolerance")

    if expected_resolution:
        actual = f"{width}x{height}" if width and height else ""
        if actual != expected_resolution:
            result["errors"].append(f"Resolution mismatch: {actual} vs expected {expected_resolution}")
        else:
            result["passed"].append("Resolution matches expected")

    if codec and codec.lower() not in ("h264", "libx264"):
        result["errors"].append(f"Unexpected video codec: {codec}")
    else:
        result["passed"].append("Video codec is H.264")

    if pix_fmt and pix_fmt != "yuv420p":
        result["warnings"].append(f"Pixel format {pix_fmt} may not be universally compatible")
    else:
        result["passed"].append("Pixel format yuv420p")

    if bitrate < 100_000:
        result["warnings"].append(f"Very low bitrate: {bitrate} bps")
    elif bitrate > 50_000_000:
        result["warnings"].append(f"Very high bitrate: {bitrate} bps")
    else:
        result["passed"].append("Bitrate within normal range")

    try:
        black = detect_black_frames(video_path, min_duration=0.5)
        if black:
            result["warnings"].append(f"Detected {len(black)} black-frame segments")
        else:
            result["passed"].append("No black frames detected")
    except Exception as exc:
        result["warnings"].append(f"Black-frame check failed: {exc}")

    try:
        freeze = detect_freeze_frames(video_path, min_duration=1.0)
        if freeze:
            result["warnings"].append(f"Detected {len(freeze)} frozen-frame segments")
        else:
            result["passed"].append("No frozen frames detected")
    except Exception as exc:
        result["warnings"].append(f"Freeze-frame check failed: {exc}")

    result["ok"] = len(result["errors"]) == 0
    return result
