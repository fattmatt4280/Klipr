# Klipr Phase 0 — Verification, 2026-10-26 (VM proof)

Built on VM at Matt's 05:26 EDT go-ahead ("build on the vm and push it to the vps").
Phase 1 NOT started.

## Tested and passing (tool output, not claims)
- Postgres 16 cluster started (was down, now online).
- Schema applied clean to klipr AND klipr_staging after fixing a policy bug:
  initial schema loop included `users` (which has id, not user_id) and aborted the
  policy block; fixed by excluding users from that loop and handling it separately.
- Tables: 23. RLS enabled: 23. Policies: 23 (one per table, owner_or_admin, with
  special cases for scenes/audio_tracks/templates/posts/contests/reference_videos).
- RLS read check: superuser sees 1 queued job; klipr_app (non-admin, no session
  user set) sees 0 jobs — RLS filtering, not an error.
- Job queue: analyze job enqueued, worker claimed it, first run failed on a real
  bug (Config.crm_log vs crm_log_path), job correctly retried (attempts 1, status
  queued), bug fixed, second run: status done, attempts 2, CRM JSONL event written.
- Storage: LocalStorage put/get_path works, path layout user/brand/kind/file,
  traversal rejected.
- Auth: admin token seed, check ok, check bad fails, token file mode 600, hash only.
- Backup: pg_dump 46,942 bytes + manifest. Restore test: restored into
  klipr_restore_test, verified 23 tables, test DB dropped. Initial restore failed
  on backup dir permissions (770); fixed in backup.sh (chmod 755 dir, 644 files).
- Command Center link: klipr entry added to command-center/projects.yaml, path
  ../klipr, registry only — no code in klipr imports Command Center code.

## Bugs found and fixed during proof (kept in record, not hidden)
1. Schema policy loop including users.
2. Worker Config.crm_log attribute name.
3. Backup dir permissions blocking postgres restore read.

## VPS push — tested, failed direct, indirect route ready
- ssh vps (217.216.94.215, egress proxy): "Connection timed out during banner
  exchange / Connection to 198.19.0.1 port 3128 timed out" (2026-10-26).
  This is the same blocker as Oct 24-25, not a new code failure.
- Direct push from Muse: NO.
- Indirect push: YES. Bundle /tmp/klipr-deploy.tar.gz (44K, rebuilt without
  pycache/storage/crm test data before delivery — rebuild if files change after
  this note). Matt copies it to /root/klipr on the VPS, then pastes
  scripts/deploy-vps.sh in Termius. That script installs postgres/ffmpeg/python,
  creates klipr + klipr_staging, applies db/schema.sql to both.
- Alternative: if Matt enables Direct network protocols on web muse.ai (NOT iOS),
  direct SSH may work again — untested, do not assume.

## Still NOT done (VPS / later steps, do not claim otherwise)
- Production OAuth provider, S3/R2/B2 credentials, Redis queue swap, offsite
  backup remote, systemd worker, Next.js front end, production admin seed.
- VM proof stack: Python stdlib + Postgres 16 + Postgres jobs table, NOT Next.js/
  Supabase/Redis. Interfaces match spec; front end is not built.
- Test password 'klipr-proof-only-not-production' for role klipr_app exists ONLY
  on this VM's Postgres for the proof. Change/remove it before any production use,
  and never reuse it on the VPS.
- Test data (admin test user, test brand, analyze job) remains in VM klipr DB only.
  VPS deploy starts clean from schema.sql.

## Next step for Matt
Approve the indirect push route (Termius bundle) or the web muse.ai toggle check,
then Phase 1 can start — it still needs the Tattoo Reveal reference set.
