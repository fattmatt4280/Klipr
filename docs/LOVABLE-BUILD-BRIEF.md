# Klipr — Lovable build brief (UI ONLY, Contabo stays the engine)

Status: GREEN-LIT by Matt 2026-11-06 — build the UI in Lovable from
this brief. Validation gate (§8): HTTPS health met, real first
Shyftd.ink video rendered + downloaded 2026-11-06 (Ghostface arm,
4 photos, 8s). Posting + metrics + weekly-report check still to do
— Matt chose to proceed with the UI build in parallel.
Strategy chosen by Matt 2026-11-05: keep Contabo as the engine,
Lovable builds UI only. No full Lovable rebuild, no Contabo backend
replacement. The same split applies to Voicebox (see §7, separate).

## 1. What this brief is, and is not

- BUILD IN LOVABLE: a web UI only — screens, forms, lists, downloads,
  and calls to the existing Klipr API. React/Vite, as Lovable builds it.
  Build in a FRESH Lovable project (new project, connected to the
  fattmatt4280/Klipr repo), NOT inside the existing dreamwebworkz.com
  (DWW) Lovable project. DWW is Matt's personal command center; Klipr
  is its own product. The API already owns klipr.dreamwebworkz.com,
  so the UI needs its own address (Lovable URL for now, own subdomain
  later).
- DO NOT BUILD IN LOVABLE: any Python server, FFmpeg worker, systemd
  service, Postgres worker, Redis, or render engine. Lovable does not
  run those. Do not re-implement rendering in the browser.
- DO NOT CREATE: a new Supabase project, or new tables via Lovable.
  Use the existing managed Supabase project (ref
  `qexvqansnxsohgpxhhvh`) and the schema in `db/schema.sql` (29 tables,
  RLS, 29 policies — already applied and backup/restore-proven).
  No database URL, password, token, or secret goes in Lovable code.
  Secrets go in Lovable Secrets only, and only the ones Lovable needs
  for the UI (none for Klipr API auth — the user token is entered per
  session, see §3).

## 2. The engine you are calling (already validated, do not rebuild)

- API base: `https://klipr.dreamwebworkz.com` (no trailing slash).
  Caddy on Contabo fronts it (reverse proxy to `127.0.0.1:8890`,
  TLS automatic). Health, public, no token:
  `GET /health` → `{"status":"ok","env":"production",
  "billing_enabled":false,"phase":"6","dww_mount":true}`
  Local health was verified 2026-11-04 on the VPS; HTTPS health is
  the gate before Lovable UI testing — if HTTPS health fails, the UI
  will correctly show API unreachable, and that is a Caddy/DNS issue,
  not a UI bug.
- Render engine: Contabo worker, photo-motion only. 3–6 active photos
  → one 9:16 (1080x1920) MP4, per-photo durations from the blueprint.
  No generative model is called for renders. No video_clip assets in
  the current render build — a video asset fails the render job with
  a clear error, do not auto-convert it.
  Motion note (2026-11-06): the current render is a simple zoom per
  photo. It is being upgraded to the Fluffer motion standard
  (alternating zoom in / zoom out / pan per shot, beat structure,
  hard-cut reveal) — the UI must not describe the render as
  "pan and zoom".
- Storage: local disk on Contabo (`/root/klipr/storage`). S3/R2 is
  deferred. Download is via the API, not a direct file URL.

## 3. Auth — user token only, never in code

- Every Step 6 call uses `Authorization: Bearer <user token>`.
  Admin token is REJECTED by Step 6 endpoints — do not use it, do
  not offer it in the UI.
- Operator user (already in the DB): oauth_identity `matt_operator`,
  role `user`, id `bc104804-a385-4543-b4e8-27bd9079e570`.
  Brand (already in the DB): Shyftd.ink,
  id `147ad5d3-d8cb-443c-b3b2-5832c20590f0`.
- Token handling in the UI, exactly as the DWW validation UI does
  (`dww-mount/klipr-step6.html`, the screen reference for this build):
  API base + user token entered in Setup, kept in sessionStorage
  only, cleared when the tab closes, never in code, never in
  localStorage, never logged. One Setup screen, then all other
  screens use the saved session values.
- CORS: the API allows origins `dreamwebworkz.com`, `*.lovable.app`,
  `localhost`, `127.0.0.1`. The Lovable preview / published origin
  must be one of those, or calls will be blocked by CORS.

