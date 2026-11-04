#!/bin/bash
# Build the Step 6 Contabo deploy bundle, no secrets, from the repo.
# Output: ~/workspace/klipr-step6-deploy.tar.gz
# Excludes: .git, .env, backups, storage, __pycache__, .klipr_* token files.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="$HOME/workspace/klipr-step6-deploy.tar.gz"
tar --exclude=.git --exclude=.env --exclude=.env.* --exclude=backups --exclude=storage \
    --exclude=__pycache__ --exclude=crm --exclude=.klipr_admin_token --exclude=.klipr_user_tokens \
    --exclude=*.pyc -czf "$OUT" .
echo "bundle: $OUT"
ls -lh "$OUT"
sha256sum "$OUT"
echo "contents (first 100):"
tar -tzf "$OUT" | head -n 100
echo "secret check (should be empty):"
tar -tzf "$OUT" | grep -E "\.env$|backups|storage/|\.klipr_" || echo "no secrets in bundle"
