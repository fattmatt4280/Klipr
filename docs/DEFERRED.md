# KLIPR 1A-LITE - DEFERRED
Everything listed here is explicitly NOT built in 1A-LITE. Deferred means
design and hold, not an invitation to start building. Each item needs its
own approval and its own milestone before it is built.
## Deferred from the 2026-11-03 library migration spec (27-table design)
- asset_shares (sharing / permissions for assets). If added later, total
  tables go from 29 to 30, and a new design review is required.
- scene_assets (scene-to-asset links). Scenes table remains, unlinked, in 1A-LITE.
- brand_assignment_audit column (JSONB on assets, projects, renders, posts,
  scenes, jobs), attestation, assignment ordering rules, and assignment
  immutability guards. Stage 1 one-time assignment design is archived in
  docs/ARCHIVE-library-migration-2026-11-03.md, not built here.
- Legacy migration M0-M7 in full: M0 read-only audit snapshot, M3
  normalization/backfill, legacy resolvability rules, legacy
  quarantine-by-default for existing rows. Only applies if live legacy
  data is found on the durable host - see spec Step 1.
- Deferred constraint triggers: usage_render_completion_check,
  usage_published_revert_check.
- post_delete_usage_transition and the full published/rendered usage state
  machine. In 1A-LITE, asset_usage is considered / selected / rendered only;
  published tracking is external_posts.
- Split per-operation RLS policies (separate SELECT/INSERT/UPDATE/DELETE
  policies, admin audit-only). Phase 0 owner_or_admin policies remain,
  with the server.py SET LOCAL fix as the 1A-LITE improvement.
- Session-variable impersonation hardening beyond SET LOCAL + server-side
  token mapping + pool reset. Full prevention needs per-user Postgres
  authentication or a function-only access layer - both out of scope.
- Project archival convention (archiving via projects.render_status =
  'archived', frozen project_assets, etc.). Archived vs deleted project
  policy is not built in 1A-LITE; project deletion rules from the old spec
  are archived, not enforced here beyond existing FKs.
- System-scene assignment, user-deletion anonymization for RESTRICT history.
## Deferred from the original product spec (2026-10-25, still deferred)
- Public registration / onboarding, team permissions, OAuth (production).
  Local admin token is proof only, rotation doc is docs/ADMIN-TOKEN-ROTATION.md.
- S3 / R2 / B2 storage, signed URLs, storage proxy. Local storage driver
  is proof only, not S3.
- Redis queue swap (Postgres jobs table remains in 1A-LITE).
- Vector DB / embeddings, Production Brain, planning chat, brand import
  walkthrough, community / remix / contests (beyond existing tables),
  editor, avatar/voice beyond existing consent tables.
- External publishing via API, API metric pulls (metric_snapshots are
  manual in 1A-LITE).
- Billing beyond existing credit_ledger (billing_enabled=false until Phase 7).
- Production render pipeline beyond the single photo_motion test path in Step 6.
## Deferred by design in 1A-LITE itself
- Perceptual dedup (hash is SHA-256 of file bytes only; re-encode changes hash).
- Performance scoring formula beyond the weekly report query in spec Step 6.5.
- Cryptographic attestation (attestation in the old spec was never
  cryptographic; in 1A-LITE it is deferred entirely, not downgraded silently).
- Dedicated project status column (projects.render_status has no CHECK in
  Phase 0; no new column is added in 1A-LITE).
- Fixes to unenforced Phase 0 references: feedback.target_id, credit_ledger.job_id,
  brands default_avatar_id / default_voice_id (no FK), reference_videos
  ownership (no user_id), subscriptions unique pair, contests ownership /
  created_at. These are known, not fixed, in 1A-LITE.
- Final tattoo transform allowlist confirmation (enhanced assets).
- Rules table for BBP / style (see docs/BBP-STYLE-SPLIT.md - JSON in
  templates.recipe / brands.brand_kit in 1A-LITE, no new table).
- Managed Postgres paid tier, Contabo VPS deployment, DWW mount Publish.
  All remain gated on their own approvals (root reset, URL provision,
  offsite target approval).

## Evolution Engine — END GOAL (2026-11-08, from Matt + ChatGPT conversation 2026-11-07)
- This is where Klipr is headed — the destination, not a "maybe someday"
  item. Full plan at docs/EVOLUTION-ENGINE.md. Self-optimizing creative
  platform: Creative Brain (makes videos) vs Evolution Brain (learns how to
  make them better). Five phases E1–E5: behavioral instrumentation → personal
  intelligence → adaptive workflows → experimentation → autonomous creative
  intelligence (knowledge graph).
- E1 (instrumentation) folds into the rebuild so data collection starts from
  day one. E2 (personal intelligence) after the rebuild is live and Matt uses
  it daily. E3–E5 deferred until there is real behavior data and real users —
  E4 (experiments) is meaningless with one user, E5 (knowledge graph) needs
  hundreds of published videos with measured outcomes.
- Hard gates before any phase is trusted: rebuild done, validation loop
  closed (video posted + metrics + inquiries), Library/generation/performance
  capture reliable. Do not build on incomplete data.
- Each phase needs its own go-ahead. Do not start E3–E5 without one.
