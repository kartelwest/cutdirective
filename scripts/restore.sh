#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-/tmp/cutdirective-backup}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -f "$REPO_DIR/.env" ]; then
  # shellcheck source=/dev/null
  set -a
  source "$REPO_DIR/.env"
  set +a
fi

WORKSPACE="${CUTDIRECTIVE_ROOT:-/home/ubuntu/CutDirective}"
DB_FILE="${DATABASE_URL:-sqlite:////home/ubuntu/repos/cutdirective-ai/data/cutdirective.db}"
DB_FILE="${DB_FILE#sqlite:///}"

LATEST=$(ls -1 "$BACKUP_DIR" | sort | tail -n 1)
if [ -z "$LATEST" ]; then
  echo "No backups found in $BACKUP_DIR" >&2
  exit 1
fi

SRC="$BACKUP_DIR/$LATEST"
echo "Restoring from $SRC ..."

echo "Restoring workspace ..."
mkdir -p "$WORKSPACE"
rm -rf "$WORKSPACE" && cp -r "$SRC/workspace" "$WORKSPACE"

echo "Restoring database ..."
mkdir -p "$(dirname "$DB_FILE")"
if [ -f "$SRC/data/cutdirective.db" ]; then
  cp "$SRC/data/cutdirective.db" "$DB_FILE"
else
  echo "Warning: database backup not found in $SRC/data" >&2
fi

echo "Restore complete from $SRC"
