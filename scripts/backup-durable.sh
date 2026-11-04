#!/bin/bash
# Klipr 1A-LITE Step 0 - durable backup.
# Difference from Phase 0 scripts/backup.sh:
# - Output goes to ~/workspace/klipr/backups/ by default, which lives in the
#   home directory that survives VM replacement. /var/lib/postgresql does NOT.
# - The backup directory is gitignored (see .gitignore), so dumps are kept on
#   disk, not committed to git.
# - A SHA-256 checksum and a storage manifest are written with every dump.
# - Offsite copy is NOT assumed. If KLIPR_BACKUP_REMOTE is set, the script
#   prints the remote and stops - the copy must be run explicitly with a
#   verified rclone/rsync config, and the restore must then be proven from
#   the offsite copy, not just from the local file.
# Usage: DB=klipr BACKUP_DIR=backups ./scripts/backup-durable.sh
#   Or, with a DATABASE_URL: KLIPR_DATABASE_URL=postgres://... ./scripts/backup-durable.sh
set -euo pipefail
DB="${DB:-klipr}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
mkdir -p "$BACKUP_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/${DB}-${TS}.sql"
MANIFEST="$BACKUP_DIR/${DB}-${TS}.manifest.txt"
if [ -n "${KLIPR_DATABASE_URL:-}" ]; then
  pg_dump "$KLIPR_DATABASE_URL" > "$OUT"
elif [ "$(id -u)" = "0" ] && command -v sudo >/dev/null 2>&1; then
  # Local VM proof: Postgres uses peer auth, so root must run pg_dump as postgres.
  # On a durable host with DATABASE_URL set, the branch above is used instead.
  sudo -u postgres pg_dump "$DB" > "$OUT"
else
  pg_dump "$DB" > "$OUT"
fi
# Storage manifest: files under storage/ if it exists, otherwise an empty manifest
# with a note, so a missing storage dir is visible, not silently treated as empty.
if [ -d storage ]; then
  find storage -type f | sort > "$MANIFEST"
else
  echo "# no storage/ directory at backup time" > "$MANIFEST"
fi
sha256sum "$OUT" > "$OUT.sha256"
chmod 755 "$BACKUP_DIR" 2>/dev/null || true
chmod 644 "$OUT" "$MANIFEST" "$OUT.sha256" 2>/dev/null || true
echo "backup: $OUT"
echo "manifest: $MANIFEST"
echo "checksum: $OUT.sha256"
if [ -n "${KLIPR_BACKUP_REMOTE:-}" ]; then
  echo "offsite remote is set - copy step must be run explicitly, not assumed"
  echo "remote: $KLIPR_BACKUP_REMOTE (not copied by this script without a verified config)"
fi
