# Edit Plan Schema

## Plan sections

| Section | Contents |
|---------|----------|
| identity | plan version, project ID, source fingerprints, prompt/preset versions |
| intent | goal, audience, platform, duration, ratio, style, desired response |
| assumptions | defaults applied because the brief did not specify them |
| selections | chosen source ranges with scores and reasons |
| timeline | ordered edit events and transitions |
| reframing | crop, scale, subject tracking, safe-zone decisions |
| audio | dialogue, music, effects, cleanup, loudness, fades, ducking |
| graphics | captions, titles, lower thirds, logos, callouts, end cards |
| color | correction and approved creative look |
| exports | variant names, ratio, resolution, codec, frame rate, bitrate, captions, thumbnails |
| expected_qa | checks and instruction-compliance assertions |
| confidence | overall and section-level scores plus review flags |

## Example (simplified)

```json
{
  "plan_version": "1.0",
  "project_id": "project_123",
  "source_fingerprints": ["sha256:..."],
  "intent": {
    "platform": "instagram_reel",
    "target_seconds": 45,
    "ratio": "9:16",
    "goal": "Create anticipation"
  },
  "assumptions": [],
  "timeline": [
    {
      "asset_id": "clip_a",
      "source_in": 3.2,
      "source_out": 8.75,
      "speed": 1.0,
      "crop": {"mode": "smart_vertical", "fallback": "center"},
      "transition_out": {"type": "hard_cut"},
      "reason": "Strongest visual hook"
    }
  ],
  "captions": {
    "enabled": true,
    "style_preset": "bold_clean",
    "sidecar_formats": ["srt"]
  },
  "audio": {
    "dialogue_target_lufs": -16,
    "music_ducking_db": -12
  },
  "exports": [
    {
      "name": "main",
      "ratio": "9:16",
      "resolution": "1080x1920",
      "container": "mp4",
      "video_codec": "h264"
    }
  ],
  "expected_qa": [],
  "confidence": 0.88,
  "review_flags": []
}
```
