# Progress

## Gate 0 — Repository and decision lock
- [x] Repository structure created
- [x] Decision lock documented in `docs/DECISIONS.md`
- [x] README, `.env.example`, `.gitignore`, `.dockerignore`
- [x] Docker Compose foundation (api, web, worker)
- [x] Health endpoints (`/health`, `/worker/health`)
- [x] Development scripts and run commands documented
- [x] Working-name disclaimer in `docs/DECISIONS.md`

## Gate 1 — Local foundation
- [x] Project creation (`POST /projects`)
- [x] Workspace creation with numbered folders
- [x] Asset intake with copy, fingerprint (SHA-256), and ffprobe metadata
- [x] SQLite persistence with SQLAlchemy
- [x] Worker heartbeat (polling `/health`)
- [x] Job persistence (`Job` model and `/jobs/{id}`)
- [x] Disk-space health check
- [ ] Durable retry / cancel / restart (planned)

## Gate 2 — Deterministic rendering without AI
- [x] Hand-authored edit plan accepted via `POST /projects/{id}/render`
- [x] Plan validation against real asset IDs and workspace paths
- [x] FFmpeg concat with scaling/padding to target resolution
- [x] Real rendered MP4 (`docker_vertical_v01.mp4`, 1080x1920)
- [x] Basic QA probe after render
- [ ] Full operation registry and unit tests (planned)

## Gate 3 — Media intelligence
- [x] ffprobe metadata and corruption check
- [x] Scene/shot change detection with FFmpeg scene filter
- [x] Silence, black frame, freeze frame, and volume detection
- [x] Local transcription adapter (Vosk) with word-level timestamps
- [x] `AnalysisResult` persistence and `/projects/{id}/analysis` endpoint
- [ ] Advanced visual quality scoring (blur, shake, exposure) (planned)

## Gate 4 — AI Director
- [x] Pluggable local rule-based AI Director (`LocalAIDirector`)
- [x] Reads brief, preset, asset metadata, and analysis results
- [x] Generates structured edit plan with intent, assumptions, timeline, audio, graphics, exports, QA, confidence, review flags
- [x] `POST /projects/{id}/plan` endpoint
- [x] UI to analyze, generate plan, and render from plan
- [ ] Cloud LLM adapter and prompt hierarchy (planned)
- [ ] Full plan validation/repair loop (planned)

## Gate 5+ — Next
- [ ] Preview/final render split
- [ ] Captions, thumbnails, and audio mixing
- [ ] Multiple outputs from one project
- [ ] Durable job queue with retry/cancel
- [ ] SMTP and in-app notifications
- [ ] Automated QA suite
