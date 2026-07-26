# CutDirective AI

Describe the edit. Get the cut.

A local-first, AI-directed video post-production workflow.

## Quick start (Docker Compose)

1. Copy `.env.example` to `.env` and adjust paths.
2. `docker compose -f infra/docker-compose.yml up --build`
3. Open `http://localhost:3000`.

## Development (without Docker)

- API: `cd services/api && uv run uvicorn app.main:app --reload`
- Web: `cd apps/web && npm run dev`
- Worker: `cd services/worker && uv run python -m app.main`

## Verification

A test render was produced at `sample-data/outputs/docker_vertical_v01.mp4` (1080x1920, ~4s) by creating a project, uploading two sample clips, and rendering from a hand-authored edit plan through the API.

See `docs/` for architecture, decisions, and operations guides.
