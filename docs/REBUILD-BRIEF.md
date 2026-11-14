# Klipr Rebuild Brief — Lovable app + Supabase Storage + Contabo worker

Status: DRAFT 2026-11-07 — written for Matt's decision to rebuild Klipr in Lovable.
Supersedes (for the rebuild) the UI-only scope in `docs/LOVABLE-BUILD-BRIEF.md`.
That brief stays valid for the CURRENT build (Contabo API + Lovable UI only).
This brief is the target architecture for the rebuild. Do not start it until Matt confirms.

## Goal

Rebuild Klipr in Lovable so the app, the data, and the files live in one place
(Supabase), removing the friction of the current split: CORS allowlists, the
user-token file, base64 uploads, the patch-and-restart deploy dance, and
session-only gallery thumbnails.

Contabo keeps only the jobs a phone and Lovable cannot do: FFmpeg (Auto
renders) and Voicebox (voice generation / cloning). Contabo becomes a worker,
not the app backend. End state (when Matt has a new computer): the worker
(FFmpeg + Voicebox) moves to that computer; the app and Supabase stay as-is.

## The three layers

| Layer | Job | What it owns |
| --- | --- | --- |
| Supabase (project `qexvqansnxsohgpxhhvh`) | File storage + database | Buckets (see §1), the existing 29-table schema, RLS. Photos and videos get real CDN URLs, so the gallery loads them like any image — no custom download endpoint, no base64, no session-only previews. |
| Klipr app (Lovable) | UI + Manual Editor | All screens (Build / Library / Create / Videos), the Manual editor (on-device Canvas + MediaRecorder — no FFmpeg, no server), uploads to Supabase Storage, and calls the Contabo worker for Auto renders and voice. |
| Contabo VPS (worker only) | FFmpeg + Voicebox | Stays idle until called. For an Auto render it reads the source files from Supabase Storage, runs FFmpeg, and writes the finished MP4 back to Supabase. For voice it runs the Voicebox TTS/clone service and writes the audio to Supabase. It does NOT serve gallery thumbnails or stream raw video to phones. |

What this fixes (the friction since the beginning): no CORS allowlist to maintain
for the app (Supabase Storage is built for browser fetches), no token file to
copy (the app signs in with Supabase Auth), no base64 (the app uploads files
directly to Supabase Storage), no Termius patch deploys for app changes, and
gallery images that persist across logins (they are fetched from Supabase on
every load).

What it does NOT remove: the render engine still needs a server (FFmpeg cannot
run in Lovable or reliably in a phone browser). The worker is that server. The
Manual editor needs no server and is unchanged.

## 1. Interface spec — Supabase Storage bucket structure

Buckets are NEW (the current build stores files on the VPS local disk, not in
Supabase Storage). Create them in the Supabase dashboard for project
`qexvqansnxsohgpxhhvh` before the app uses them. All buckets are PRIVATE.
The app never exposes a permanent public URL for a source asset. The app gets
short-lived signed URLs for thumbnails/previews; the worker uses the service
role key (server-side only, on the VPS `.env`, never in the app) to read and
write.

| Bucket | Holds | Path pattern |
| --- | --- | --- |
| `assets` | Source photos and video clips (the Library) | `assets/<user_id>/<brand_id>/<kind>/<asset_id>.<ext>` — `kind` is `photo` or `video_clip`; `<ext>` is `jpg`, `png`, `mp4`, or `mov`. The original filename is NOT used as the key (the asset id is the key, so re-uploads and renames cannot collide). |
| `renders` | Finished MP4s (Auto renders only) | `renders/<user_id>/<brand_id>/<render_id>.mp4` |
| `audio` | Voicebox tracks (and uploaded music, if the app supports it) | `audio/<user_id>/<voice_id>/<track_id>.mp3` (mp3) or `.wav` |

Rules:
- The DB is the source of truth for ownership and status. The `assets` table row
  stores `storage_bucket` (`assets`) and `storage_key` (the path above). The
  current `storage_path` column (a VPS-local relative path) is kept during
  migration and then deprecated — the app must NOT build a URL from it (that is
  the bug that caused the 404 tiles: `storage_path` is a server-local path, not
  a URL).
