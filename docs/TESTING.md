# Testing

## Commands

```bash
# Python tests
cd /home/ubuntu/repos/cutdirective-ai
uv run pytest

# Frontend checks
cd apps/web
pnpm type-check
pnpm lint
```

## Test media

Small, legally usable fixtures are generated under `tests/golden_media/` by `scripts/development/generate-fixtures.sh`. Do not commit large or private media.

## Acceptance

See the MVP acceptance criteria in the master implementation prompt. Each gate has exit conditions that must pass before moving to the next gate.
