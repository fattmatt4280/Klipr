# Klipr — What it takes to complete Phase 1
Updated 2026-10-26. Spec: Klipr Product Spec, Oct 25 2026.
Rule: build in phase order, do not start a phase until the gate above it passes.
Phase 1 = "First real video" — 1 test brand, 1 template, upload -> posted-ready video.
It is NOT the full app. Full chat, editor, brand import, avatars, community, MCP,
publishing, billing are later phases and are explicitly OUT of Phase 1.

## Gate for Phase 1 (what "complete" means)
Matt watches a Klipr Tattoo Reveal output next to the reference set and the previous
version, and would post it without re-editing. Until that happens, Phase 1 is not done,
even if code runs. A render that needs re-editing is a fail, not a pass.

## Already done (prep only, 2026-10-25)
- [x] Spec stored verbatim: workspace/klipr/docs/Klipr-Product-Spec.md
- [x] Reconciliation vs Muse draft, with Matt's 2026-10-25 corrections
      (generic multi-brand app, NOT Shyftd rules; text overlay user-controlled;
       tattoo generative ban verbatim from spec, line 86)
- [x] Skeleton folders only: workspace/klipr/{app,db,queue,templates,docs}
- [x] VPS fit check: Contabo VPS 4 (4 vCPU, 8 GB, 100 GB) fits Phase 0/1 — no GPU needed,
      generation via APIs, FFmpeg CPU renders for short 9:16 reels
- [x] Reusable tooling inventoried (see below) — NOT yet wired into Klipr

## Phase 0 — Foundation (must come first, per spec)
- [ ] Separate `klipr` app folder, database schema, and env file.
      Command Center links/mounts it; Klipr never imports Command Center code.
- [ ] Staging environment next to production (separate app + DB copy for testing).
- [ ] Object storage for all media from day one (S3-compatible: R2/B2 type),
      NOT VPS disk. Editor uses low-res proxies; raw retention policy set.
- [ ] Daily offsite backups of DB + storage, with one tested restore.
- [ ] OAuth (same system the public app will use), admin role on Matt's account,
      `billing_enabled` flag = OFF. No paywall until Phase 7.
- [ ] Row-level security on EVERY table at creation. Every row carries user_id
      (+ brand_id where it applies). This is what makes the CC version already multi-tenant.
- [ ] Job queue (Redis-backed in spec). Every analyze / b-roll / avatar / render step
      is a job with status, retry policy, and credit cost.
- [ ] OpenRouter adapter: every AI call routes through it, is metered in the credit
      ledger, and is logged to CRM — even while billing is off, so real costs are known.
- [ ] Per-capability adapters, so providers can swap without redoing setup:
      vision, video, avatar, music (Voicebox for voice/STT in spec).
- [ ] Stack decision locked: spec suggests Next.js + Postgres/RLS (Supabase fits) +
      S3 storage + Redis queue + FFmpeg workers. Muse can adjust, but the adjustment
      must be stated before building, not mid-build.

BLOCKER (not a Phase 0 item, a delivery blocker):
- Muse cannot SSH to the VPS from here (blocked 2026-10-24; iOS toggle already
  confirmed missing 2026-10-07). So Phase 0 on the VPS needs either:
  (a) prove Phase 0/1 on this VM first, then move it via Matt's Termius pastes, or
  (b) Matt checks web muse.ai for a Direct network protocols screen.
  Do NOT send Matt hunting in iOS again.

## Phase 1 — First real video
- [ ] Test brand set up BY HAND (brand import is Phase 4, do not build it now):
      Shyftd.ink only. Hand-entered brand fields only — name, logo if supplied,
      palette/fonts if supplied, voice notes, business facts, usual CTA.
      This is test data, NOT product rules. Do not hardcode its preferences into Klipr.
- [ ] Tattoo Reveal reference set, built WITH Matt:
      20-30 videos that nail the format, chosen by Matt for tattoo, stored admin-only.
      Smaller starter set is acceptable to prove the pipeline, but the full set is
      required before the template can be called shipped.
- [ ] Reference breakdown, AI pass + Matt review, into measurable traits:
      hook length, cut rhythm (avg shot length), camera moves, caption size/position/timing,
      music energy curve, where the payoff lands.
- [ ] Tattoo Reveal recipe WRITTEN FROM those shared traits, stored as a JSON row
      in the database (template table, versioned) — NOT hardcoded logic.
      Spec example structure: id tattoo-reveal, content_type tattoo, length 8-15s,
      aspect 9:16, hook text_overlay max 1.5s, slots wipe 2s / macro 3s slow_push /
      full 3s / flex 2s optional, broll allowed [photo_motion, scene], generative false,
      captions preset brand_default, music mood dark_build beat_sync true,
      transitions whip/flash/zoom_punch, CTA brand_default.
      NOTE: caption preset/position in the recipe is a user/brand-kit default the user
      can change in the editor — it is NOT a hardcoded IG rule.
- [ ] Tattoo rule enforced in code, not just docs:
      content_type=tattoo blocks generative models from creating/altering tattoo detail.
      Tattoo b-roll = photo-motion from real photos + scene ambiance only.
- [ ] Simple brief form (NOT the full planning chat — that is Phase 2):
      brand, template, one-line note or brief, uploads, hook/length/CTA fields.
      "Plan first, generate second" still applies in miniature: no generation until
      the brief is approved.