- RLS on Storage: a user can read/write only objects under their own
  `<user_id>/` prefix. The worker (service role key) bypasses RLS server-side.
- Signed URLs: the app requests a signed URL for a thumbnail/preview (short
  expiry, e.g. 1 hour) and fetches it on every Library load. Do NOT cache the
  image in sessionStorage or a local blob that is lost on logout — that is the
  session-only bug. Fetch from Supabase on every load.
- The finished render (in `renders/`) is the app's output. It is NOT public by
  default; it becomes public only when the user posts it (on Instagram/TikTok)
  by their own action outside the app.
- Migration: existing VPS-local assets (the Ghostface photos and any others on
  `/root/klipr/storage`) must be uploaded to the `assets` bucket and their DB
  rows updated from local `storage_path` to `storage_bucket` + `storage_key`
  before the app switches over. The finished Ghostface render MP4 moves to
  `renders/`. Do not delete the VPS files until the migration is verified.

## 2. Interface spec — Render Job schema (v1)

The app sends one Render Job (JSON) to the Contabo worker when the user taps
an Auto render. The worker runs FFmpeg from it and writes the finished MP4 to
the `renders/` bucket. This is a CONTRACT: the app and the worker must agree
on every field. Fields marked (new) are not in the current worker and must be
built; the rest carry over from the current Step 6 blueprint.

Current Step 6 blueprint (for reference, the 7 keys the worker already takes):
`hook_type`, `first_frame`, `shot_list`, `length`, `cta`, `music`,
`recipe_name`. `shot_list` entries may carry a per-shot `duration`. The current
worker (`photo_motion_multi`) only does: photos, zoom-IN only, no transitions,
no text, no video clips, no audio muxing. It takes (sources, durations) and
outputs a 9:16 MP4. Everything below marked (new) is a worker upgrade.

```json
{
  "version": 1,
  "project_id": "<uuid>",
  "brand_id": "<uuid>",
  "aspect_ratio": "9:16",
  "resolution": "1080x1920",
  "fps": 30,
  "hook_type": "color_flash",
  "first_frame": "<asset_id of the opening shot>",
  "cta": "BOOK",
  "recipe_name": "Ghostface Arm Reveal",
  "clips": [
    {
      "asset_id": "<uuid>",
      "source_url": "<supabase storage signed url for this asset>",
      "kind": "photo",
      "trim_start": 0.0,
      "trim_end": 2.0,
      "duration": 2.0,
      "motion": "zoom_in",
      "transition_in": "cut",
      "speed": 1.0
    }
  ],
  "text_overlays": [
    {
      "text": "string, max 6 words for a hook",
      "start": 0.0,
      "end": 2.0,
      "position": "center-upper",
      "style": "default"
    }
  ],
  "audio": {
    "music": {
      "source_url": "<url of the music track, or null>",
      "volume": 0.8,
      "trim_start": 0.0,
      "trim_end": 8.0
    },
    "voiceover": {
      "source_url": "<supabase audio url for the Voicebox track, or null>",
      "volume": 1.0
    }
  }
}
```

Field rules:
- `version` (required, integer, currently `1`). The worker rejects a job whose
  `version` it does not know.
- `aspect_ratio` (required): `"9:16"` for reels. `resolution` (required):
  `"1080x1920"`. `fps` (required): `30`.
- `clips` (required, non-empty, 3–6 entries for an Auto render — the same
  3–6 rule as Step 6). Each clip:
  - `asset_id` (required, uuid) — must be an active asset owned by the user.
  - `source_url` (required) — a Supabase Storage signed URL for that asset.
    The worker downloads it. The worker must NOT be given a VPS-local path.
  - `kind` (required): `"photo"` or `"video_clip"`. (new: `video_clip` — the
    current worker rejects video clips.)
  - `trim_start` / `trim_end` (optional, seconds, default the whole clip).
    For a photo, `trim_end - trim_start` is the on-screen duration.
  - `duration` (required for photos, seconds) — the on-screen time. For a
    video clip, `duration` defaults to `trim_end - trim_start`.
  - `motion` (optional, default `"zoom_in"`): `"zoom_in"`, `"zoom_out"`,
    `"pan_left"`, `"pan_right"`, `"none"`. (new: everything except `zoom_in` —
    the current worker only zooms in.)
  - `transition_in` (optional, default `"cut"`): `"cut"`, `"fade"`, `"zoom"`.
    (new: `fade` and `zoom` — the current worker only hard-cuts.)
  - `speed` (optional, default `1.0`): `0.5`, `1.0`, or `2.0`. (new.)
