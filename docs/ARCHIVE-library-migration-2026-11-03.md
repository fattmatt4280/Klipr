# ARCHIVE - Klipr Library Migration Spec, 2026-11-03 (SUPERSEDED)
Status: ARCHIVED, DESIGN ONLY, NEVER IMPLEMENTED.
Superseded for the next milestone by 1A-LITE (docs/KLIPR-1A-LITE-SPEC.md).
Do NOT implement this spec as written. It is preserved here so the design
decisions are not lost, and so 1A-LITE's cuts are auditable against it.
Provenance note, honestly: this spec was delivered in chat on 2026-11-03
as a consolidated copy-paste block ("KLIPR - DATA SPEC AND SCAFFOLD - AS OF
2026-11-03"). No file containing it existed in the repo at that time.
This archive file was created from that chat delivery in the same commit
as the 1A-LITE spec, so the old design is moved to archive, not deleted.
If any detail here conflicts with the 1A-LITE spec, 1A-LITE governs for
the next milestone.
## Scope freeze (old spec)
23 existing tables + 4 new tables = 27 total.
New tables: asset_relationships, project_assets, scene_assets, asset_usage.
asset_shares deferred, not counted; if added later total becomes 28.
No new services or infrastructure. Milestone 1A (library) and 1B
(minimal-render integration) remain separate.
## Phase 0 facts governing the old design
23 tables: users, brands, social_connections, memories, style_profile_rules,
threads, briefs, consent_records, avatars, voices, scenes, assets, audio_tracks,
templates, reference_videos, projects, renders, feedback, posts, subscriptions,
contests, credit_ledger, jobs. No CREATE INDEX anywhere; only UNIQUE besides
PKs is users.oauth_identity. All IDs uuid PK DEFAULT gen_random_uuid()
except templates.id text PK.
assets (Phase 0, 8 columns): id, user_id NOT NULL FK users CASCADE,
brand_id FK brands CASCADE (nullable), type text NOT NULL, storage_path
text NOT NULL, description, shot_tags jsonb DEFAULT '{}', created_at.
No hash/mime/dimensions/license/origin/provenance/usage.
renders: user_id NOT NULL, project_id uuid NOT NULL FK projects CASCADE.
No brand_id, no asset_id, no status column.
posts: user_id NOT NULL, project_id FK projects SET NULL (nullable).
No brand_id, no render_id.
scenes: user_id nullable, no brand_id, no project/brand relationship.
projects: user_id NOT NULL, brand_id nullable, brief_id SET NULL,
template_id SET NULL, input_assets uuid[] NOT NULL DEFAULT '{}' (no FK,
no role/order/brand - cannot be auto-migrated), edl jsonb, render_status
text NOT NULL DEFAULT 'draft' with no CHECK.
jobs: user_id NOT NULL, brand_id FK brands CASCADE (nullable - brand_id
DOES exist), project_id SET NULL, kind NOT NULL, status CHECK
queued/running/done/failed, attempts/max_attempts DEFAULT 3.
templates: user_id nullable, id text PK, no brand column - user/system-scoped.
RLS: 23 policies, one per table, all named owner_or_admin, using
app.current_user_id / app.is_admin session settings, with special cases
for users, scenes (community readable), audio_tracks/templates (NULL-user
system rows readable/writable - a hole), reference_videos (admin-only),
posts (community readable), contests (read-all, admin write).
API flaw carried through the old design: every server DB query used
queue._set_admin(), so the API always saw the admin view and per-user
RLS was NOT exercised through the API.
## Provenance (old spec)
Two fields: source_origin (authentic / synthetic, NULL only for assembled)
+ production_method (original / enhanced / assembled).
Assembled output composition is derived, never collapsed to a single label.
Example: authentic tattoo (authentic/original) + enhanced photo
(authentic/enhanced) + synthetic atmosphere (synthetic/original) =
finished asset NULL / assembled, composition
{authentic_original:1, authentic_enhanced:1, synthetic_original:1}.
Column additions: assets (kind, category, source_origin, production_method,
hash_sha256, mime, file size, duration/width/height/fps, source filename,
visibility, status, license, consent_record_id, allowed/prohibited uses,
bbp_compliant, generator_provider, generator_model, plus
brand_assignment_audit); renders (brand_id, asset_id, origin_composition);
posts (brand_id, render_id); scenes (brand_id).
Kind (Stage 1): photo, video_clip, audio, finished_video, reference_image,
reference_video.
Category: source_photo, source_video, tattoo_documentation, shop_atmosphere,
workstation_prep, equipment_closeup, gloved_hands, needle_to_skin,
artist_working, cleaning_wiping, shop_interaction, transition_broll,
character_reference, environment_reference, hook_clip, transition_clip,
music, voice, sfx, ambient, finished_video. Product reference excluded.
Tattoo gate: synthetic assets can never be tattoo_documentation or
needle_to_skin; synthetic shop_atmosphere/equipment_closeup must carry
prohibited use tattoo_session_representation.
Lifecycle: assets inserted only as quarantined, then relationships created,
then activation. Activation requires the complete invariant per method case.
Provenance immutability: CHECK + BEFORE UPDATE trigger using IS DISTINCT
FROM consistently for all nullable columns + column-level REVOKE on app role;
delete-and-recreate blocked by RESTRICT lineage/usage FKs - archive instead.
## Lineage (old spec)
asset_relationships is asset-to-asset ONLY, types: extracted_from,
enhanced_version_of, alternate_angle_of, version_of, remix_of,
character_reference_for, environment_reference_for.
Removed types: used_in, part_of, rendered_as, published_as.
Separate typed links instead: project_assets (project-to-asset, slot_role),
renders.project_id, renders.asset_id, posts.render_id, scene_assets
(scene-to-asset).
Enhanced cardinality: partial unique index on derivative where type =
enhanced_version_of enforces at most one source; activation also requires
exactly 1 enhanced_version_of and 0 extracted_from/version_of/remix_of for
an enhanced asset. A true T1+T2 combination is assembled (source_origin NULL,
method assembled, inputs via project_assets/render), not enhancement.
## Ownership, NULL-brand bypass, legacy (old spec)
New tables carry denormalized user_id NOT NULL, brand_id NOT NULL.
Parents gain UNIQUE constraints (brands UNIQUE(user_id,id), jobs
UNIQUE(user_id,brand_id,id), and UNIQUE(user_id,brand_id,id) on
assets/projects/renders/posts/scenes after adding brand_id).
Composite FKs: asset_relationships both ends -> assets RESTRICT;
project_assets -> projects CASCADE + -> assets RESTRICT;
scene_assets -> scenes CASCADE + -> assets RESTRICT.
Exception: a composite FK with ON DELETE SET NULL nulls ALL FK columns
including user_id/brand_id, erasing ownership - therefore asset_usage uses
a composite FK only for asset (RESTRICT) and single-column FKs +
INSERT/UPDATE ownership-validation triggers for project/render/post/job.
NULL-brand bypass: Postgres MATCH SIMPLE skips FK check when any
referencing column is NULL. Resolution: new library tables have brand
NOT NULL; for existing tables where brand stays nullable for legacy,
INSERT triggers (app role must insert with brand non-NULL; migration role
exempt) + change-detection UPDATE triggers (IS DISTINCT FROM) block
setting/changing asset_id, render_id, or project_id while brand is NULL.
Legacy mismatches: M0 creates a read-only audit snapshot (table, row id,
user_id, original brand_id, mismatch reason, timestamp) BEFORE any change.
Normalization (M3) then sets live brand_id to NULL for rows whose brand
owner != row user; legitimately owned brands retained; NULL stays NULL;
no brand invented. Assignment later is a third, distinct operation.
Resolvability: assets resolvable only if brand_id non-NULL AND brand owner
= asset user; renders resolvable only via project_id -> projects.brand_id
when non-NULL and owned by render user; posts resolvable only via project
when project_id non-NULL and brand non-NULL and owned by post user;
every legacy scene is brand-unresolvable by definition until owner assignment.
projects.input_assets and scenes.stills_or_clips must NOT be auto-migrated.
## Duplicates (old spec)
Hash is SHA-256 of stored file bytes. Partial unique index on assets
(user_id, brand_id, hash_sha256) WHERE status='active'.
Same user+brand+active duplicate = rejected, returns existing ID to owner only.
Same user+brand+archived duplicate = reactivates same ID (import path).
Same user+different brand = explicit cross-brand import only, new ID, same
hash, NO lineage link, origin/category copied only after explicit
re-attestation, flagged cross_brand_import=true.
Different user = independent import, no leak; duplicate checks RLS-scoped.
## Brand assignment audit (old spec, deferred in 1A-LITE)
One JSONB column brand_assignment_audit added (in M2) to assets, projects,
renders, posts, scenes, jobs - no new table. Stage 1 permits at most one
assignment per row. Trigger assignment_audit_generate (BEFORE UPDATE)
generates the audit itself from OLD row, NEW row, session identity, and a
required attestation read from a transaction-local session setting;
application-supplied audit JSON is never trusted, app role has UPDATE
revoked on the audit column.
Audit fields: original_brand_id (= OLD.brand_id at assignment time - for
normalized mismatched rows this is NULL, NOT the pre-normalization value,
which lives only in the M0 snapshot, linked by table+row id),
assigned_brand_id, assigning_user_id, assigned_at, attestation text,
row_id, table name.
assignment_immutability_guard blocks any later brand or audit change when
audit is already non-NULL; a second assignment/correction is rejected in
Stage 1 and deferred to a separately approved correction process.
Assignment and audit are in the same transaction; a failed transaction
leaves both unchanged.
Eligibility ordering: projects first; renders second (brand must equal
project brand when project_id non-NULL); posts third - a post with
project_id NOT NULL must receive the project brand even when render_id
is NULL; a post with project_id NULL + render_id non-NULL must receive
the render brand; a post with both non-NULL must match both or fail;
jobs after their project (brand = project brand when project_id non-NULL).
Assignment alone never activates an asset.
Attestation clarification: attestation proves only that a non-empty
attestation text was supplied in that transaction and recorded, and that
session user matched row owner then. It is NOT cryptographic, NOT a
signature, NOT independent proof of human identity.
Session identity limitation, honestly stated, not solved: app.current_user_id
/ app.is_admin must be set by the server from a per-user token mapping
held by the server only, never from client-supplied user_id/role, set as
transaction-local with pool reset on return. Postgres custom session
variables are freely settable by the session owner, so there is no DB
privilege preventing a party who already holds application-role SQL
execution from setting them arbitrarily. Full prevention would require
per-user Postgres authentication or a function-only access layer -
both deferred.
## asset_usage state matrix (old spec, deferred in 1A-LITE)
One row per occurrence (same asset twice in a render = two rows,
occurrence_index 1 and 2, distinct timeline).
considered = render_id/rendered_at/post_id/published_at all NULL, next state
selected only; selected = all four NULL, next state rendered only via
completion (render_id set, rendered_at set by trigger); rendered = render_id
+ rendered_at NOT NULL, post_id + published_at NULL, next state published only;
published = all four NOT NULL, next state rendered only via post deletion.
Enforced by CHECK usage_valid_state_matrix_check + triggers.
INSERT of published is always blocked; INSERT of rendered is allowed only
inside a completion transaction (immediate guard + DEFERRABLE INITIALLY
DEFERRED constraint trigger verifying at commit that the render is completed
and composition matches recalculated usage).
Rendered->published requires the referenced post to have same user_id, same
brand_id, and same render_id. rendered_at/published_at are trigger-generated
from transaction time, never trusted from input.
Asset_id is immutable for all usage states; rendered/published rows cannot
be deleted and their occurrence fields cannot change. Considered/selected
rows remain editable/deletable by owner.
## Post deletion, project deletion (old spec)
Post deletion: FK changed to ON DELETE NO ACTION; trigger
post_delete_usage_transition (BEFORE DELETE on posts, SECURITY INVOKER,
not DEFINER, function owned by migration role, fully qualified names,
fixed safe search_path) updates, in the same transaction, only rows where
post_id = deleted post AND user_id/brand_id match the post AND state =
published, setting post_id NULL and state rendered, NOT touching
published_at, renders, or composition. A corrupt cross-user/cross-brand
row is deliberately not updated; the NO ACTION check at statement end
then fails the DELETE, preserving corruption for review.
usage_published_revert_check (DEFERRABLE INITIALLY DEFERRED) verifies at
commit that a published->rendered transition's old post no longer exists.
Project deletion/archival: project with ANY usage (including considered),
any render, or any post cannot be hard-deleted (BEFORE DELETE trigger +
RESTRICT); project with only project_assets and no usage/renders/posts
can be hard-deleted with project_assets CASCADE; empty draft can be
hard-deleted. asset_usage.project_id is RESTRICT, not SET NULL. Archiving
is defined as setting projects.render_status to 'archived' - no new column,
justified because render_status has no CHECK in Phase 0 and no Phase 0
code branches on it, and renders have no status column.
Jobs on an archived project keep project_id and remain audit history but
cannot create new renders; jobs on a deleted draft project get project_id
SET NULL (single-column, safe); a job with usage history cannot be deleted
(asset_usage source_job_id RESTRICT); a job without usage can be deleted,
with the known limitation that credit_ledger.job_id has no FK.
## Render completion (old spec, serialized, idempotent, frozen)
Transaction A creates a draft render (project_id, user, brand,
file_path/asset_id/origin_composition all NULL) and commits it; file
generation happens outside any DB transaction; Transaction B (completion,
atomic) first locks the draft render row with SELECT FOR UPDATE, rechecks
(already completed -> roll back empty and return existing render+asset;
rendered usage without completed render -> abort for manual review;
project archived / brand mismatch / inactive inputs -> abort), then in
order creates the finished asset as quarantined (assembled, source_origin
NULL, kind/category finished_video), inserts rendered usage rows for
exactly the assets in the final rendered file (from the final edit list,
NOT from planned project_assets), calculates origin_composition from
exactly those rows (per group: occurrence count, distinct asset count,
summed duration; considered/selected/cut assets excluded), updates the
render with file_path + asset_id + composition in a single UPDATE, commits.
Transaction C (activation, separate) activates the finished asset only
if the completed render, usage, and composition match.
A render is "completed" only when file_path, asset_id, and
origin_composition are all non-NULL (renders has no status column).
Unique defenses: renders_asset_id_unique partial unique on
renders(asset_id) WHERE NOT NULL, plus asset_usage_idempotency_unique
on idempotency_key. Retry after success returns existing render/asset;
retry after rollback completes cleanly; crash after file generation leaves
draft incomplete with no DB changes; crash after DB completion but before
job-status update is resolved by retry returning existing render.
Correction of a completed render requires a NEW render + NEW finished
asset; old render/usage/composition/asset stay frozen (renders_frozen_guard
blocks changing composition/asset_id/file_path after completion); old
finished asset may be archived, and if the new file has the same hash the
old asset must be archived before the new one can activate.
## Migration sequence (old spec, M0-M7, rollback = restore from M0 backup)
M0 pre-flight audit + read-only snapshot, abort if no DB reachable;
M1a prerequisite uniques on existing columns only (brands, assets, projects,
jobs); M2 nullable column additions only (renders brand_id/asset_id/
origin_composition, posts brand_id/render_id, scenes brand_id, assets
provenance/metadata, brand_assignment_audit); M1b post-column uniques
(renders, posts, scenes); M3 backfill (renders/posts brand derived from
project only when non-NULL and owner-matching) + normalization (projects
first, then renders/posts/jobs, then assets; legacy assets set to
quarantined; scenes brand left NULL); M4 create the 4 new tables in order
asset_relationships -> project_assets -> scene_assets -> asset_usage
(count becomes 27); M5 constraints/indexes/triggers/FK changes; M6 RLS
splits + closing NULL-user insert holes on audio_tracks/templates;
M7 validation (table count 27, inventories, illegal-operation tests in
rolled-back transactions, then 1A, then 1B only if 1A passes).
## Milestones (old spec)
1A Library (L1-L7): import/identity/legacy, classification/immutability,
single-source lineage, retrieval/slot gates, ownership/RLS two-identity
matrix (matt_operator / test_user_2 / matt_admin audit-only),
duplicate/quarantine/assignment, migration validation - independently
testable via direct DB sessions with correct user context (NOT via the
old admin-forcing API), no render/FFmpeg/worker required.
1B Minimal-render integration (R1-R6): assembled render with actual (not
planned) composition including a cut asset excluded, usage states +
retry idempotency, render-time slot gate, Klipr-internal published state
only, repeat appearances (occurrence 2 / distinct 1 / summed duration),
two-phase creation + concurrency + frozen provenance + correction-via-new-render.
1B depends on 1A, reported separately, failure does not fail 1A, external
publishing is NOT in 1B.
Verdicts (old spec): 1A ready for implementation conditional on
incorporating all corrections verbatim and on M7 proving the mechanisms
in the target Postgres version; 1B ready for test-harness integration
only, NOT a production render pipeline approval.
## Deferred in the old 27-table design
asset_shares, public registration/onboarding/team permissions, OAuth,
S3/signed URLs/storage proxy, Redis, vector DB/embeddings, Production
Brain, external publishing, editor, planning chat, brand import,
community, avatar/voice beyond existing consent tables, billing beyond
existing ledger, dedicated project status column, fixes to
feedback.target_id / credit_ledger.job_id / brands default avatar+voice
FKs / reference_videos ownership / subscriptions unique pair / contests
ownership, perceptual dedup, performance scoring formula, production
render pipeline, system-scene assignment, user-deletion anonymization
for RESTRICT history, final tattoo transform allowlist confirmation,
cryptographic attestation, per-user Postgres auth / function-only access.
## Honest limitations (old spec)
Live DB never verified in that chat (M0 mandatory, no row counts assumed);
M0 snapshot is an external file with no FK to the DB assignment audit -
if the file is lost, the pre-normalization mismatched brand value is lost
from the live DB; draft-render creation idempotency by job is NOT
DB-guaranteed (renders has no job_id column, none added); DB lock does
not serialize file writes (render file paths must be render-specific);
superuser/migration role can bypass triggers/RLS (M7 recalculation is
detection, not prevention for that role); deferred constraint trigger
behavior and column-REVOKE + definer-rights trigger interaction must be
proved by M7 in the target Postgres version, with stated weaker fallbacks
if they fail; the deferred completion check proves a render completion
with matching composition exists, it does NOT verify video file content
against usage rows.
This spec is DESIGN ONLY. Implementation is NOT authorized by this archive alone.
