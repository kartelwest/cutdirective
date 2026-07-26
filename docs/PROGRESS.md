# Progress

## Gate 0 — Repository and decision lock
- [x] Repository structure created
- [ ] Decision lock documented below
- [x] README and .gitignore
- [ ] Docker Compose foundation
- [ ] Health endpoints
- [ ] Development scripts

## Decision lock
- Product: CutDirective AI (working name, not trademark-cleared)
- Model: local web application with Docker Compose
- Database: SQLite (single-user internal MVP)
- Notification: SMTP (WhatsApp/Telegram adapter later)
- First presets: Instagram Reel 9:16, Horizontal Social 16:9
- Approval mode: plan approval + low-resolution preview
- Output root: user-selectable `CutDirective/Projects` folder
- AI: provider-pluggable structured-output model with local analysis fallback

## Current state
Repository initialized. Environment has Node 20, Python 3.10, FFmpeg 4.4.2, Docker 27.4.1, and `uv` 0.7.9. No remote repository yet; the GitHub integration could not create it, so the codebase is local-only until a remote is added.

## Next step
Build Gate 1 local foundation: FastAPI + SQLite project/asset API with health endpoints and worker heartbeat.
