# KLIPR 1A-LITE - SPEC (design only, no endpoints yet)
Status: DESIGN ONLY. Approved as the next milestone spec, superseding the
2026-11-03 library migration spec (archived, not deleted, in
docs/ARCHIVE-library-migration-2026-11-03.md). No Step 6 code in this commit.
Schema diff is on a separate branch, NOT merged, NOT applied to any managed DB.
Goal: One real Shyftd.ink video: uploaded assets -> rendered file ->
manually posted -> metrics + inquiries recorded.
Success question only: does Klipr increase qualified tattoo inquiries for
Shyftd.ink and cut time per post?
## Scope freeze
- 23 existing Phase 0 tables, unchanged on main.
- 3 new library tables + 3 new measurement tables = 29 total on the diff branch.
- No new services, queues, or infrastructure in 1A-LITE.
- Single-operator validation, multi-tenant architecture (user_id + brand_id
  on every row, RLS enabled). First test brand: Shyftd.ink, by hand only.
- Step 6 (upload / render / post / metrics endpoints) is NOT started until
  this spec is approved separately. This commit is design only.
## Step 0 - done, see docs/STEP0-1A-LITE.md
Git init + .gitignore (secrets/storage/dumps excluded, db/schema.sql tracked),
live-data check (fresh VM Postgres, 0 rows, 23 tables), backup + restore proof
locally (41K, checksum OK, restore 23/23), token rotation doc, requirements.txt
(psycopg2-binary) + unittest runner (10 tests, 9 passed, 1 DB-skipped).
Daily cron and managed DB are NOT done in Step 0 - see A4 / A2 below.
## Step 1 - fresh schema if no data
If no live data worth keeping is found on the durable host: do NOT run the
old M0-M7 legacy migration. Recreate schema fresh from schema.sql as the
single source of truth. Remove from scope: M0 snapshot, M3 normalization /
backfill, legacy resolvability rules, legacy quarantine-by-default.
If real data DOES exist on that host: stop, report counts, do not recreate.
VM-only finding (0 rows) does NOT prove Contabo holds no data. Contabo is
unchecked until root is reset - do not touch it, do not delete anything there.
## Step 2 - keep (core provenance, simplified)
assets: add kind, category, source_origin (authentic/synthetic/NULL),
production_method (original/enhanced/assembled), hash_sha256, mime, width,
height, duration, status (quarantined/active/archived), consent_record_id,
generator_provider, generator_model, prohibited_uses.
CHECKs for kind, category, and provenance combinations.
kind: photo, video_clip, audio, finished_video, reference_image, reference_video.
category: source_photo, source_video, tattoo_documentation, shop_atmosphere,
workstation_prep, equipment_closeup, gloved_hands, needle_to_skin,
artist_working, cleaning_wiping, shop_interaction, transition_broll,
character_reference, environment_reference, hook_clip, transition_clip,
music, voice, sfx, ambient, finished_video.
Provenance combos: original/enhanced require source_origin authentic/synthetic;
assembled requires source_origin NULL; synthetic original requires provider+model;
authentic/enhanced require provider/model NULL.
Tattoo gate, in DB: synthetic assets can NEVER be tattoo_documentation or
needle_to_skin. Synthetic shop_atmosphere / equipment_closeup must carry
prohibited use tattoo_session_representation.
Provenance immutability after activation: simple BEFORE UPDATE trigger on
source_origin, production_method, hash_sha256.
Duplicate: UNIQUE (user_id, brand_id, hash_sha256) WHERE status='active'.
Hash is SHA-256 of stored file bytes. Rename does not change it, re-encode does.
Same user+brand+archived duplicate reactivates same ID (import path).
Same user+different brand = explicit cross-brand import only, new ID, same hash,
NO lineage link, origin/category copied only after explicit re-attestation,
flagged cross_brand_import=true. Different user = independent import, no leak.
Duplicate checks must be RLS-scoped, never a global hash lookup.
New library tables (3): asset_relationships (lineage, asset-to-asset only),
project_assets (planned), asset_usage (actual rendered usage).
Lineage types: extracted_from, enhanced_version_of, alternate_angle_of,
version_of, remix_of, character_reference_for, environment_reference_for.
Enhanced: exactly one enhanced_version_of source (partial unique index +
activation check). A true two-source combination is assembled, not enhanced.
renders: add brand_id, asset_id, origin_composition.
Composition is computed from asset_usage rows for THAT render only.
Planned-but-cut assets are excluded. Per group: occurrence count, distinct
asset count, summed duration.
Keep user_id + brand_id on every row, RLS enabled.
Fix server.py: queries run as authenticated user via SET LOCAL
app.current_user_id, NOT always _set_admin(). Token mapping is server-side
only, never client-supplied user_id. Session variables alone cannot prevent
a SQL-holding application role from impersonating - full prevention needs
per-user Postgres auth or function-only access, deferred (see DEFERRED.md).
## Step 3 - defer (do not build in 1A-LITE)
See docs/DEFERRED.md for the full list. Headline deferrals:
brand_assignment_audit, attestation, assignment ordering / immutability guards;
session-variable impersonation hardening beyond SET LOCAL + server token mapping;
deferred constraint triggers (usage_render_completion_check,
usage_published_revert_check); post_delete_usage_transition and the full
published/rendered state machine; scene_assets; split per-operation RLS;
project archival convention; asset_shares, OAuth, S3, Redis, vector DB,
Production Brain, API metric pulls, team permissions, public onboarding.
asset_usage states in 1A-LITE: considered / selected / rendered only.
Published tracking lives in external_posts, not in a published usage state.
## Step 4 - add (measurement, required, not optional)
external_posts: id, user_id, brand_id, render_id, platform
(instagram/tiktok/youtube/facebook), platform_post_id,
cta_keyword UNIQUE per brand, posted_at, posted_by (manual/muse/api).
metric_snapshots: id, external_post_id, captured_at, hours_since_post, views,
reach, avg_watch_time_sec, completion_rate, likes, comments, shares, saves,
profile_visits, follows. Snapshots at roughly 1h, 24h, 72h, 7d.
Manual entry for now, API pulls later.
inquiries: id, user_id, brand_id, received_at, channel
(dm/comment/form/walk_in/referral), cta_keyword nullable, external_post_id
nullable, qualified bool, deposit_taken bool, notes.
projects.blueprint jsonb: hook type, first-frame content, shot list with
durations, length, CTA, music, recipe name.
Rule: one project = one blueprint = one post, frozen once that project has a
completed render, so weekly reporting joins external_posts -> renders ->
projects -> blueprint and the comparison stays honest.
Internal posts table (Phase 0) stays dormant in 1A-LITE; external_posts is
the source of truth for posted videos.
## Step 5 - BBP vs style split
See docs/BBP-STYLE-SPLIT.md for the full split and QA format.
bbp_rules (universal, safety): machine in barrier bag, bottles bagged,
armrest/chair/tray covered, gloves worn.
brand_style_rules (Shyftd.ink): glove color neon green or black, wireless
black pen-style machine with battery pack, no cords.
Stored in 1A-LITE as recipe / brand_kit JSON (templates.recipe,
brands.brand_kit), NOT a new rules table. QA failure must name which list
and which rule it broke.
## Step 6 - first end-to-end path (NOT started, gated on spec approval)
1. Upload endpoint: store file, hash it, create asset quarantined with
   kind/category/provenance. Activate endpoint validates and sets active.
