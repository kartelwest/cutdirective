# AI Director

## Responsibility

The AI Director decides what the edit should be. It does not execute media commands.

## Inputs

- Editing constitution
- Brand/creator preset
- Platform preset
- Project brief (natural language + structured fields)
- Asset registry and fingerprints
- Media metadata
- Timestamped transcript
- Scene/shot analysis
- Quality scores
- Sampled-frame descriptions / low-resolution visual inputs

## Output

A JSON edit plan matching the versioned schema (see `EDIT_PLAN_SCHEMA.md`).

## Repair loop

1. Validate model output.
2. If invalid, return validation errors to the model with the original context.
3. Revalidate.
4. After a configured number of failures, stop and escalate to human review.

## Safety

- Output must never contain executable shell commands.
- All timecodes and asset IDs must be validated against real sources.
- Confidence and review flags are always included.
