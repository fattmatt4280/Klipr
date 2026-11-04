# Klipr in DWW — test shell, separate repo (2026-10-26)

Decision by Matt 2026-10-26 ~06:58 EDT: test Klipr in DWW (dreamwebworkz.com,
Lovable command center), but keep Klipr separate.

## Boundary — this is the whole point, do not blur it
- Klipr repo = ~/workspace/klipr/ (this folder). Own DB schema, own routes,
  own adapters, own templates. It never imports Command Center / DWW code.
- DWW repo = Lovable dreamwebworkz project (Hostinger-hosted, Lovable-published,
  GitHub-connected Sept 28, pages in public/). DWW gets ONLY a thin mount page:
  dww-mount/klipr-mount.html in this folder, to be added to DWW as a hidden page.
- DWW mount talks to Klipr ONLY over HTTPS API (app/server.py). No DB credentials,
  no pipeline code, no FFmpeg, no secrets in the mount page. API base URL and
  admin token are set at runtime (Lovable secrets / session input), never baked in.
- Pull-out later = point a new domain at the Klipr repo, move its DB + storage,
  delete the DWW mount page. No rewrite, because DWW never owned Klipr code.

## What DWW already gives for testing (verified from record)
- Hosted + published via Lovable, phone-accessible, Google sign-in gate already
  used for DWW studio/editor pages (dreamtattoocompany@gmail.com pattern).
- Hidden-page pattern already used for the command-center dashboard (no menu,
  noindex, link-only). Mount page must follow the same pattern: hidden, noindex,
  no menu link, no sharing.
- CORS allowlist pattern already used for the Contabo CRM proxy: dreamwebworkz.com
  + lovable.app domain. Klipr API uses the same allowlist (see app/server.py).

## What DWW does NOT give (do not pretend otherwise)
- Lovable does NOT run Python, FFmpeg, Postgres job workers, or Redis.
  Klipr API + worker + FFmpeg must live on a real server: Contabo VPS (deploy
  bundle) or this VM for proof. DWW is the UI shell, Contabo/VM is the engine.
- DWW mount is NOT live until BOTH: (1) Klipr API is deployed + reachable over
  HTTPS with a front door (Caddy/proxy, like tts.fridgespy.com), and (2) Matt
  adds the mount page to DWW and hits Lovable Publish.
  Until then, the mount page will show "API unreachable" — that is expected,
  not a bug in the mount.

## Files in this setup
- app/server.py — minimal Klipr API (stdlib http.server, psycopg2 for DB).
  Endpoints: GET /health (public), GET /templates, GET /brands, GET /jobs,
  POST /jobs (enqueue). Protected endpoints require Bearer admin token.
  CORS: only dreamwebworkz.com, *.lovable.app, localhost for VM proof.
- dww-mount/klipr-mount.html — thin test page. Inputs: API base URL + admin
  token (sessionStorage only, cleared on tab close, never in code/localStorage).
  Buttons: Check health, List templates, List jobs, Enqueue test analyze job.
  Shows raw API status, not a finished editor. Editor is Phase 3, not this mount.
- scripts/deploy-vps.sh — updated to also start the API server (see below).
  VPS step still needs Matt's Termius paste, because Muse SSH is blocked.

## Steps for Matt (in order, do not skip 1)
1. Deploy Klipr API to Contabo via Termius bundle (klipr-deploy.tar.gz):
   copy bundle to /root/klipr, paste scripts/deploy-vps.sh, then start API:
   KLIPR_DATABASE_URL="postgresql://klipr_app:<password>@127.0.0.1:5432/klipr" \
   KLIPR_AUTH_TOKEN_FILE="/root/klipr/.klipr_admin_token" \
   python3 -m app.server --port 8890
   Then put a Caddy/proxy front door in front of it with CORS allowlist, same
   pattern as the CRM proxy. Do NOT expose :8890 directly without auth + TLS.
   Note: admin token must be seeded first (see app/auth.py seed_admin_token)
   and kept by Matt only — never paste it into chat or into the mount page.
2. Add dww-mount/klipr-mount.html to the DWW Lovable project as a hidden page
   (no menu, noindex), set its API base to the Klipr API HTTPS URL, Publish in Lovable.
   Lovable secret changes need a redeploy to take effect (lesson from Oct 7).
3. Phone test: open the hidden mount page, enter API base + token for that
   session, Check health -> List templates -> Enqueue test analyze job -> List jobs
   should show it done (worker must be running on the same server as the API).
4. Phase 1 still gates on the Tattoo Reveal reference set — DWW mount does not
   replace that gate, it only makes testing the API easier once Phase 1 is built.

## Voicebox in this setup (deferred, not blocking)
- Phase 0/1 needs no voice. Voicebox stays a remote adapter: Klipr -> Contabo
  voice service (Kokoro live at tts.fridgespy.com:8001, or Qwen Voicebox
  localhost:8765 once its Termius installer is run + front-doored).
- DWW mount does NOT embed Voicebox. When voice is built, the Klipr API calls
  the voice adapter, which calls Contabo — DWW never talks to Voicebox directly.
- If the final standalone Klipr app is hosted on Contabo, voice becomes local
  again (localhost service) — easier at launch than the DWW remote interim.
