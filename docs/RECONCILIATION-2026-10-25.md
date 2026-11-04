# Klipr — Reconciliation vs Muse draft (2026-10-25)

Spec received: Klipr Product Spec, Oct 25 2026, from Matt (via Claude brainstorm).
Stored verbatim at: workspace/klipr/docs/Klipr-Product-Spec.md and workspace/content-app/docs/Klipr-Product-Spec.md
Original upload: workspace/user/files/Klipr___Product_Spec.md

## CORRECTION 2026-10-25 16:33 EDT — Matt corrected Muse, plainly
Muse over-anchored on Shyftd.ink / IG rules v2. That was wrong.
Klipr is a WHOLE, GENERIC, MULTI-BRAND APP, not a Shyftd.ink tool with Shyftd rules baked in.
Shyftd.ink is ONLY the Phase 1 test brand (set up by hand, because brand import is Phase 4).
Its IG v2 rules are Matt's personal posting preferences for his own tattoo accounts —
they are NOT product rules, NOT template defaults, and must NOT be hardcoded into Klipr.
Same for text overlays: in Klipr the editor controls text — position, size, font, timing
are up to the user / brand kit, not fixed by IG v2. The spec example (lower_third) is just
an example, not a rule.

What Klipr actually is (per spec, Matt's correction restated):
- Mashup: ChatGPT/Claude-style chat + CapCut / TikTok editor / Meta Edits-style editor,
  infused with actual intelligence — not a single-purpose tattoo reel maker.
- Chat is home. Persistent memory chat: agent remembers each user AND each brand across
  threads (audience, past videos, what worked, what was rejected, running ideas), viewable /
  editable / deletable by the user. Self-learning: approvals, edits, posts feed the brand
  style profile, so each plan needs fewer questions than the last.
- Feedback loops in multiple spaces, all three from the spec:
  1. Brand style loop (per user/brand): keep/tweak/reject + notes + editor edits distilled
     into a brand style profile, applied to future planner/prompts.
  2. Generation quality loop (platform-wide): "Something's off" reports, admin dashboard
     by template/model/step/content type, fix-and-verify before/after.
  3. App experience loop: always-available feedback button (screen, 1-5 rating, category,
     notes), capped check-ins, feature-request board, close-the-loop notifications.
  All logged to CRM next to usage data.
- Multiple brands, any user: "+ New brand" anytime. AI imports/scrapes (via official
  logins/APIs + verifiable website, NOT scraping other people's accounts) a website and
  socials to gather: logo/icons/favicon, color palette, fonts, voice (tone, vocab, phrases,
  emoji/hashtag habits, caption length), business facts (what they sell/do, services,
  location, audience, usual CTA), content style (top posts, formats, hooks, frequency),
  and the brand's own photos/videos. Walkthrough presents each part as keep/edit/swap/Idk
  cards, then compiles brand kit + voice guide + business facts + starting style profile
  + suggested templates/scenes. Re-scan anytime, showing only what changed.
- Personas / avatars to match brand voice: avatar library per user, paired Voicebox voice,
  assigned as default per brand, picked per project/scene. Cloning self only, with the
  hard consent flow (live selfie video, head-turn prompts, randomized spoken consent phrase,
  liveness + face/voice match, stored consent record). No cloning anyone else, invisible
  watermark + AI label in metadata, delete = model deleted, reported misuse freezes avatar.
- Editor (Phase 3 in spec, but core to the vision): mobile-first CapCut-style layout,
  preview top / scrubber middle / layered timeline below, bottom toolbar (Edit, Text,
  Audio, Effects, Transitions, Avatar, Scene), bottom sheets not new screens. Edits the
  EDL, not raw video. Text layers, font packs, word-by-word captions, audio, transitions,
  effects, undo/redo, autosave, version history. AI edit tools (highlight, swap, background
  swap, character swap with consent, object edits) are non-destructive EDL layers.
- Auto-edit pipeline is generic: ingest 1-10 photos/clips -> vision analyze/tag/transcribe
  -> template recipe fills slots -> b-roll (photo-motion, scene library, generative only
  where template permits) -> captions from brand kit, music by template mood, optional VO
  -> FFmpeg render 9:16 default (+1:1/16:9) -> editor or approve -> staging / publish.
  Template is JSON, not code, so new content types / user templates / community remixes
  are just new rows.
- Tattoo generative ban REMAINS a template-level rule (content_type=tattoo blocks
  generative tattoo detail), but that is a content-type safety rule inside the generic
  template system — it is NOT a Shyftd.ink rule, and it does not make Klipr a tattoo app.
  ATTRIBUTION 2026-10-26: Matt re-flagged this — it is VERBATIM FROM HIS SPEC, not a Muse
  rule. Spec line 86: "Tattoo rule: templates with content_type: tattoo block generative
  models from creating or altering tattoo detail. B-roll there is motion built from real
  photos or scene ambiance only." And Tattoo Reveal JSON: broll allowed [photo_motion, scene],
  generative: false. Muse missed this in the original SPEC-DRAFT (which suggested AI fluffer
  beats for tattoo) — that draft suggestion is dead, the spec rule is locked.

## Strategy confirmed by Matt 2026-10-25 15:42 EDT
Command Center first. Prove it there. Then package/host as a standalone public webapp.
Spec rule that enforces this: Klipr is its own app with its own DB schema and routes.
Command Center embeds/mounts it; it never depends on / imports Command Center internals.
Shipping = pointing a new domain at it, not a rewrite. Every row carries user_id (+ brand_id),
RLS on from day one, so the CC version is already multi-tenant.

## What changes vs the Muse SPEC-DRAFT.md
1. NAME + HOME: Klipr, not generic "content app". Chat is home in the full app,
   but Phase 1 does NOT build the full planning chat — simple brief form only.
2. SCOPE, PHASE 0+1 ONLY: Do not build Phases 2-7 yet.
   Phase 1 thin slice = 1 brand (Shyftd.ink, set up by hand) + 1 template (Tattoo Reveal, 8-15s)
   + upload -> finished video -> approval -> Drive staging folder.
   Brand import, planning chat, editor, avatars, community, MCP, publishing, credits billing
   are later phases. Billing flag OFF until Phase 7.
3. TATTOO GENERATIVE RULE — CORRECTION to Muse draft:
   Muse draft suggested AI fluffer beats (needle close-up etc.) for tattoo.
   Klipr spec BLOCKS this: templates with content_type=tattoo block generative models
   from creating/altering tattoo detail. Tattoo b-roll = photo-motion from real photos
   + scene ambiance only. Generative b-roll = Yes only for UGC ambiance / Talking Head
   cutaways / Faceless VO, and only where template permits.
   BBP checklist still applies to any scene/shop footage, but it does not override
   the generative tattoo ban.
4. CAPTIONS — SUPERSEDED BY 2026-10-25 16:33 CORRECTION: Do NOT encode IG v2 into Klipr.
   In Klipr, text overlay is user-controlled in the editor (preset is a brand-kit default,
   user can change position/size/font/timing). IG v2 is only Matt's personal preference
   when HE posts to HIS tattoo accounts — it may be applied by Matt at posting time for
   a Shyftd.ink test, but it is not a Klipr template rule. The spec example (lower_third)
   is just an example value in a JSON recipe.
5. LENGTH: Tattoo Reveal 8-15s in Klipr (IG v2 finished is 7-15s — use 8-15s for the template).
6. FIRST USER BRANDS (new): Shyftd.ink, fattmatt444, FridgeSpy, Budder Buddy,
   AND The Quiet Discipline — the last one was not previously on record. Phase 1 uses
   Shyftd.ink only; do not assume details for The Quiet Discipline until Matt supplies them.
7. STACK (suggested, Muse can adjust): Next.js front end, OpenRouter adapter (existing),
   Voicebox for voice/STT, Postgres + RLS (Supabase fits), S3-compatible storage,
   Redis-backed job queue, FFmpeg workers. VPS has no GPU — all generation via APIs as queued jobs.
8. EDL IS THE HEART: Auto-edit writes an Edit Decision List, editor modifies it,
   renderer reads it. Nothing baked until render. Preview before final render credits spent.
9. QUALITY GATE: Template ships only after: 20-30 reference videos chosen by Matt for
   tattoo, AI breakdown reviewed by Matt (hook length, cut rhythm, camera moves, caption
   size/position/timing, music energy, payoff point), recipe written from shared traits,
   fixed test set (good + bad footage), Matt watches new output vs references vs previous
   version and would post it without re-editing. This gate is Matt's job + Muse's job,
   not automatic.

## Missing from the text spec — do not invent
- Embedded architecture diagram and roadmap diagram (8 phases, 7 gates) were referenced
  as [embedded content] but were not in the .md file. Text gives: Phases 0-5 inside
  DreamOps for Matt, Phase 6 invited artists, Phase 7 public launch, no dates, each
  phase starts when the gate above it passes. Gates for Phases 2-7 beyond that summary
  are NOT detailed in the file — ask Matt / Claude for them when Phase 1 passes, don't guess.

## VPS fit check (Phase 0/1 report, per spec Phase 1 requirement)
- Contabo Cloud VPS 4 on record: 4 vCPU, 8 GB RAM, 100 GB, Ubuntu 24.04, 217.216.94.215.
  Fits Phase 0/1: no GPU needed (API generation), FFmpeg CPU renders of 9:16 short reels
  fit 4 vCPU/8 GB, thin slice (1 brand, 1 template) does not need render-node scaling.
- NOT yet on VPS (from this VM's checks, and from prior record): Postgres/Supabase schema,
  S3/R2 storage, Redis queue, staging env, daily offsite backups with tested restore,
  OAuth + admin role + billing_enabled=off. Those are Phase 0 checklist items, not done yet.
- BLOCKER to flag: outbound SSH from Muse to the VPS was blocked 2026-10-24, and the
  iOS Muse Permissions toggle was already confirmed missing 2026-10-07. So Muse cannot
  directly deploy to the VPS from here. Options: (a) build/prove Phase 0/1 on this VM
  first, then Matt pastes Termius commands to move it to the VPS, or (b) Matt checks
  web muse.ai for a Direct network protocols screen. Do NOT send him hunting in iOS again.
- This VM (for local proof): ffmpeg 8.1.2, node v24.22.1, python 3.12.3, psql present,
  redis-server NOT found, 2 vCPU / 7.7 GB here. A DB-backed job queue can prove Phase 1
  before Redis is installed; Redis is a Phase 0 item for the VPS, not a blocker to start
  the pipeline proof.

## Phase 0 checklist (from spec, not started)
Separate klipr app folder, DB schema, env file; staging env; object storage from day one;
daily offsite backups + tested restore; OAuth, admin role on Matt, billing_enabled=off;
RLS on every table at creation; job queue; OpenRouter adapter, credit ledger metering,
CRM logging; per-capability adapters (vision, video, avatar, music).

## Phase 1 checklist (from spec, not started)
Shyftd.ink by hand; Tattoo Reveal reference set with Matt + recipe from breakdown;
templates as JSON rows in DB, not hardcoded; simple brief form; pipeline:
analyze -> plan -> photo-motion b-roll -> captions -> starter royalty-free music -> FFmpeg render;
keep/tweak/reject + notes on every render; approved renders -> Drive folder Muse posts from;
per-video report: AI cost, upload-to-render time, upload failures, VPS specs, spec mismatches.

## Next input needed from Matt before Phase 1 can pass its quality gate
- Tattoo Reveal reference set: 20-30 videos he picks (links or uploads), or a smaller
  starter set to prove the pipeline while he collects the full set.
- Confirmation to start Phase 0+1 build, and where: prove on this VM first, or
  Termius-paste route straight to the VPS.