- `text_overlays` (optional, default `[]`): on-screen text. (new — the current
  worker renders no text.) `position` is `"center-upper"` by default (the IG
  safe zone). The app must not burn in prices, phone numbers, or client names.
- `audio` (optional): `music` and `voiceover` are each optional (null if
  absent). The worker muxes them into the MP4. (new: audio muxing — the current
  worker outputs silent video.)
- `hook_type`, `first_frame`, `cta`, `recipe_name`: carried over from the
  Step 6 blueprint. `cta` is the keyword recorded with the post (used to
  measure inquiries). `recipe_name` is a human label, not a filename.
- Worker output: the finished MP4 is written to the `renders/` bucket at
  `renders/<user_id>/<brand_id>/<render_id>.mp4`, and the worker records the
  render row (project_id, brand_id, asset_id, origin_composition, file_path =
  the Supabase key) in the DB, exactly as Step 6 does today. The app polls the
  job (same as today: `GET /jobs`) and then fetches the MP4 from the `renders/`
  bucket (signed URL) or via the existing `GET /renders/<id>/file` endpoint.
- Blueprint freeze (unchanged): one project = one blueprint = one post. Once a
  project has a completed render, a second render is a 409. Edit the blueprint
  before rendering; a new version is a new project.

## 3. Interface spec — Voicebox API contract

The Voicebox is the Contabo voice service (Qwen3-TTS 0.6B, zero-shot clone).
It is DEPLOYED and live on the VPS at `https://voicebox.dreamwebworkz.com`
(verified 2026-11-07: health `model_loaded: true`, Kratos speak test 200).
The code lives in `~/workspace/command-center/modules/voicebox/`
(`server.py`, `voicebox.py`). (The live TTS at `tts.fridgespy.com` is Kokoro,
the FridgeSpy TTS — a different service, not the Klipr voice-clone path.
Do not confuse them.)

Verified from `server.py` (the contract below is the real one, not a guess):

- Base: the Voicebox service on the VPS (default port `8765`, host
  `127.0.0.1`). Public: `https://voicebox.dreamwebworkz.com`. The app may
  reach it directly (public URL) or through the Contabo worker API base
  (`https://klipr.dreamwebworkz.com`), which proxies `/voice/*` to the Voicebox
  (exact proxy path is a deploy detail; the contract below is what the proxy
  forwards). Do not expose the Voicebox port directly to the internet.
  Note: the Voicebox has NO CORS headers, so a browser app must call it
  through a server-side route (e.g. a Supabase Edge Function), not directly
  from the frontend.
- Auth: `Authorization: Bearer <secret>`. The secret lives in a file on the
  VPS (`VOICEBOX_SECRET_FILE`) and in Lovable Secrets for the app. Never in
  code, never in chat, never in a screenshot.
- `GET /health` (no auth) → `{"ok": true, "model_loaded": bool}`.
- `GET /voices` (auth) → `{"voices": [{"name": "...", "description": "..."}]}`.
  The list is the manifest — the voices the service can clone.
- `POST /speak` (auth) → raw audio bytes.
  - Request JSON body: `{"text": "<string, required, 1..1000 chars>", "voice": "<string, optional, default \"bella\", must be a voice in the manifest>"}`.
  - Query: `?format=wav|mp3` (default `wav`; `mp3` needs ffmpeg on the VPS PATH).
  - Response: the audio bytes, `Content-Type: audio/wav` or `audio/mpeg`.
    For `wav` the response carries an `X-Cache: HIT|MISS` header (the service
    caches by sha256(voice + text), up to 2000 files).
  - Errors: `400` for missing/empty text, text over 1000 chars, or an unknown
    voice; `401` for a missing/invalid Bearer secret.