2. Worker wires VideoAdapter.photo_motion: job takes 3-6 active Shyftd.ink
   assets + blueprint, produces one 9:16 video, writes renders +
   asset_usage + origin_composition in ONE transaction.
3. Matt posts manually; endpoint records external_posts with its CTA keyword.
4. Endpoints to record metric_snapshots and inquiries manually for now.
5. Weekly report query: per post, views, avg watch time, completion, saves,
   shares, inquiries by CTA keyword, compared to Matt's own median.
## Acceptance tests (automated, against durable DB, and on restored DB)
- Synthetic cannot be inserted or activated as tattoo_documentation or needle_to_skin.
- source_origin / production_method / hash cannot change after activation.
- Active duplicate hash for same user + brand is rejected.
- Render origin_composition matches its asset_usage rows; planned-but-cut asset excluded.
- Second user cannot read/write Matt's rows through API (proves _set_admin fix).
- Full path: upload -> activate -> render -> external_post -> metric_snapshot
  -> inquiry linked by CTA keyword.
- Backup restore succeeds and tests pass on restored DB.
- DB test with KLIPR_DATABASE_URL set must pass, not skip (Step 0 test
  currently skips without a URL - that skip is NOT acceptable for 1A-LITE sign-off).
## A - Close Step 0 (status at spec commit time)
A1 GitHub: repo fattmatt4280/Klipr exists, created 2026-11-04, currently
PUBLIC, empty, size 0. API attempt to make it private returned 403
(token lacks repo-update scope, same as repo-creation 403). Push is BLOCKED
until visibility is changed to private manually in GitHub Settings, or
Matt explicitly approves pushing as public. No code has been pushed yet.
A2 Managed DB: KLIPR_DATABASE_URL has NOT been provided yet. No managed DB
has been created, applied, or tested in this commit. Store the URL in .env
only, never commit it. .env does not exist in the repo.
A3 Restore proof: restore-proof.sh now supports DATABASE_URL mode (see
script header). Managed-DB backup/restore proof is PENDING the URL in A2.
Local proof (23/23) from Step 0 remains the only proven restore so far.
A4 Backups: daily schedule is NOT running off-VM yet. Provider built-in
backups (Supabase/Neon) cannot be verified until a project exists, and
the offsite copy target has NOT been approved yet. Plain statement:
no off-VM daily schedule is running at spec commit time.
A5 Contabo: NOT touched, listed as unchecked until root is reset.
## What this commit does NOT do
No schema change on main (main still has 23 Phase 0 tables).
No schema application to any managed DB.
No endpoints, no render code, no Step 6 implementation.
No secrets, storage files, or backups committed. No .env committed.
No Contabo access, no managed account creation, no paid commitment.
