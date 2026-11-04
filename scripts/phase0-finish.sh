#!/bin/bash
# Klipr Phase 0 FINISH deploy — run ON the Contabo VPS as root, via Termius.
# Phone-pasteable: edit ONLY the 3 variables at the top, then paste the whole block.
# It does NOT set production OAuth, S3, Redis, or offsite backup remote — those
# remain VPS/later steps (see output at the end). Local admin token is the Phase 0
# proof auth, NOT production OAuth. Never paste the printed admin token into chat
# unprompted — save it in your password manager, you need it for the DWW mount page.
#
# Variables Matt edits (one line each, before pasting):
#   BUNDLE_URL — the Muse storage link for klipr-deploy.tar.gz (from Muse chat)
#   DB_PASSWORD — letters + numbers only, no $ ' " spaces (avoids shell/URL breakage)
#   KLIPR_DOMAIN — optional, e.g. klipr.yourdomain.com . Leave empty "" to skip
#                  Caddy for now (API stays localhost-only, DWW will show unreachable
#                  until a front door is added). If you set a domain, its DNS A record
#                  MUST point to 217.216.94.215 BEFORE you run this, or Caddy cert will fail.
set -euo pipefail
# You can also pass these as env vars in one paste, e.g.:
#   BUNDLE_URL="https://..." DB_PASSWORD="MyPass123" KLIPR_DOMAIN="" bash /root/klipr/scripts/phase0-finish.sh
# If env vars are not set, edit the 3 lines below instead.
BUNDLE_URL="${BUNDLE_URL:-__BUNDLE_URL__}"
DB_PASSWORD="${DB_PASSWORD:-__CHOOSE_A_PASSWORD_LETTERS_NUMBERS_ONLY__}"
KLIPR_DOMAIN="${KLIPR_DOMAIN:-}"
# --- do not edit below this line ---
if [ "$BUNDLE_URL" = "__BUNDLE_URL__" ] || [ "$DB_PASSWORD" = "__CHOOSE_A_PASSWORD_LETTERS_NUMBERS_ONLY__" ]; then
  echo "STOP: edit BUNDLE_URL and DB_PASSWORD at the top first, then paste again."
  exit 1
fi
echo "== 1. download + extract bundle =="
cd /root
curl -L -o klipr-deploy.tar.gz "$BUNDLE_URL"
tar -xzf klipr-deploy.tar.gz
cd /root/klipr
echo "== 2. system deps =="
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql ffmpeg python3 python3-psycopg2 curl
systemctl enable --now postgresql || service postgresql start || true
echo "== 3. databases + schema (prod + staging) =="
sudo -u postgres psql -c "CREATE DATABASE klipr;" 2>/dev/null || echo "klipr DB exists"
sudo -u postgres psql -c "CREATE DATABASE klipr_staging;" 2>/dev/null || echo "klipr_staging DB exists"
sudo -u postgres psql -d klipr -q -f db/schema.sql
sudo -u postgres psql -d klipr_staging -q -f db/schema.sql
echo "== 4. app role + grants =="
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='klipr_app'" | grep -q 1; then
  sudo -u postgres psql -c "ALTER ROLE klipr_app WITH PASSWORD '$DB_PASSWORD';"
  echo "klipr_app role exists — password updated"
else
  sudo -u postgres psql -c "CREATE ROLE klipr_app LOGIN PASSWORD '$DB_PASSWORD';"
