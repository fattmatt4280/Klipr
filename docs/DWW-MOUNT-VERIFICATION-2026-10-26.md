# DWW mount — verification, 2026-10-26

## Tested on VM
- API server (app/server.py): health 200, billing_enabled false, phase 0, dww_mount true.
- Protected endpoints: no token -> 401. With admin token -> 200.
- /brands returns Test Brand Only. /jobs returns queued analyze job.
- /templates returns [] (no templates seeded yet — Phase 1 recipe not built, correct).

## Incident during test (kept in record)
- Postgres cluster was down and klipr/klipr_staging DBs were GONE on re-check
  (only postgres/template0/template1 remained). Home files survived, /var/lib
  Postgres data did not. This is why schema.sql in home is the source of truth,
  and why VM proof DB is NOT production. Recreated both DBs + klipr_app role
  from schema.sql in minutes, re-seeded test brand/job, API test passed again.
- Lesson for VPS: schema-as-code + backups are mandatory, not optional.
  Do NOT rely on a VM-local Postgres DB as durable storage.

## NOT live yet
- DWW mount page is a file in this repo (dww-mount/klipr-mount.html), NOT yet
  added to the DWW Lovable project, NOT yet Published. Matt must add it as a
  hidden page + Publish.
- Klipr API is NOT yet deployed to Contabo, NOT yet front-doored over HTTPS.
  DWW page will show "API unreachable" until that deploy + Caddy/proxy step is done.
- Voicebox: not in this mount. Phase 0/1 needs no voice; voice is a remote
  adapter to Contabo when built.
