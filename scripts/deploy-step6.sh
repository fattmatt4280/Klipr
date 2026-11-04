#!/bin/bash
# Klipr Step 6 Contabo deploy, run on the VPS as root, in /root/klipr.
# This script does NOT contain secrets. KLIPR_DATABASE_URL and tokens are
# supplied by Matt on the VPS only, in /root/klipr/.env (mode 600).
# Prerequisites on the VPS: Ubuntu 24.04, root login working (Contabo reset
# if needed), domain DNS pointing to this VPS IP if Caddy TLS is wanted.
# Usage, in order:
#   1. Copy the Step 6 bundle to /root/klipr and extract it there.
#   2. bash scripts/deploy-step6.sh
#   3. Edit /root/klipr/.env (see .env.example in the repo) with the real
#      Supabase KLIPR_DATABASE_URL, then chmod 600 /root/klipr/.env
#   4. Create the operator user + brand in Supabase (see docs/STEP6-DEPLOY.md),
#      then seed a user token: KLIPR_USER_TOKEN_FILE=/root/klipr/.klipr_user_tokens
#      /root/klipr/.venv/bin/python scripts/seed_user_tokens.py <user_id>
#      Copy that token once into the DWW UI session. Never paste it in chat.
#   5. systemctl enable --now klipr-api klipr-worker
#   6. Set up Caddy from deploy/Caddyfile.template with your domain, then
#      systemctl reload caddy, and test health over HTTPS.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Installing system deps (python3, venv, ffmpeg, postgresql-client-17 for backups)..."
apt-get update
apt-get install -y python3 python3-venv python3-pip ffmpeg curl
# PostgreSQL 17 client, for pg_dump >= server 17.11, via PGDG (same as VM proof).
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg
chmod 644 /usr/share/keyrings/postgresql-keyring.gpg
cp /usr/share/keyrings/postgresql-keyring.gpg /etc/apt/trusted.gpg.d/postgresql.gpg
chmod 644 /etc/apt/trusted.gpg.d/postgresql.gpg
echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt noble-pgdg main" > /etc/apt/sources.list.d/pgdg.list
apt-get update -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/pgdg.list -o Dir::Etc::sourceparts=/dev/null || true
apt-get install -y postgresql-client-17 || echo "WARNING: postgresql-client-17 install failed, backups need pg_dump >=17.11"
echo "Creating venv and installing requirements..."
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
mkdir -p storage crm
chmod 700 storage || true
echo "Installing systemd units..."
cp deploy/systemd/klipr-api.service /etc/systemd/system/klipr-api.service
cp deploy/systemd/klipr-worker.service /etc/systemd/system/klipr-worker.service
systemctl daemon-reload
echo "Deploy script done. Next: edit .env (mode 600), seed user token, enable services, set up Caddy."
echo "Do NOT start the API without a real KLIPR_DATABASE_URL in .env, and do NOT expose port 8890 directly without Caddy + TLS."