- Async voiceover jobs — long scripts in the background (2026-11-08):
  `POST /speak/jobs` (auth) → `202` with `{"job_id": "vjob_...",
  "status": "queued", "total_parts": N, "created_at": "..."}`. The job runs
  in the background even if the client disconnects. Request JSON:
  `{"text": "<string, required unless chunks given, max 20000 chars>",
  "voice": "<string, optional, default \"bella\">",
  "format": "wav|mp3" (optional, default "wav"),
  "split_chunks": bool (optional, default true),
  "chunks": ["...", ...] (optional, pre-split by the caller)}`.
  The server splits the text into chunks (max 1000 chars each, same as
  /speak), generates each chunk, and stitches them with pauses (400ms after
  `.` `!` `?`, 180ms after `,` `...`, 250ms otherwise). Jobs run one at a
  time, FIFO. `GET /speak/jobs/<job_id>` (auth) → status + progress
  (`{current_part, total_parts, percent}`) + `logs` + `error` +
  `duration_seconds` (when completed) / `failed_part` (when failed).
  `GET /speak/jobs/<job_id>/audio` (auth) → the finished audio bytes
  (`audio/wav` or `audio/mpeg`); `404` unknown job, `409` not ready yet.
  `DELETE /speak/jobs/<job_id>` (auth) → cancel a queued/processing job.
  Job audio is kept in `/tmp/voicebox_jobs/` for 24h. Timing (CPU): roughly
  7x realtime (a 60s voiceover takes ~7 minutes) — it is a background job,
  the app polls and downloads when done.
- `POST /clone` (auth) → `{"name": ..., "description": ..., "file": ...,
  "duration": ..., "source": "custom", "edits": {...}}` (201). Clone a voice
  from a reference audio clip, with optional audio editing. The new voice is
  usable by `/speak` immediately (no restart). No restrictions on which voice
  or name may be cloned — only filesystem safety on the name and a 100 MB
  upload cap. A name that already exists returns `409`.
  - multipart/form-data: fields `name` (required), `description` (optional),
    `audio` (required file: wav/mp3/m4a/ogg/...).
  - ... or JSON: `{"name": ..., "description": ..., "audio_base64": ...,
    "filename": ...}` (raw base64, no data URL prefix).
  - Optional audio-editing params (form fields or JSON fields, all optional):
    `isolate` (bool) — Demucs vocal isolation, pulls the voice out of
    background noise/music (slow on CPU, ~5x realtime; the Demucs model
    downloads on first use, ~81 MB, then cached). `speed` (0.25..4) — tempo
    multiplier. `pitch` (-12..12) — semitones. `trim_start` / `trim_end`
    (seconds). `volume` (0.1..4) — linear gain. `normalize` (bool) — dynamic
    level normalization. The clip is normalized to mono 24kHz WAV (capped
    at 60s) and added to the manifest. Errors: `400` bad name/audio/edit
    params, `401` bad secret, `409` name already exists, `413` audio over
    100 MB.
- How a voice works (zero-shot clone): a voice name in the manifest maps to a
  reference audio file. The service builds a clone prompt (x-vector) from that
  reference audio and generates new speech in that voice. So the "reference
  audio ID / embedding" the app needs is simply the voice NAME — the app does
  not send audio or an embedding, it sends `voice: "<name>"`. To add Matt's
  voice (or any new voice), use `POST /clone` from the app, or clone manually
  on the VPS (see below). There is a `--voice matt` slot reserved for Matt's
  voice.
- Manual cloning / audio editing (VPS, Termius): the same editing is available
  from the command line, so Matt can edit a sample and clone a voice by hand.
  `voicebox.py edit --in <file> --out <file> [--isolate] [--speed X]
  [--pitch N] [--trim-start S] [--trim-end E] [--volume V] [--normalize]`
  edits a sample and writes the edited WAV (an audio editor, like the video
  editor but for audio). `voicebox.py clone-from --wav <file> --name <name>
  [--desc "..."]` + the same editing flags edits + clones in one step.
  Run from `/root/voicebox` with the venv python.
