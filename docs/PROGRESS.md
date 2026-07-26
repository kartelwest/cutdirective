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
- [x] Alembic migrations committed to `services/api/alembic/`
- [x] Worker heartbeat (polling `/health`)
- [x] Job persistence (`Job` model and `/jobs/{id}`)
- [x] Disk-space health check
- [x] `/jobs` list and `/jobs/{id}/retry` endpoints

## Gate 2 — Deterministic rendering without AI
- [x] Hand-authored edit plan accepted via `POST /projects/{id}/render`
- [x] Plan validation against real asset IDs and workspace paths
- [x] FFmpeg concat with scaling/padding to target resolution
- [x] Source audio mixed into the rendered output
- [x] Real rendered MP4 (`docker_vertical_v01.mp4`, 1080x1920)
- [x] Basic QA probe after render
- [x] Structured plan validator and whitelisted operation registry (`app/services/plan_validator.py`)

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
- [x] Edit plans persisted (`EditPlan` model)
- [x] Plan approve/reject/revise endpoints (`/plans/{id}/approve`, etc.)
- [x] UI to analyze, generate plan, approve, and render from plan
- [x] Provider-pluggable adapter (`BaseAIDirector`)
- [x] OpenAI-compatible adapter (`OpenAIDirector`) with `AI_PROVIDER` / `AI_MODEL` / `AI_BASE_URL` / `AI_API_KEY` config
- [x] Automatic fallback to local rule-based director when cloud provider is unavailable or unconfigured
- [ ] Advanced prompt hierarchy and plan repair loop (planned)

## Gate 5 — Production workflow
- [x] Preview render to `05_Previews` with half-resolution and lower bitrate
- [x] Final render to `06_Final-Exports`
- [x] Multiple outputs from a single plan (e.g., main + alternate 16:9)
- [x] Source audio mixed and loudness-normalized
- [x] Thumbnail generation to `08_Thumbnails`
- [x] SRT sidecar generation to `07_Captions`
- [x] Versioned output file naming
- [x] Basic `POST /jobs/{id}/cancel` endpoint
- [x] UI buttons for preview vs final, plan approval, and output review
- [ ] Watermarked preview burn-in (planned)
- [ ] Background worker render queue with real-time progress (planned)

## Gate 6 — QA, notifications, and delivery
- [x] Automated QA per output (duration, resolution, codec, pixel format, bitrate, black/freeze frames, audio presence)
- [x] `COMPLETED` vs `COMPLETED_WITH_WARNINGS` job status
- [x] Pluggable notification adapter (`in_app` + SMTP when configured)
- [x] In-app notification records and `/projects/{id}/notifications` endpoints
- [x] Automatic notification on render completion
- [x] Project packaging endpoint (`/projects/{id}/package`) creating `10_Archive` zip
- [x] Local delivery endpoint (`/projects/{id}/deliver`) copying final exports to `DELIVERY_ROOT`
- [x] UI for QA summary, packaging, delivery, and notification inbox

## Gate 7 — Internal release
- [x] Operator runbook (`docs/OPERATORS.md`)
- [x] Backup/restore scripts (`scripts/backup.sh`, `scripts/restore.sh`)
- [x] Integration test script (`scripts/integration-test.sh`)
- [x] Real-project pilot with a generated speech+scene clip
- [x] End-to-end verification: analyze → plan → approve → render → QA → package → deliver → notify
- [x] `docs/KNOWN_LIMITATIONS.md` published
- [ ] Cloud LLM adapter for the AI Director (planned)
- [ ] Background worker render queue with real-time progress and retry/restart (planned)
