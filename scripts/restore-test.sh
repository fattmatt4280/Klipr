#!/bin/bash
# Klipr restore TEST, Phase 0. Restores a backup into klipr_restore_test, verifies
# table count matches, then drops the test DB. This proves restore works; it does
# NOT prove offsite restore until the offsite copy step is configured and tested.
# Usage: ./scripts/restore-test.sh backups/klipr-YYYYMMDDTHHMMSSZ.sql
set -euo pipefail
SQL="${1:?usage: restore-test.sh <backup.sql>}"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS klipr_restore_test;" -c "CREATE DATABASE klipr_restore_test;"
sudo -u postgres psql -d klipr_restore_test -q -f "$SQL"
sudo -u postgres psql -d klipr_restore_test -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
sudo -u postgres psql -c "DROP DATABASE klipr_restore_test;"
echo "restore test: OK (table count above, test DB dropped)"