- Where the audio goes: after `POST /speak` returns the bytes, the caller
  (the app or the worker) uploads the audio to the Supabase `audio/` bucket
  at `audio/<user_id>/<voice_id>/<track_id>.mp3` (or `.wav`) and stores the key
  in the DB. The Render Job's `audio.voiceover.source_url` is a signed URL for
  that key. The Voicebox itself does not write to Supabase — the caller does.
- Limits (from the code): text max 1000 chars per call; requests are
  serialized (CPU inference, one at a time); the model loads once at startup.
  Keep voiceover scripts short (one call per clip/line, not a whole script).
  Clone uploads are capped at 100 MB; the reference clip is capped at 60s.

## 4. Database changes

The existing 29-table schema (in Supabase project `qexvqansnxsohgpxhhvh`) stays.
Only the file-location columns change:

- `assets`: add `storage_bucket` (text, e.g. `assets`) and `storage_key` (text,
  the path in §1). Keep `storage_path` (the VPS-local path) during migration,
  then deprecate it. The app reads `storage_bucket` + `storage_key` and
  requests a signed URL. It must never use `storage_path` as a URL.
- `renders`: `file_path` becomes the Supabase key in the `renders/` bucket
  (e.g. `renders/<user_id>/<brand_id>/<render_id>.mp4`) instead of a VPS-local
  path. The existing `GET /renders/<id>/file` endpoint keeps working (it can
  serve from Supabase by key) or the app fetches the signed URL directly.
- Nothing else in the schema changes: the 29 tables, RLS (`owner_or_admin`),
  the provenance split (`source_origin` + `production_method`), the tattoo gate
  (synthetic can never be `tattoo_documentation` / `needle_to_skin`), the
  blueprint freeze, and `asset_usage` (considered / selected / rendered) all
  carry over unchanged.

## 5. Auth split

- App ↔ Supabase (storage + DB): Supabase Auth. The user signs in with the
  app; RLS enforces per-user access (a user can only read/write objects under
  their own `<user_id>/` prefix and rows they own). The existing operator user
  (`bc104804-a385-4543-b4e8-27bd9079e570`, `matt_operator`) is migrated to a
  Supabase Auth user; the Shyftd.ink brand (`147ad5d3-d8cb-443c-b3b2-5832c20590f0`)
  stays owned by that user. Self-serve signup is still deferred (a new user +
  token is a manual seed, as today) unless Matt asks for it.
- App ↔ Contabo worker (Auto renders + voice): the existing Klipr user token
  (Bearer, 22-char, the one Matt holds privately) — the worker API accepts it
  for render and voice jobs only. The worker does NOT need the user's token to
  read Supabase; it uses its own service role key (server-side only, in the
  VPS `.env`, never in the app, never in chat).
- The Voicebox secret is separate from the Klipr user token. Do not reuse one
  for the other.

## 6. Migration plan (phases)

1. Supabase Storage: create the three buckets (`assets`, `renders`, `audio`),
   private, with the RLS/prefix rules in §1. Verify a signed URL loads in the
   browser.
2. Existing assets: upload the VPS-local files to the `assets` bucket and
   update their DB rows to `storage_bucket` + `storage_key`. Verify each one
   loads from Supabase. Do not delete the VPS files until this is verified.
3. App: Lovable switches uploads to Supabase Storage (direct upload, no
   base64) and thumbnails/previews to signed URLs from `GET /assets/<id>/file`
   (or directly from Supabase). The Library must load on every login (the
   session-only bug is the acceptance test).
4. Worker: the Contabo worker reads source files from Supabase (signed URLs in
   the Render Job, §2) and writes the finished MP4 to the `renders/` bucket.
   Deploy the Voicebox to the VPS (see §3) and expose it through the worker API.
5. Retire: the Contabo API stops serving gallery files and stops accepting
   base64 uploads. Local VPS storage (`/root/klipr/storage`) is kept as a
   backup until Matt confirms the migration, then removed. Contabo is
   worker-only (FFmpeg + Voicebox).
