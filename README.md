# Klipr — Phase 0 (built on VM, 2026-10-26)

Status: Phase 0 foundation built and tested on this VM. Phase 1 NOT started.
Direct push to the VPS was TESTED and FAILED (see below) — VPS delivery is via
the Termius bundle route, not direct SSH.

## What Phase 0 is, per spec
Separate app (own DB schema/routes, Command Center mounts it, never imports CC code),
staging env, object storage from day one, daily backups + tested restore, OAuth +
admin + billing_enabled=false, RLS on every table, job queue, OpenRouter adapter with
credit metering + CRM logging, per-capability adapters.

## Stack adjustment (stated, not hidden)
Spec suggests Next.js + Supabase + Redis. VM proof uses Python stdlib + local
Postgres 16 + Postgres jobs table instead of Redis, because that is testable here
without new credentials. Interfaces (schema, queue fields, storage path layout,
adapter classes) match the spec, so swapping to Next.js/Supabase/Redis on the VPS
does not change the data model or job kinds. Do NOT present this proof as the
Next.js production app — that front end is not built yet.

## What is real vs stubbed (honest)
Real and tested on VM: Postgres schema with RLS, prod + staging DBs, job enqueue/
claim/retry, worker for analyze (proof adapter, no spend), storage adapter (local
driver, S3-shaped paths), CRM JSONL logging, backup dump + restore test, admin
token file (mode 600, hash only).
Stubbed / VPS steps, NOT done: production OAuth provider, S3/R2/B2 credentials,
Redis queue swap, offsite backup remote, systemd worker service, Next.js front end.
Local storage is NOT S3. Local auth is NOT production OAuth.

## Push to VPS — tested result 2026-10-26
`ssh vps` (217.216.94.215 via egress proxy): timed out during banner exchange /
proxy timed out. Same blocker as Oct 24-25. So:
- Build on VM: YES, done here.
- Direct push from Muse: NO, blocked.
- Indirect push: YES — package `klipr-deploy.tar.gz` (this folder + deploy script),
  Matt copies it to /root/klipr on the VPS (Termius upload, or curl a link he
  approves), then pastes `scripts/deploy-vps.sh` on the VPS via Termius.
  Alternative if Matt enables it on web muse.ai: Direct network protocols toggle
  (NOT iOS — already confirmed missing there).

## Run the proof (VM)
sudo -u postgres psql -c "CREATE DATABASE klipr;" -c "CREATE DATABASE klipr_staging;"
sudo -u postgres psql -d klipr -f db/schema.sql
sudo -u postgres psql -d klipr_staging -f db/schema.sql
KLIPR_DATABASE_URL="postgresql://..." python3 -m app.worker --once  # needs psycopg2
./scripts/backup.sh && ./scripts/restore-test.sh backups/*.sql

## Files
db/schema.sql, app/config.py, app/storage.py, app/auth.py, app/crm.py,
app/adapters.py, app/queue.py, app/worker.py, scripts/backup.sh,
scripts/restore-test.sh, scripts/deploy-vps.sh, .env.example
docs/: Klipr-Product-Spec.md (verbatim), RECONCILIATION-2026-10-25.md,
PHASE1-CHECKLIST.md, PHASE0-VERIFICATION-2026-10-26.md (after test run)
