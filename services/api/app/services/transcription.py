import json
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app import config


def _ensure_model() -> Optional[Path]:
    model_path = config.VOSK_MODEL_DIR / config.VOSK_MODEL_NAME
    if model_path.exists():
        return model_path
    zip_path = config.VOSK_MODEL_DIR / f"{config.VOSK_MODEL_NAME}.zip"
    try:
        urllib.request.urlretrieve(config.VOSK_MODEL_URL, zip_path)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(config.VOSK_MODEL_DIR)
        zip_path.unlink(missing_ok=True)
        return model_path
    except Exception as exc:
        print(f"Could not download Vosk model: {exc}")
        return None


def _extract_wav(input_path: Path, output_path: Path) -> bool:
    cmd = [
        config.FFMPEG_PATH,
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def _has_audio(input_path: Path) -> bool:
    from app.services.ffmpeg import probe
    data = probe(input_path)
    return any(s.get("codec_type") == "audio" for s in data.get("streams", []))


def transcribe(input_path: Path) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Return transcript dict and list of warnings."""
    warnings: List[str] = []
    if not _has_audio(input_path):
        warnings.append("No audio stream found")
        return None, warnings

    model_path = _ensure_model()
    if not model_path:
        warnings.append("Vosk model not available")
        return None, warnings

    try:
        from vosk import Model, KaldiRecognizer
        import wave
    except ImportError as exc:
        warnings.append(f"Vosk not installed: {exc}")
        return None, warnings

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "audio.wav"
        if not _extract_wav(input_path, wav_path):
            warnings.append("Failed to extract audio for transcription")
            return None, warnings

        try:
            wf = wave.open(str(wav_path), "rb")
        except Exception as exc:
            warnings.append(f"Could not open extracted audio: {exc}")
            return None, warnings

        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
            warnings.append("Audio not in expected 16kHz 16-bit mono format")
            return None, warnings

        model = Model(str(model_path))
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)

        words: List[Dict[str, Any]] = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                words.extend(res.get("result", []))

        final = json.loads(rec.FinalResult())
        words.extend(final.get("result", []))

        segments: List[Dict[str, Any]] = []
        if words:
            current_text: List[str] = []
            current_start: Optional[float] = None
            current_end: Optional[float] = None
            for w in words:
                text = w.get("word", "")
                if not text:
                    continue
                if current_start is None:
                    current_start = w.get("start")
                    current_end = w.get("end")
                current_text.append(text)
                current_end = w.get("end")
                if text.endswith((".", "!", "?")) or len(current_text) >= 12:
                    segments.append({
                        "start": current_start,
                        "end": current_end,
                        "text": " ".join(current_text),
                    })
                    current_text = []
                    current_start = None
                    current_end = None
            if current_text:
                segments.append({
                    "start": current_start,
                    "end": current_end,
                    "text": " ".join(current_text),
                })

        transcript_text = final.get("text", " ".join(w.get("word", "") for w in words))
        return {
            "text": transcript_text,
            "language": "en",
            "words": words,
            "segments": segments,
        }, warnings
