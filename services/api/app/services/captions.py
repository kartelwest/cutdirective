from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List


def _srt_time(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    total = int(td.total_seconds() * 1000)
    hours = total // 3600000
    minutes = (total % 3600000) // 60000
    seconds = (total % 60000) // 1000
    millis = total % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def generate_srt(segments: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for i, seg in enumerate(segments, start=1):
        start = float(seg.get("start") or 0)
        end = float(seg.get("end") or start + 2)
        text = seg.get("text", "").strip()
        if not text:
            continue
        lines.append(str(i))
        lines.append(f"{_srt_time(start)} --> {_srt_time(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def write_caption_sidecar(segments: List[Dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_srt(segments), encoding="utf-8")
    return output_path
