# Known Limitations — v1

This document tracks intentional v1 boundaries and gaps that are out of scope for the first internal release. Items are listed with a short rationale and the release/post-release path.

## Out of scope for v1

- **Cloud AI provider integration** — an OpenAI-compatible adapter is implemented (`OpenAIDirector`) and can be enabled with `AI_PROVIDER=openai` plus an API key. Advanced prompt hierarchy, multi-provider switching, and plan repair loops are not yet implemented.
- **True source audio ducking/music mixing** — the renderer now mixes source audio segments into the output. It does not yet auto-duck background music under dialogue or mix external music tracks.
- **Real-time job progress events** — jobs are polled via `/jobs/{id}`. A streaming or WebSocket event feed is not implemented.
- **Durable worker queue** — implemented: render jobs are queued in the API and processed by a dedicated worker container that polls the database. The queue is not yet backed by Celery/RQ/RabbitMQ; it uses the SQLite database as the queue store.
- **Advanced transitions and motion graphics** — only hard cuts and basic padding are supported. Transitions, lower-thirds, and animated graphics are future work.
- **Manual NLE-style timeline editor** — the UI is wizard-driven, not a drag-and-drop timeline.
- **Real-time collaboration / multi-user** — sessions are single-user per local instance.
- **Mobile editing app** — only the local web UI is supported.
- **SaaS billing, accounts, or cloud storage** — CutDirective AI is local-first.
- **Automatic Google Drive / cloud intake and social publishing** — files are uploaded through the UI; delivery is to the local filesystem.
- **Automatic deletion or overwriting of originals** — originals are never deleted or overwritten; workspace versioning appends new versions.
- **Unrestricted shell commands from the AI** — only whitelisted FFmpeg operations are used; no shell execution is exposed.

## Current implementation notes

- **AI Director** — the local adapter uses rule-based scene selection. Confidence and review flags are generated from heuristics, not an LLM.
- **Transcription** — Vosk runs locally and downloads a model on first use. The first transcription may take longer while the model is cached.
- **Captions** — SRT sidecars are generated from transcript segments. Timing is based on the trimmed source region.
- **QA** — automated checks cover duration, resolution, codec, pixel format, bitrate, black frames, frozen frames, and audio presence. Subjective quality is not scored.

## Next up

1. OpenAI-compatible AI adapter with prompt templating and JSON plan extraction.
2. Background worker queue with progress events and retry UI.
3. External music/background tracks and dialogue ducking.
4. More transitions and thumbnail/caption styling.
5. SMTP notification adapter and per-recipient email delivery.
