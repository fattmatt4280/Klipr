#!/bin/bash
# Klipr 1A-LITE Step 0 - minimal automated test runner.
# Stdlib unittest only, no pytest required. DB tests are skipped when no
# Postgres is reachable, so this runner passes on a clean checkout and
# still proves the DB tests when a durable DB is configured.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v "$@"
