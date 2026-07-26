# Security

## Threat model

- AI model manipulation: the model is never allowed to emit shell commands or file paths. It emits JSON that is validated and translated by trusted code.
- Path traversal: all file paths are resolved relative to the configured `CUTDIRECTIVE_ROOT` and verified to stay within it.
- Original media destruction: originals are opened read-only; exports use versioned names and never overwrite.
- Secret leakage: `.env` is gitignored; logs do not include API keys or SMTP credentials.
- Provider rejection of content: local transcription and analysis fallback are architecturally pluggable.

## Controls

- JSON Schema + Pydantic validation for every AI plan.
- Whitelisted operation registry; FFmpeg commands built by deterministic code.
- File checksums and immutable originals.
- Audit events for destructive operations.
- Watermarked previews when configured.
