#!/bin/bash
# Klipr backup, Phase 0. Dumps DB + storage manifest to BACKUP_DIR.
# Offsite = copy BACKUP_DIR to a separate provider (R2/B2/rsync target) via
# KLIPR_BACKUP_REMOTE (rclone/rsync destination) — that remote is NOT configured
# in the VM proof, so the proof backup is local-only and must be labelled as such.
# Usage: BACKUP_DIR=/path/to/backups DB=klipr ./scripts/backup.sh
set -euo pipefail
DB="${DB:-klipr}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
mkdir -p "$BACKUP_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
sudo -u postgres pg_dump "$DB" > "$BACKUP_DIR/${DB}-${TS}.sql"
find storage -type f 2>/dev/null | sort > "$BACKUP_DIR/${DB}-${TS}.manifest.txt" || true
chmod 755 "$BACKUP_DIR" 2>/dev/null || true
chmod 644 "$BACKUP_DIR/${DB}-${TS}.sql" "$BACKUP_DIR/${DB}-${TS}.manifest.txt" 2>/dev/null || true
echo "backup: $BACKUP_DIR/${DB}-${TS}.sql"
if [ -n "${KLIPR_BACKUP_REMOTE:-}" ]; then
  echo "offsite remote is set — copy step must be run explicitly, not assumed"
  echo "remote: $KLIPR_BACKUP_REMOTE (not copied by this script without a verified rclone/rsync config)"
fi