- [ ] Pipeline, one generic pipeline, template changes recipe not code:
      1. Ingest 1-10 photos/clips into the brand, to object storage, job queued.
      2. Analyze: vision tags each shot (stencil, linework, wipe, reveal, face,
         product, hands, ambiance), scores sharpness/lighting/motion, Voicebox STT
         transcribes speech, writes shot tags to the asset.
      3. Plan: recipe fills shot slots from tagged shots, empty slots flagged for b-roll,
         output = draft EDL. EDL is the heart: auto-edit writes it, renderer reads it,
         nothing baked until render.
      4. Generate b-roll: photo-motion (push-ins, parallax, reframes, lighting sweeps
         from the user's own stills) + scene b-roll from the brand scene library.
         NO generative tattoo b-roll.
      5. Finish: captions from brand kit style, music picked by template mood,
         transitions per recipe. Starter royalty-free music only — cleared for commercial
         use, no copyrighted tracks bundled. "Export without music" option for later
         trending-sound addition in-app is a later-phase concern, note it, don't build it now
         unless the recipe needs it.
      6. Render: FFmpeg 9:16 by default, preview shown BEFORE final-render credits spent.
         iOS delivery: faststart (moov first) — otherwise iPhone shows poster and plays blank.
      7. Hand off: user opens it (in Phase 1, approves/rejects) or approves it.
         Approved renders go to the Drive staging folder Muse posts from
         (existing muse-posting-queue flow).
- [ ] Feedback on every render (Phase 1 slice of the brand style loop):
      keep / tweak / reject + notes field. Thumbs on individual beats/captions/transitions
      is the full loop — Phase 1 needs at least the render-level keep/tweak/reject + notes,
      stored and linked to the project, so it can feed the style profile later.
- [ ] Fixed test set: a set of raw uploads (good footage AND bad footage) that is run
      through every template change. No template change ships without re-running it.
- [ ] Per-video report, every video, no exceptions:
      AI cost, time from upload to finished render, any upload failures,
      VPS specs, and anything in the spec that doesn't fit the VPS.
      This report is a Phase 1 deliverable in the spec, not optional.

## Inputs needed from Matt (gates, not nice-to-haves)
1. Go-ahead + build location: prove Phase 0/1 on this VM first, or Termius-paste
   route straight to the VPS. Without this, Muse cannot start the VPS build.
2. Tattoo Reveal reference set: 20-30 picks (links/uploads), or a starter set to
   prove the pipeline while he collects the full set. Without this, the recipe
   cannot be written from traits — it would be invented, which the spec forbids.
3. Test assets for the fixed test set: 1-10 photos/clips per test (good + bad),
   ideally a real finished tattoo set that fits wipe -> macro -> full -> flex.
4. Shyftd.ink hand-setup fields he wants for the test brand (logo, palette, CTA,
   caption style he prefers for THIS test — as brand-kit defaults, not product rules).
5. Starter music: approve the royalty-free source/library, or let Muse pick a
   cleared library and show it for approval before first render.

## Reusable tooling already on hand (wire in, don't rebuild from scratch)
- workspace/goals/fluffer-formula-content-training/build-fluffer-reel.sh
  (reel builder: source image, audio, offset, CTA, output path)
- workspace/command-center/modules/video-toolkit/fluffer_edit.py
  (cutout/composite)
- workspace/command-center/modules/video-toolkit/or_studio.py + studio_server.py
  (OpenRouter generation studio, BBP-baked templates, cost preflight, --yes gate,
   job status, gallery — bearer-token gated, token in .studio_token mode 600)
- workspace/video-pipeline/PIPELINE.md (8-step pipeline: one core moment, hook first,
  short beats, voice separate, edit like a human, export correctly, adapt per account,
  score Hook/Hold/Action)
- Existing Drive flow: Google Drive 'muse-posting-queue' -> ~/workspace/tattoo-posting-queue/files/
  (sidecar .txt caption verbatim, .jpg cover — Phase 1 hand-off target)

## Explicitly OUT of Phase 1 (do not build yet)
Brand import/scrape + walkthrough (Phase 4), full planning chat + brief card + Idk
(Phase 2), CapCut-style editor + AI edit tools (Phase 3), avatars/voice cloning +
consent flow, community/feed/remix/contests, MCP server/client, direct publishing +
content calendar + coach, credits billing (flag OFF), public launch (Phase 7).
Evolution Engine (docs/EVOLUTION-ENGINE.md, phases E1–E5) — the END GOAL,
the destination the product is building toward. A later phase, after the
rebuild and the validation loop. E1 instrumentation folds into the rebuild;
E2–E5 each need their own go-ahead.

## Order of work, once Matt gives go-ahead + location
1. Lock stack + location.
2. Phase 0: folders/schema/env, staging, storage, backups+restore test, OAuth/admin/
   billing flag, RLS, queue, OpenRouter adapter + ledger + CRM logging, capability adapters.
3. Phase 1: hand brand, reference set, breakdown, recipe JSON in DB, brief form,
   pipeline, EDL + FFmpeg render, keep/tweak/reject, Drive hand-off, per-video report.
4. Test set runs + Matt pass test (would post without re-editing?) -> Phase 1 complete.
   If not, fix ONE weak thing (per pipeline scoring: Hook / Hold / Action), re-run test set,
   re-test with Matt. Do not jump to Phase 2 on a failed pass test.
