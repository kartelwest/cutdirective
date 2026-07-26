# Testing

## Commands

```bash
# Start the stack
cd /home/ubuntu/repos/cutdirective-ai
docker compose -f infra/docker-compose.yml up -d --build

# End-to-end integration test (expects API at http://localhost:8000)
./scripts/integration-test.sh

# Generate the pilot fixture used by the integration test
./scripts/test-media/generate_pilot_clip.sh

# Frontend checks
cd apps/web
pnpm type-check
pnpm lint
```

## Integration test coverage

`scripts/integration-test.sh` exercises the full pipeline:
1. Health check (`GET /health`)
2. Project creation (`POST /projects`)
3. Asset upload (`POST /projects/{id}/assets`)
4. Media analysis (`POST /projects/{id}/analyze`)
5. Edit-plan generation (`POST /projects/{id}/plan`)
6. Final render (`POST /projects/{id}/render`) with per-output QA assertions
7. Packaging (`POST /projects/{id}/package`)
8. Local delivery (`POST /projects/{id}/deliver`)
9. Notifications (`GET /projects/{id}/notifications`)

The test fails if any stage returns an error or if QA does not pass.

## Test media

Small, legally usable fixtures are generated under `sample-data/` by `scripts/test-media/generate_pilot_clip.sh`. Do not commit large or private media.

## Acceptance

See the MVP acceptance criteria in the master implementation prompt. Each gate has exit conditions that must pass before moving to the next gate.
