import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    crf: int = 23,
    video_bitrate: Optional[str] = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    inputs: List[str] = []
    video_filters: List[str] = []
    audio_filters: List[str] = []
    delayed_labels: List[str] = []
    total_duration = 0.0
    for idx, sel in enumerate(selections):
        src = Path(sel["workspace_path"])
        start = float(sel["source_in"])
        end = float(sel["source_out"])
        duration = round(end - start, 6)
        total_duration += duration
        inputs.extend(["-ss", str(start), "-t", str(duration), "-i", str(src)])
        video_filters.append(
            f"[{idx}:v]setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[v{idx}]"
        )

        has_audio = has_audio_stream(probe(src))
        if has_audio:
            audio_filters.append(
                f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo:sample_rates=48000,"
                f"atrim=0:{duration},asetpts=PTS-STARTPTS[a{idx}]"
            )
        else:
            audio_filters.append(
                f"anullsrc=r=48000:cl=stereo,atrim=0:{duration},asetpts=PTS-STARTPTS[a{idx}]"
            )

        delay_ms = int(round(total_duration - duration, 3) * 1000)
        audio_filters.append(
            f"[a{idx}]adelay=delays={delay_ms}:all=1[d{idx}]"
        )
        delayed_labels.append(f"[d{idx}]")

    v_concats = "".join(f"[v{idx}]" for idx in range(len(selections)))
    video_filters.append(f"{v_concats}concat=n={len(selections)}:v=1:a=0[outv]")

    amix_inputs = "".join(delayed_labels)
    audio_filters.append(
        f"{amix_inputs}amix=inputs={len(selections)}:duration=longest:normalize=0,"
        f"aformat=sample_fmts=fltp:channel_layouts=stereo:sample_rates=48000,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,"
        f"aformat=sample_fmts=fltp:channel_layouts=stereo:sample_rates=48000[outa]"
    )

    filter_complex = ";".join(video_filters + audio_filters)

    cmd = [FFMPEG_PATH, "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", str(crf),
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
    ])
    if video_bitrate:
        cmd.extend(["-b:v", video_bitrate])
    cmd.extend([str(output_path)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")


def _run_ffmpeg_filter(path: Path, filter_graph: str, stream: str = "v") -> str:
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", str(path),
        f"-{stream}f", filter_graph,
        "-f", "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stderr


def detect_scenes(path: Path, threshold: float = 0.3) -> List[float]:
    """Return timestamps of scene changes using the scene detection filter."""
    stderr = _run_ffmpeg_filter(
        path, f"select=gt(scene\\,{threshold}),showinfo", stream="v"
    )
    timestamps = []
    for line in stderr.splitlines():
        if "pts_time:" in line:
            parts = line.split("pts_time:")
            if len(parts) > 1:
                try:
                    timestamps.append(float(parts[1].split()[0]))
                except ValueError:
                    pass
    return timestamps


def detect_silence(path: Path, noise_db: int = -50, min_duration: float = 0.5) -> List[Dict[str, float]]:
    stderr = _run_ffmpeg_filter(
        path, f"silencedetect=noise={noise_db}dB:d={min_duration}", stream="a"
    )
    segments = []
    start: Optional[float] = None
    for line in stderr.splitlines():
        if "silence_start:" in line:
            try:
                start = float(line.split("silence_start:")[1].split()[0])
            except (IndexError, ValueError):
                start = None
        elif "silence_end:" in line and start is not None:
            try:
                end = float(line.split("silence_end:")[1].split()[0])
                segments.append({"start": start, "end": end})
                start = None
            except (IndexError, ValueError):
                pass
    return segments


def detect_black_frames(path: Path, min_duration: float = 0.1) -> List[Dict[str, float]]:
    stderr = _run_ffmpeg_filter(
        path, f"blackdetect=d={min_duration}:pix_th=0.00", stream="v"
    )
    segments = []
    start: Optional[float] = None
    for line in stderr.splitlines():
        if "black_start:" in line:
            try:
                start = float(line.split("black_start:")[1].split()[0])
            except (IndexError, ValueError):
                start = None
        elif "black_end:" in line and start is not None:
            try:
                end = float(line.split("black_end:")[1].split()[0])
                segments.append({"start": start, "end": end})
                start = None
            except (IndexError, ValueError):
                pass
    return segments


def detect_freeze_frames(path: Path, min_duration: float = 2.0, noise_db: int = -60) -> List[Dict[str, float]]:
    try:
        stderr = _run_ffmpeg_filter(
            path, f"freezedetect=n={noise_db}dB:d={min_duration}", stream="v"
        )
    except Exception:
        return []
    segments = []
    start: Optional[float] = None
    for line in stderr.splitlines():
        if "freeze_start:" in line:
            try:
                start = float(line.split("freeze_start:")[1].split()[0])
            except (IndexError, ValueError):
                start = None
        elif "freeze_end:" in line and start is not None:
            try:
                end = float(line.split("freeze_end:")[1].split()[0])
                segments.append({"start": start, "end": end})
                start = None
            except (IndexError, ValueError):
                pass
    return segments


def volume_detect(path: Path) -> Dict[str, Any]:
    stderr = _run_ffmpeg_filter(path, "volumedetect", stream="a")
    result: Dict[str, Any] = {}
    for line in stderr.splitlines():
        if "mean_volume:" in line:
            try:
                result["mean_volume_db"] = float(line.split("mean_volume:")[1].split()[0])
            except (IndexError, ValueError):
                pass
        elif "max_volume:" in line:
            try:
                result["max_volume_db"] = float(line.split("max_volume:")[1].split()[0])
            except (IndexError, ValueError):
                pass
    return result


def has_audio_stream(probe_data: Dict[str, Any]) -> bool:
    return any(s.get("codec_type") == "audio" for s in probe_data.get("streams", []))


def generate_thumbnail(video_path: Path, output_path: Path, time_offset: str = "1") -> None:
    """Extract a single-frame thumbnail as JPEG."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-ss", time_offset,
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Thumbnail failed: {result.stderr}")


def burn_captions(video_path: Path, srt_path: Path, output_path: Path) -> None:
    """Burn an SRT caption file into the video using the subtitles filter."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", str(video_path),
        "-vf", f"subtitles={srt_path}",
        "-c:a", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Caption burn-in failed: {result.stderr}")
