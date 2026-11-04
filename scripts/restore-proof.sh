#!/bin/bash
# Klipr 1A-LITE - restore proof, with DATABASE_URL mode.
# Restores a backup into a throwaway test DB, verifies the table count,
# then drops the test DB. This proves restore works; it does NOT prove
# offsite restore until the offsite copy step is configured and tested
# from the offsite copy.
# Usage: ./scripts/restore-proof.sh backups/klipr-YYYYMMDDTHHMMSSZ.sql [expected_table_count]
#   Default expected count is 23 (Phase 0). Pass a different count after a
#   schema change, e.g. 29 for 1A-LITE, instead of editing this script.
# Modes:
#   1. KLIPR_DATABASE_URL set (managed DB, Supabase/Neon, etc.):
#      - pg_dump / psql are run as the current user, using the URL.
#      - The test DB is created/dropped via an admin connection derived
#        from KLIPR_DATABASE_URL by replacing the database name with
#        "postgres". The URL user must have CREATEDB privilege on that
#        host (managed project owners normally do).
#      - The URL itself is NEVER echoed, logged, or written to a file by
#        this script. It is read from the environment only.
#      - The backup file is read by the local psql client, so no /tmp
#        copy is needed in this mode.
#   2. KLIPR_DATABASE_URL NOT set (local Postgres):
#      - psql is run as postgres when run as root (peer auth), else local.
#      - Postgres (running as postgres user) must be able to READ the
#        backup file. The workspace repo directory is 2770, so postgres
#        cannot traverse into backups/ directly. The backup is copied
#        to /tmp with mode 644 for the restore, then the temp copy is
#        deleted. The original backup is untouched.
#   In both modes, a trap drops the test DB on failure, so a failed
#   restore does not leave a test DB behind.
set -euo pipefail
SQL="${1:?usage: restore-proof.sh <backup.sql> [expected_table_count]}"
EXPECTED="${2:-23}"
TESTDB="klipr_restore_test"

derive_url() {
  # $1 = target database name. Reads KLIPR_DATABASE_URL from the
  # environment only, never from a command-line argument, and prints
  # only the derived URL (callers must not echo it).
  TARGET_DB="$1" python3 -c "
import os, urllib.parse
u = urllib.parse.urlparse(os.environ['KLIPR_DATABASE_URL'])
print(urllib.parse.urlunparse(u._replace(path='/' + os.environ['TARGET_DB'])))
"
}

if [ -n "${KLIPR_DATABASE_URL:-}" ]; then
  MODE="database_url"
  ADMIN_URL="$(derive_url postgres)"
  TEST_URL="$(derive_url "$TESTDB")"
  # Admin / test helpers for DATABASE_URL mode.
  admin_psql() { psql "$ADMIN_URL" "$@"; }
  test_psql() { psql "$TEST_URL" "$@"; }
  SQL_FOR_PSQL="$SQL"
  TMP_SQL=""
else
  MODE="local"
  if [ "$(id -u)" = "0" ] && command -v sudo >/dev/null 2>&1; then
    PSQL="sudo -u postgres psql"
  else
    PSQL="psql"
  fi
  admin_psql() { $PSQL "$@"; }
  test_psql() { $PSQL -d "$TESTDB" "$@"; }
  # Copy to /tmp so the postgres user can read it (see header).
  TMP_SQL="$(mktemp /tmp/klipr-restore-XXXXXX.sql)"
  cp "$SQL" "$TMP_SQL"
  chmod 644 "$TMP_SQL"
  SQL_FOR_PSQL="$TMP_SQL"
fi

cleanup() {
  if [ -n "${TMP_SQL:-}" ]; then
    rm -f "$TMP_SQL"
  fi
  if [ "$MODE" = "database_url" ]; then
    psql "$ADMIN_URL" -c "DROP DATABASE IF EXISTS $TESTDB;" >/dev/null 2>&1 || true
  else
    $PSQL -c "DROP DATABASE IF EXISTS $TESTDB;" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "restore-proof: mode=$MODE, expected table count=$EXPECTED"
if [ "$MODE" = "database_url" ]; then
  admin_psql -c "DROP DATABASE IF EXISTS $TESTDB;" -c "CREATE DATABASE $TESTDB;"
  test_psql -q -f "$SQL_FOR_PSQL"
  COUNT="$(test_psql -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")"
else
  admin_psql -c "DROP DATABASE IF EXISTS $TESTDB;" -c "CREATE DATABASE $TESTDB;"
  test_psql -q -f "$SQL_FOR_PSQL"
  COUNT="$(test_psql -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")"
fi
echo "restore-proof: table count in restored DB = $COUNT, expected = $EXPECTED"
if [ "$MODE" = "database_url" ]; then
  admin_psql -c "DROP DATABASE $TESTDB;"
else
  admin_psql -c "DROP DATABASE $TESTDB;"
fi
trap - EXIT
if [ -n "${TMP_SQL:-}" ]; then
  rm -f "$TMP_SQL"
fi
if [ "$COUNT" != "$EXPECTED" ]; then
  echo "restore-proof: FAILED - table count mismatch"
  exit 1
fi
echo "restore-proof: OK (table count matches, test DB dropped)"
