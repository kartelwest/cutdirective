# Architecture

## Components

```text
apps/web/        Next.js UI (dashboard, project, brief, edit plan, job detail, output review, settings)
services/api/    FastAPI + Pydantic + SQLAlchemy (project/asset CRUD, job lifecycle, presets, settings)
services/worker/ Python durable worker (media analysis, AI plan generation, FFmpeg render, QA, notifications)
packages/contracts/  Shared JSON Schemas / Pydantic models for plans, assets, jobs
infra/docker/    Docker images and docker-compose.yml
```

## Data flow

1. User creates a project in the web UI.
2. API copies/fingerprints assets into the local workspace and persists metadata.
3. User writes a brief and chooses presets/approval mode.
4. Worker probes assets, generates proxies, transcribes, and runs scene/quality analysis.
5. AI Director consumes brief + analysis + constitution and emits a structured edit plan.
6. Validator checks the plan against the schema, asset fingerprints, and safe ranges.
7. User approves the plan (or auto-approved if confidence threshold is met).
8. Worker renders preview/final outputs with FFmpeg.
9. QA runs technical and instruction-compliance checks.
10. Passing outputs move to `06_Final-Exports`; notifications are sent.

## Persistence

- SQLite (`data/cutdirective.db`) for MVP.
- Alembic migrations in `services/api/alembic`.
- Project workspaces live outside source control under `CutDirective/Projects/YYYY-MM-DD_Project-Name/`.

## Job stages

```text
DRAFT -> INGESTING -> ANALYZING -> PLAN_READY -> WAITING_FOR_APPROVAL
-> QUEUED -> RENDERING -> QA -> COMPLETED
| COMPLETED_WITH_WARNINGS | FAILED | CANCELED
```

## Security boundaries

- API runs as a non-root user inside Docker.
- Worker only writes inside approved roots.
- Secrets live in `.env`, never in source.
- AI provider receives only metadata, transcripts, contact sheets, and low-resolution proxies.