## 4. API contract (do not invent endpoints)

Base `https://klipr.dreamwebworkz.com`, all Step 6 calls user-token only.

- `GET /health` — public.
- `GET /brands` — own brands only.
- `POST /assets` — upload one photo (JSON base64 in validation;
  production Lovable build should use multipart / signed upload,
  not base64 — see §6). Fields: kind, category, source_origin,
  production_method, file bytes + filename. Categories:
  source_photo, tattoo_documentation, shop_atmosphere,
  workstation_prep, equipment_closeup, gloved_hands, artist_working,
  cleaning_wiping. Origins: authentic / synthetic. Methods:
  original / enhanced / assembled.
  New assets start `quarantined`, not active.
- `POST /assets/<id>/activate` — quarantined → active. Enforces the
  tattoo gate and the duplicate-active-hash rule; show the API error
  text, do not swallow it.
- `POST /assets/<id>/archive` — soft-delete: sets the asset to
  `archived` (owner only). Archived assets disappear from `GET
  /assets`. The file stays on disk, so renders that used it still
  work; re-uploading the same file reactivates it. Use this for the
  Library delete button — it must work from the tile itself, even
  when the thumbnail does not render.
- `GET /assets` — own assets, with status (archived excluded).
  Active assets are the only ones selectable for a project.
- `POST /projects` — one project = one blueprint = one post.
  Blueprint keys, all required: hook_type, first_frame, shot_list,
  length, cta, music, recipe_name. shot_list is a non-empty list,
  each shot with a duration (seconds). Planned assets: 3–6 active
  photos, chosen by checkbox.
- `POST /projects/<id>/render` — enqueues a render job, returns a
  job id. Render is async — poll `GET /jobs` for that job, do not
  block the UI. Blueprint is FROZEN once a project has a completed
  render: a second render on the same project returns 409. Do not
  offer a re-render button for a frozen project.
- `GET /renders` — own renders, with file_path and origin_composition.
  Composition is computed from rendered assets only — a planned
  asset that was cut is excluded, and the UI must not count it.
- `GET /renders/<id>/file` — download the finished MP4 as an
  attachment. Fetch with the Bearer token, then blob → download.
  A plain link will not send the token and will fail.
- `POST /external_posts` — record a post Matt made manually.
  Fields: render_id, platform (instagram/tiktok/youtube/facebook),
  platform_post_id, cta_keyword. CTA keyword must match the
  project's CTA, and is unique per brand — a duplicate CTA for the
  same brand returns 400, show that error.
- `POST /metric_snapshots` — fields: external_post_id, views,
  avg_watch, completion, saves, shares. Only those fields.
- `POST /inquiries` — fields: brand_id, channel
  (dm/comment/form/walk_in/referral), cta_keyword, external_post_id,
  qualified, deposit_taken, notes.
- `GET /weekly_report?brand_id=<uuid>` — per external post: latest
  snapshot, inquiry count, and medians (views, avg_watch,
  completion, saves, shares) computed over each post's latest
  snapshot only.
- Legacy Phase 0 routes (`GET /templates`, `GET /jobs`,
  `POST /jobs` kind `analyze`) exist but are NOT part of this UI.
  Do not build screens for them.

## 5. Screens (mirror dww-mount/klipr-step6.html, do not redesign)

1. Setup — API base URL, user token, Save setup + load brands.
   Brand select. Check health (public).
2. Upload + activate — multi-file image input, category, origin,
   method, tattoo-gate note. Upload per file. List my assets, with
   Activate per non-active asset, and checkboxes on active assets
   for project selection.
3. Project + render — hook_type (default `color_flash`), first_frame,
   durations (comma list, default `2,2,2,2`), length, CTA keyword,
   music, recipe name. Create project requires 3–6 checked active
   assets. Render project → job id, Check my jobs, List my renders.
   Each render: file_path, origin_composition JSON, Download MP4,
   Use for post (fills the render id in §4).
4. Post / metrics / inquiries — render id, platform, platform post
   id, CTA, Record external post → external post id. Metric snapshot
   fields as in §4. Inquiry: channel, CTA, qualified, deposit taken,
   notes.
5. Weekly report — brand select, fetch report, show per-post latest
   snapshot + inquiry count + medians.