6. End state (new computer): the worker (FFmpeg + Voicebox services) moves to
   Matt's computer. The app and Supabase do not change. The worker API base
   URL is the only value that changes (one config value in the app).

## 7. What does NOT change

- IG rules v2 (approval always, finished work only, 9:16, 7–15s finished reels,
  hook in 1–2s, strict on-screen text, 5-tag formula, CTA on the final end card
  only). The auto-poster stays paused until Matt says go.
- BBP rules for AI shop footage (machine sheathed, bottles bagged, surfaces
  covered, gloves on; neon green or black gloves, wireless black pen machine —
  the style lives in the Shyftd.ink `brand_kit`, the safety in `templates.recipe`).
- The tattoo gate and provenance rules (§4). The Manual editor stays on-device
  (Canvas + MediaRecorder, no server, no FFmpeg). The validation loop stays:
  post manually to @shyftd.ink, record the external post + metrics + inquiries,
  check the weekly report.
- Multi-tenancy: Shyftd.ink is NOT hardcoded. Users + brand ownership + RLS +
  per-user tokens + per-brand `brand_kit` stay the separation mechanism.

## 8. Validation gate (how to know the rebuild works)

1. Log out of the app, log back in — the Library shows every photo/video
   thumbnail (the session-only bug is gone).
2. Upload a photo and a short video clip from the phone — both appear in the
   Library with thumbnails, no base64 error, no 404.
3. Delete a tile (trash icon) — it disappears and stays gone after a reload.
4. Build a Manual edit (photos + a video clip, trim, text) and export it
   on-device — the MP4 downloads, no stuck-at-100% screen.
5. Send an Auto render (Render Job v1) — the worker returns a finished MP4 in
   the `renders/` bucket; the app plays/downloads it.
6. Generate a voiceover (Voicebox `/speak`) — the audio lands in the `audio/`
   bucket and muxes into a render.
7. Post the finished video manually to @shyftd.ink and record the post, metrics,
   and inquiries — the validation loop closes.

## Sources (verified, not guessed)

- Current blueprint keys and the photo-only worker: `app/step6.py`,
  `app/adapters.py` (`photo_motion_multi`, zoom-in only).
- Current storage layout (VPS-local): `app/storage.py` (`LocalStorage`,
  `<user_id>/<brand_id>/<kind>/<filename>`).
- Current endpoints (including the wrong ones Lovable guessed):
  `POST /assets/<id>/archive` (not `/delete`, not `DELETE`),
  `POST /assets` with `kind: "video_clip"` (not `"video"`),
  `GET /assets/<id>/file` (inline, correct MIME — built 2026-11-07, commit
  `adb7f65`, deployed to the VPS).
- Voicebox contract: `~/workspace/command-center/modules/voicebox/server.py`
  (`GET /health`, `GET /voices`, `POST /speak`, `POST /clone` with audio
  editing — isolate/speed/pitch/trim/volume/normalize, `POST /speak/jobs`
  + `GET /speak/jobs/<id>` + `GET /speak/jobs/<id>/audio` +
  `DELETE /speak/jobs/<id>` for async long-script voiceovers, Bearer secret,
  text 1..1000 per /speak call (20000 per job), voice from manifest,
  `?format=wav|mp3`). Deployed and live
  at `https://voicebox.dreamwebworkz.com` (verified 2026-11-07/08; jobs
  endpoints built + tested locally 2026-11-08, deploy pending).
  Manual cloning/editing: `voicebox.py edit` + `voicebox.py clone-from`.
- Kokoro TTS (live, FridgeSpy): `tts.fridgespy.com`, systemd uvicorn `:8001`.
  Not the Klipr voice-clone path.
- Supabase project: `qexvqansnxsohgpxhhvh` (29 tables, RLS). Storage buckets
  in §1 are to be created — they do not exist yet.
- Lovable project id: `c6d48b76-34c9-4840-a7c8-bd5f9c5fbd1e`. CORS on the
  Contabo API already allows `*.lovable.app` and `*.lovableproject.com`.
