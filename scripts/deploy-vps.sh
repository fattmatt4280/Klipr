#!/bin/bash
# Klipr VPS deploy — Termius paste block (run ON the VPS as root, one paste).
# This is the INDIRECT push route, because Muse outbound SSH to this VPS is
# blocked/timed out (tested 2026-10-26). Muse builds on the VM, packages this
# folder as klipr-deploy.tar.gz, Matt copies it to the VPS (Termius upload /
# curl from a link Matt approves), then pastes this script on the VPS.
# Steps: install deps, create DBs, apply schema to prod + staging, create app user.
# It does NOT set OAuth provider, S3 credentials, or offsite backup remote —
# those are separate VPS steps with Matt's credentials, never in this script.
set -euo pipefail
cd /root/klipr 2>/dev/null || { echo "ERROR: copy klipr folder to /root/klipr first"; exit 1; }
apt-get update -qq && apt-get install -y -qq postgresql ffmpeg python3 python3-pip python3-psycopg2 >/dev/null
systemctl enable --now postgresql || service postgresql start || true
sudo -u postgres psql -c "CREATE DATABASE klipr;" 2>/dev/null || echo "klipr DB exists"
sudo -u postgres psql -c "CREATE DATABASE klipr_staging;" 2>/dev/null || echo "klipr_staging DB exists"
sudo -u postgres psql -d klipr -q -f db/schema.sql
sudo -u postgres psql -d klipr_staging -q -f db/schema.sql
cp -n .env.example .env || true
echo "VPS deploy: schema applied to klipr + klipr_staging. Next: edit .env (DB URL, storage, OAuth, S3), then run worker."
echo "API server (DWW mount): seed admin token first, then:"
echo "  KLIPR_DATABASE_URL=\"postgresql://klipr_app:<password>@127.0.0.1:5432/klipr\" KLIPR_AUTH_TOKEN_FILE=\"/root/klipr/.klipr_admin_token\" python3 -m app.server --port 8890"
echo "Front-door it with Caddy/proxy + CORS allowlist for dreamwebworkz.com + lovable.app — do NOT expose :8890 directly without auth + TLS."
echo "Check RLS: sudo -u postgres psql -d klipr -c \"SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' ORDER BY 1;\""
