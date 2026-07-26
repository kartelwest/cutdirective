# CutDirective AI — Operator Runbook

## Stack overview
- **API**: FastAPI + SQLite + SQLAlchemy (`services/api`)
- **Web UI**: Next.js 16 (`apps/web`)
- **Worker**: Python heartbeat poller (`services/worker`)
- **Runtime**: Docker Compose (`infra/docker-compose.yml`)
- **Workspace**: `CutDirective/Projects/<date>_<project-name>/` with numbered folders (`01_Originals` … `10_Archive`)

## Daily commands

```bash
# Start everything
docker compose -f infra/docker-compose.yml up -d --build

# View logs
docker compose -f infra/docker-compose.yml logs -f api
docker compose -f infra/docker-compose.yml logs -f worker

# Health check
curl http://localhost:8000/health

# Stop
docker compose -f infra/docker-compose.yml down
```

## Project lifecycle
1. Create project via UI (`http://localhost:3000/projects/new`) or `POST /projects`.
2. Upload assets via project page.
3. Click **Analyze assets** to run probe, scene, silence, black/freeze, and transcription.
4. Click **Generate plan** to produce an AI edit plan.
5. Click **Render preview** for a half-resolution sample, then **Render final** for full exports.
6. Review QA summary under each output.
7. Click **Package project** to create a zip in `10_Archive`.
8. Click **Deliver to local drive** to copy finals to `DELIVERY_ROOT`.

## Backup / restore
```bash
./scripts/backup.sh  /path/to/backup/dir
./scripts/restore.sh /path/to/backup/dir
```

Backups include the SQLite database (`data/cutdirective.db`) and the entire `CutDirective/` workspace.

## Configuration
Copy `.env.example` to `.env` and adjust:
- `CUTDIRECTIVE_ROOT` — local workspace root
- `DATABASE_URL` — four-slash absolute SQLite URL, e.g. `sqlite:////home/ubuntu/repos/cutdirective-ai/data/cutdirective.db`
- `DELIVERY_ROOT` — local delivery folder
- `SMTP_*` — optional email notifications
- `AI_*` — optional cloud LLM provider
- `FFMPEG_PATH` / `FFPROBE_PATH` — should be `/usr/bin/ffmpeg` and `/usr/bin/ffprobe`

## Common issues
- **"FFmpeg failed"** — check `FFMPEG_PATH`, disk space, and that source files are not corrupt.
- **"Stream map matches no streams"** — resolved by adding a generated AAC audio track; source audio mixing is a future enhancement.
- **SQLite URL relative path** — use four slashes (`sqlite:///`) for an absolute path.
- **Worker not processing** — current worker only polls `/health`; render is handled synchronously by the API. Background queue is planned.

## Security notes
- Original assets are copied to `01_Originals` and never modified/deleted by the app.
- The AI never emits raw shell commands; only whitelisted FFmpeg operations run.
- All file paths are validated against `CUTDIRECTIVE_ROOT`.

## Monitoring
- `GET /health` returns ffmpeg, ffprobe, database, workspace, and free-space status.
- Job status is stored in the `jobs` table and surfaced in the UI.
- Notifications are stored in `notifications`.

## Next operational improvements
- Background worker render queue with retry/cancel.
- PostgreSQL backend for multi-user deployments.
- Backup automation with cron.