fi
sudo -u postgres psql -d klipr -c "GRANT USAGE ON SCHEMA public TO klipr_app; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO klipr_app; GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO klipr_app;"
sudo -u postgres psql -d klipr_staging -c "GRANT USAGE ON SCHEMA public TO klipr_app; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO klipr_app; GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO klipr_app;"
echo "== 5. .env (no secrets in git, this file stays on the VPS only) =="
cat > /root/klipr/.env <<EOF
KLIPR_ENV=production
KLIPR_DATABASE_URL=postgresql://klipr_app:${DB_PASSWORD}@127.0.0.1:5432/klipr
KLIPR_STORAGE_DRIVER=local
KLIPR_STORAGE_ROOT=/root/klipr/storage
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
KLIPR_BILLING_ENABLED=false
KLIPR_CRM_LOG=/root/klipr/crm/events.jsonl
KLIPR_AUTH_TOKEN_FILE=/root/klipr/.klipr_admin_token
EOF
chmod 600 /root/klipr/.env
mkdir -p /root/klipr/storage /root/klipr/crm /root/klipr-backups
echo "== 6. admin token (SAVE THIS — printed once, hash only is stored) =="
if [ -f /root/klipr/.klipr_admin_token ]; then
  echo "Admin token file already exists — NOT re-issued. Use the token you saved on first run."
else
  python3 -c "
import sys; sys.path.insert(0, '/root/klipr')
from app.auth import Auth
tok = Auth('/root/klipr/.klipr_admin_token').seed_admin_token()
print('KLIPR_ADMIN_TOKEN=' + tok)
print('SAVE THIS TOKEN IN YOUR PASSWORD MANAGER NOW. It is not stored in plain text anywhere.')
"
fi
echo "== 7. systemd services: klipr-api + klipr-worker =="
cat > /etc/systemd/system/klipr-api.service <<'EOF'
[Unit]
Description=Klipr API (Phase 0 test)
After=network.target postgresql.service
[Service]
WorkingDirectory=/root/klipr
EnvironmentFile=/root/klipr/.env
ExecStart=/usr/bin/python3 -m app.server --port 8890 --host 127.0.0.1
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/klipr-worker.service <<'EOF'
[Unit]
Description=Klipr Worker (Phase 0 test)
After=network.target postgresql.service
[Service]
WorkingDirectory=/root/klipr
EnvironmentFile=/root/klipr/.env
ExecStart=/bin/bash -c 'while true; do python3 -m app.worker --once || true; sleep 5; done'
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now klipr-api klipr-worker
echo "== 8. daily backup cron (local only until offsite remote is chosen) =="
( crontab -l 2>/dev/null | grep -v "klipr/scripts/backup.sh" ; echo "0 3 * * * cd /root/klipr && BACKUP_DIR=/root/klipr-backups DB=klipr bash scripts/backup.sh >> /root/klipr-backups.log 2>&1" ) | crontab -
echo "== 9. Caddy front door (only if KLIPR_DOMAIN is set) =="
if [ -n "$KLIPR_DOMAIN" ]; then
  apt-get install -y -qq caddy
  printf "%s {\n  reverse_proxy 127.0.0.1:8890\n}\n" "$KLIPR_DOMAIN" > /etc/caddy/Caddyfile
  systemctl enable --now caddy
  systemctl reload caddy || systemctl restart caddy
  echo "Caddy configured for $KLIPR_DOMAIN -> 127.0.0.1:8890"
else
  echo "KLIPR_DOMAIN empty — Caddy skipped. API is localhost-only (127.0.0.1:8890)."
  echo "DWW mount will show API unreachable until you add a domain + front door."
fi
echo "== 10. verify =="
sleep 3
systemctl is-active klipr-api klipr-worker || true
curl -s http://127.0.0.1:8890/health || echo "API health check failed — check: systemctl status klipr-api"
sudo -u postgres psql -d klipr -t -c "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND rowsecurity=true;"
echo "Expected RLS count: 23"
echo ""
echo "PHASE 0 DEPLOY DONE (except the items below, which are still open by design):"
echo "- Production OAuth provider: NOT wired (local admin token is Phase 0 proof only)"
echo "- S3/R2/B2 storage: NOT configured (local storage driver in use)"
echo "- Redis queue swap: NOT done (Postgres jobs table in use)"
echo "- Offsite backup remote: NOT configured (local /root/klipr-backups only)"
echo "- Next.js front end: NOT built (API + DWW mount page only)"
echo "Next: DWW mount page (hidden, Lovable Publish) + Tattoo Reveal reference set for Phase 1."
