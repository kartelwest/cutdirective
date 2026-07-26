# Architecture Decision Records

## 2026-07-26 — Repository bootstrap
- Created a standalone repository `cutdirective-ai` with no dependency on KarayModels.
- Chose a monorepo layout (`apps/web`, `services/api`, `services/worker`, `packages/contracts`, `infra/docker`) so the front-end, back-end, and shared contracts can evolve independently while sharing Docker Compose orchestration.
- Could not create a remote GitHub repository through the integration token; the repository is local-only for now. Remote can be added later without changing code.

## 2026-07-26 — Stack for version one
- Next.js + TypeScript for the web UI (familiar, App Router, good local-first desktop feel).
- FastAPI + Pydantic + SQLAlchemy + Alembic for the API.
- SQLite for the MVP; repository interfaces use SQLAlchemy so PostgreSQL can be swapped later.
- FFmpeg/ffprobe for all deterministic rendering and probing.
- `uv` for Python environment and dependency management.
- Docker Compose for local development and internal deployment.

## 2026-07-26 — File safety defaults
- All file operations restricted to the configured `CUTDIRECTIVE_ROOT`.
- Original files are copied into `01_Originals` by default; reference-in-place is an explicit advanced option.
- Paths are validated for traversal and symlink escape.
- Checksums (SHA-256) are recorded for every source file.
- Exports use unique versioned names and never overwrite previous approved versions.

## 2026-07-26 — AI safety
- The AI model emits JSON only; it never emits shell commands.
- The renderer translates an approved plan into FFmpeg commands through deterministic code.
- All operations come from a whitelist with typed Pydantic models.
- Invalid model output is rejected, repaired up to a limit, then escalated to human review.
