# Klipr Step 6 — DWW UI + Contabo deploy (built 2026-11-04, NOT deployed yet)

This is the validation build, not the Lovable duplicate. Matt's plan
2026-11-04: validate with Muse first, then duplicate through Lovable
once the functionality is proven, so the Lovable build is not exploratory.
Do NOT start a Lovable duplicate from this doc.

## Boundary, unchanged from DWW-MOUNT.md

- Klipr stays its own repo, DB, and routes. DWW gets only a hidden page.
- DWW / Lovable does NOT run Python, FFmpeg, or a worker. DWW is the UI,
  Contabo (or VM for proof) is the engine, over HTTPS API only.
- No Klipr code, DB credentials, or secrets go into DWW. API base + user
  token are entered per session in the DWW page, sessionStorage only.

## What was built in this bundle

- Download endpoint: GET /renders/<id>/file, user token only, serves the
  finished MP4 as an attachment. Without this, a DWW UI could list renders
  but could not hand Matt the file to post manually.
- DWW Step 6 UI: dww-mount/klipr-step6.html, hidden page, noindex, no menu.
  Setup (API base + user token, session only), brands dropdown, upload
  photos + activate, project + blueprint form, render + job check, renders
  list + download, record external post / metric snapshot / inquiry,
  weekly report. Uploads use base64 JSON for validation (photos under
  ~5 MB); a production Lovable build should use multipart / signed upload.
- Contabo deploy: scripts/deploy-step6.sh, deploy/systemd/klipr-api.service,
  deploy/systemd/klipr-worker.service (loop, --once every 10s),
  deploy/Caddyfile.template, scripts/worker-loop.sh.
  No local Postgres is created in this bundle — Step 6 uses the managed
  Supabase DB, not a VPS Postgres. VPS storage is local disk under
  /root/klipr/storage for the single-operator proof; S3/R2 is still deferred.

## Blockers, in order — do not skip 1

1. Contabo root login is still blocked (since 2026-10-28, password rejected).
   Reset credentials in the Contabo panel with a NEW password, wait 3-5 min,
   try one root host only (217.216.94.215). VNC console is the fallback.
   Until root works, this bundle cannot be deployed to Contabo, and the
   DWW UI will correctly show API unreachable.
2. DWW Publish is by Matt: add dww-mount/klipr-step6.html to DWW in Lovable
   as a hidden page, set API base to the deployed Klipr HTTPS URL, Publish.
   Lovable secret changes need a redeploy to take effect.
3. Operator user + token must be created on the backend host, not in chat:
   insert a users row + brands row in Supabase, then run
   KLIPR_USER_TOKEN_FILE=/root/klipr/.klipr_user_tokens
   /root/klipr/.venv/bin/python scripts/seed_user_tokens.py <user_id>
   Copy the printed token once into the DWW UI session. Never paste it
   in chat, never commit the token file.

## Deploy steps, Termius paste, in order

1. Copy the Step 6 bundle to /root/klipr and extract it there.
   Bundle file: klipr-step6-deploy.tar.gz (built from the repo, no .env,
   no backups, no storage, no __pycache__, no .git).
2. `bash scripts/deploy-step6.sh`
3. Create /root/klipr/.env from .env.example, with the real Supabase
   KLIPR_DATABASE_URL, plus:
   KLIPR_USER_TOKEN_FILE=/root/klipr/.klipr_user_tokens
   KLIPR_STORAGE_ROOT=/root/klipr/storage
   Then `chmod 600 /root/klipr/.env`
4. Seed the operator user token (step 3 above), save it only in the DWW
   UI session, not in a file you share.
5. `systemctl enable --now klipr-api klipr-worker`
   Check: `systemctl status klipr-api klipr-worker`, and
   `curl http://127.0.0.1:8890/health` on the VPS should return ok, phase 6.
6. Caddy: copy deploy/Caddyfile.template to /etc/caddy/Caddyfile, replace
   KLIPR_DOMAIN with your domain (DNS pointing to the VPS first),
   `systemctl reload caddy`, then test health over HTTPS from your phone.
7. DWW: add the Step 6 UI as a hidden page, Publish, open it, enter API
   base + user token for that session, load brands, upload, activate,
   project, render, download, post manually, record post/metrics/inquiry.

## Verification after deploy (do not claim live until these pass)

- Health over HTTPS returns ok, phase 6.
- Brands list with a user token returns only that user's brands.
- Upload + activate + project + render + download works from the DWW page
  on your phone, with a real Shyftd.ink asset set, not test colors.
- Weekly report shows the real post, metrics, and inquiries by CTA.
- Backup: run scripts/backup-durable.sh with PATH=/usr/lib/postgresql/17/bin
  first, and scripts/restore-proof.sh with expected count 29, as in Step 6.
