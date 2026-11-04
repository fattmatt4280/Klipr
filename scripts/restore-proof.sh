#!/bin/bash
# Klipr 1A-LITE Step 0 - restore proof.
# Restores a backup into a throwaway test DB, verifies the table count,
# then drops the test DB. This proves restore works; it does NOT prove
# offsite restore until the offsite copy step is configured and tested
# from the offsite copy.
# Usage: ./scripts/restore-proof.sh backups/klipr-YYYYMMDDTHHMMSSZ.sql [expected_table_count]
#   Default expected count is 23 (Phase 0). Pass a different count after a
#   schema change, e.g. 29 for 1A-LITE, instead of editing this script.
set -euo pipefail
SQL="${1:?usage: restore-proof.sh <backup.sql> [expected_table_count]}"
EXPECTED="${2:-23}"
TESTDB="klipr_restore_test"
if [ -n "${KLIPR_DATABASE_URL:-}" ]; then
  echo "restore-proof: DATABASE_URL mode is not supported in this proof script - run it on the Postgres host with local psql access"
  exit 2
fi
# PSQL helper: use DATABASE_URL mode only if explicitly set (not supported
# for restore-proof, see above), otherwise run as postgres when root, else local.
if [ "$(id -u)" = "0" ] && command -v sudo >/dev/null 2>&1; then
  PSQL="sudo -u postgres psql"
else
  PSQL="psql"
fi
# Postgres (running as postgres user) must be able to READ the backup file.
# The workspace repo directory is 2770, so postgres cannot traverse into
# backups/ directly. Copy the backup to /tmp with world-readable mode for
# the restore, then delete the temp copy. The original backup is untouched.
# Also trap cleanup so a failed restore does not leave a test DB behind.
TMP_SQL="$(mktemp /tmp/klipr-restore-XXXXXX.sql)"
cp "$SQL" "$TMP_SQL"
chmod 644 "$TMP_SQL"
cleanup() {
  rm -f "$TMP_SQL"
  $PSQL -c "DROP DATABASE IF EXISTS $TESTDB;" >/dev/null 2>&1 || true
}
trap cleanup EXIT
$PSQL -c "DROP DATABASE IF EXISTS $TESTDB;" -c "CREATE DATABASE $TESTDB;"
$PSQL -d "$TESTDB" -q -f "$TMP_SQL"
COUNT="$($PSQL -d "$TESTDB" -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")"
echo "restore-proof: table count in restored DB = $COUNT, expected = $EXPECTED"
$PSQL -c "DROP DATABASE $TESTDB;"
if [ "$COUNT" != "$EXPECTED" ]; then
  echo "restore-proof: FAILED - table count mismatch"
  exit 1
fi
echo "restore-proof: OK (table count matches, test DB dropped)"
