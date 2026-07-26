#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-/tmp/cutdirective-backup}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Prefer values from .env if present
if [ -f "$REPO_DIR/.env" ]; then
  # shellcheck source=/dev/null
  set -a
  source "$REPO_DIR/.env"
  set +a
fi

WORKSPACE="${CUTDIRECTIVE_ROOT:-/home/ubuntu/CutDirective}"
DB_FILE="${DATABASE_URL:-sqlite:////home/ubuntu/repos/cutdirective-ai/data/cutdirective.db}"
DB_FILE="${DB_FILE#sqlite:///}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEST="$BACKUP_DIR/$TIMESTAMP"
mkdir -p "$DEST"

echo "Backing up workspace $WORKSPACE ..."
cp -r "$WORKSPACE" "$DEST/workspace"

echo "Backing up database $DB_FILE ..."
mkdir -p "$DEST/data"
if [ -f "$DB_FILE" ]; then
  cp "$DB_FILE" "$DEST/data/cutdirective.db"
else
  echo "Warning: database file not found at $DB_FILE" >&2
fi

echo "Backup complete: $DEST"