- Show API errors as `METHOD path → status` + the API's error JSON.
  Do not hide failures behind a generic message.
- Finished work only, finished reels 7–15s, hook in first 1–2s.
  Those are Matt's IG rules v2 for the content itself, not UI rules
  — the UI does not enforce them, the blueprint does.

## 6. Data rules the UI must not break

- Provenance: `source_origin` (authentic/synthetic, NULL only for
  assembled) + `production_method` (original/enhanced/assembled)
  are separate. Never collapse them. Provenance is immutable after
  activation — the UI has no edit-provenance control.
- Tattoo gate: synthetic assets may NEVER be
  `tattoo_documentation` / needle-to-skin. The API enforces it;
  the UI must not offer a way around it, and must surface the
  gate error.
- BBP rules (universal, safety — failure fails the whole cut):
  machine fully sheathed, bottles bagged, surfaces covered, gloves
  worn. Stored in `templates.recipe` (BBP) — see
  `docs/BBP-STYLE-SPLIT.md`.
- Brand style (Shyftd.ink, in `brands.brand_kit`, user-controlled):
  gloves neon green or black only (never blue/purple); machine
  wireless black pen-style with battery pack, no cords, wrapped in
  clear/black tubing. Style is brand preference, not safety — a
  style failure is reported as style, not BBP.
- One project = one blueprint = one post. No multi-post projects.
- Uploads: base64 JSON is validation-only (3–6 phone photos under
  ~5 MB each). Production Lovable build must use multipart / signed
  upload, not base64.

## 7. Voicebox — separate project, same split, do NOT mix into Klipr

- Voicebox TTS stays on Contabo. Live endpoint:
  `https://tts.fridgespy.com` (Kokoro, systemd, port 8001).
  Qwen3-TTS cook-mode Voicebox is built but not deployed — separate
  decision, not part of this Klipr brief.
- A Lovable Voicebox shell is UI only: text in, audio out, voice
  select (Kokoro `af_heart` feminine/default, `am_adam`
  masculine). Secrets `TTS_URL` / `TTS_API_KEY` go in Lovable
  Secrets, never in code. Do not put Voicebox screens inside the
  Klipr UI, and do not put Klipr screens inside a Voicebox shell.
  Its own GitHub repo if Matt wants one; Lovable GitHub sync covers
  the web UI only, not the Python TTS server.

## 8. Validation gate — do not start the Lovable build until this is met

1. HTTPS health passes: `GET https://klipr.dreamwebworkz.com/health`
   returns ok, phase 6.
2. Real first Shyftd.ink video: Matt's 3–6 real photos + blueprint,
   rendered on Contabo, downloaded — MET 2026-11-06 (Ghostface arm,
   4 photos, 8s, downloaded to his phone). Still to do, in parallel
   with the UI build: posted manually by Matt, real external_post +
   metric snapshots + inquiries recorded, weekly report checked.
   Code was acceptance-tested with test images only — that proves
   the code runs, not that it increases bookings. The Lovable build
   is a UI duplicate of a proven flow, not a discovery build.
3. Gate met 2026-11-06 (health + real render; posting/metrics in
   parallel). Build in Lovable from this brief, with the DWW Step 6
   UI as the screen reference and `db/schema.sql` as the data
   reference. Matt's estimate for a tight UI-only duplicate is
   ~20 credits — that estimate assumes this brief, not a redesign.
   If Lovable proposes re-implementing render, auth, RLS, or
   storage in Lovable, stop and ask Matt before spending credits.

## 9. Sources in the repo (do not guess these)

- `db/schema.sql` — 29 tables, RLS, policies.
- `docs/KLIPR-1A-LITE-SPEC.md` — the approved 1A-LITE design.
- `docs/STEP6.md` — Step 6 build + acceptance test (PASS, test data
  cleaned, DB back to 0 rows at test close).
- `docs/STEP6-DEPLOY.md` — Contabo deploy, Caddy, DWW Publish.
- `docs/BBP-STYLE-SPLIT.md` — BBP vs brand style split.
- `dww-mount/klipr-step6.html` — validation UI, screen reference.
- `app/server.py` — endpoint list (docstring) + CORS allowlist.
- `app/step6.py` — endpoint logic, composition, freeze rule.
