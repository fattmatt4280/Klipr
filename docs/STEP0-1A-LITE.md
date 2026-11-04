# Klipr 1A-LITE - Step 0 report

Date: 2026-11-03 (Step 0 run, after adoption of 1A-LITE)
Scope of this report: Step 0 ONLY. Schema diff (1A-LITE tables/columns) and
Step 6 (upload / render / post / metrics path) are NOT started here.

## 0.1 Git

- Initialized git in ~/workspace/klipr, branch main.
- Commit 39ac4cb: Phase 0 pristine state, 2026-10-26/27 build, before 1A-LITE Step 0.
- Commit 83bbec2: Fix .gitignore - keep db/schema.sql tracked (source of truth).
  Note, honestly: the first commit missed db/schema.sql because the initial
  .gitignore contained a blanket *.sql rule. That was caught by checking
  `git ls-files`, fixed by removing *.sql (dumps live in gitignored
  backups/, not in db/), and committed as a second commit. Do not amend
  history to hide that fix - the two commits are the audit trail.
- .gitignore excludes: .env, .env.*, .klipr_admin_token, *.token, storage/,
  storage_staging/, backups/, *.dump, crm/, __pycache__/, .venv/.
  It does NOT exclude db/schema.sql.
- Local git identity for these commits is Matt Faxon / matt@localhost
  (local-only placeholder, not a real email, not pushed anywhere).
  There is no remote configured yet. Do not push until a remote is
  explicitly approved.

## 0.2 Live data - what was found

Checked on this VM, then proven by starting a fresh cluster:

- At Step 0 start, Postgres was NOT installed in this VM. No
  /var/lib/postgresql/, no /etc/postgresql/, no psql/pg_dump binaries,
  no psycopg2 module. This is a VM replacement effect: the previous VM
  had Postgres 16, this VM does not. System installs do NOT survive VM
  replacement (see AGENTS.md).
- Postgres 16.15 was then installed from cached .deb files in
  /var/cache/apt/archives via dpkg (not apt, because system apt was
  locked by a VM boot apt process, process 780, which was NOT killed).
  A fresh cluster 16/main was created, started, and listed only
  postgres / template0 / template1 - NO klipr, NO klipr_staging, NO
  user data. That is the definitive Step 0.2 finding for this VM.
- After that, klipr and klipr_staging were created fresh and
  db/schema.sql was applied to both. Result: 23 tables each, 0 rows in
  users, brands, assets, jobs (and by construction, 0 rows elsewhere -
  schema only, no seed data was inserted).
- Storage files: none at Step 0 start. No storage/, no backups/, no
  crm/ directory in ~/workspace/klipr. queue/ and templates/ are empty.
  A test storage file was created only to prove the backup manifest,
  then deleted (see 0.3).
- Secrets: no .env, no .klipr_admin_token file in the repo. Only
  .env.example exists, with placeholder values.
- Code only: the Oct 27 deploy bundle ~/workspace/klipr-deploy.tar.gz
  exists, but it is code, not user data.

Conclusion for Step 1: in this workspace/VM, there is NO live Klipr data
worth keeping, so the Step 1 fresh-schema condition is met HERE.
Caveat, stated plainly: this does NOT prove that the Contabo VPS
(217.216.94.215) holds no Klipr data, because VPS access is blocked
(root login rejected, unanswered since Oct 28) and was not checked in
this run. Before recreating any schema on a shared/durable host, check
that host's DBs and report counts. Do not delete anything on Contabo
based on this VM-only finding.

## 0.3 Durable Postgres - recommendation and what was actually set up

Recommendation:

- Primary durable host for 1A-LITE: a managed Postgres free tier to start
  (Neon / Supabase free tier), because (a) Muse VM Postgres is ephemeral
  by design and was already lost twice, (b) Contabo VPS root login is
  blocked, so Contabo cannot be set up until that reset succeeds,
  (c) a free tier requires no new paid commitment to prove backup/restore.
- Do NOT commit to a paid managed tier yet. Paid pricing was not verified
  live in this run, and 1A-LITE does not need paid scale to prove the
  first end-to-end path.
- Long-term: move to Contabo VPS once root is reset, OR stay managed if
  Contabo stays blocked. Either way, the durable store must NOT be
  /var/lib/postgresql on a Muse VM.

What was actually set up in this run (workspace-durable, not external):

- scripts/backup-durable.sh: pg_dump to ~/workspace/klipr/backups/
  (home directory, survives VM replacement, gitignored), plus a storage
  manifest and a SHA-256 checksum per dump. Offsite copy is NOT assumed;
  if KLIPR_BACKUP_REMOTE is set, the script prints it and stops - the
  copy must be run explicitly with a verified rclone/rsync config.
- scripts/restore-proof.sh: restores a backup into klipr_restore_test,
  verifies table count against an expected count passed as an argument
  (default 23 for Phase 0, pass 29 for 1A-LITE after the schema change),
  then drops the test DB. It does NOT support DATABASE_URL mode in this
  proof version - it must run on the Postgres host with local psql access.
- Automated daily pg_dump: NOT yet wired as a running cron in this VM.
  The backup script is ready and proven manually (see above), but a
  daily schedule must be set up on the durable host once it is chosen
  (cron on Contabo, or the managed provider's backup schedule, plus a
  daily run of backup-durable.sh to workspace). Claiming a daily cron is
  running now would be false - it is a script ready to schedule, not a
  running schedule. This is the one Step 0.3 item that remains open,
  and it cannot be closed until the durable host is chosen, because a
  cron on this ephemeral VM would not survive VM replacement either.

Restore proof status - PROVEN in this run, with limits stated:

- Postgres 16.15 was installed from cached .deb files via dpkg (system
  apt lock process 780 was NOT killed; dpkg did not need the apt lists
  lock at the time it ran).
- Backup run: DB=klipr, BACKUP_DIR=backups, output
  backups/klipr-20261104T022150Z.sql, 41K, SHA-256 checksum verified OK,
  manifest contained the test storage file
  storage/testuser/testbrand/photo/test.txt (created only for this
  proof, then deleted - final storage/ state is empty again).
- Restore run: ./scripts/restore-proof.sh
  backups/klipr-20261104T022150Z.sql 23
  Result: OK, table count in restored DB = 23, expected = 23,
  test DB klipr_restore_test dropped, no restore test DB remains.
- Two permission fixes found and fixed during this proof, honestly
  recorded: (1) the repo directory is 2770, so the postgres user
  cannot traverse into backups/ or read db/schema.sql directly -
  schema was applied from a /tmp copy, and restore-proof.sh now copies
  the backup to /tmp with mode 644 for the restore, then deletes the
  temp copy, with a trap to drop the test DB on failure; (2) backup
  and restore scripts now run pg_dump/psql via sudo -u postgres when
  run as root with no DATABASE_URL, because Postgres peer auth
  otherwise rejects root. Both fixes are in the scripts, not hidden.
- Limits: this proof is for a local VM Postgres, NOT for a managed
  Postgres and NOT for Contabo. It proves backup/restore logic and
  schema application, not durability across VM replacement - that
  durability comes from the backup files living in
  ~/workspace/klipr/backups/ (home, survives VM replacement, gitignored)
  plus a managed/Contabo host chosen next, not from /var/lib/postgresql
  on this VM, which will be lost again on the next VM replacement.

## 0.4 Admin token rotation

- Full procedure is in docs/ADMIN-TOKEN-ROTATION.md.
- Summary: lost token cannot be recovered, only rotated (delete token
  file, re-seed, print once, store in vault, restart server, verify old
  fails / new succeeds). Token file is mode 600, hash only, gitignored.
- No token was seeded, rotated, or stored in this run, because there is
  no running server or token file to rotate. The procedure is documented,
  not executed against live credentials.

## 0.5 Requirements and test runner

- requirements.txt: psycopg2-binary>=2.9.9 only, plus ffmpeg as a system
  binary (not pip) and Python 3.12 stdlib. No pytest required.
- scripts/run_tests.sh: runs `python3 -m unittest discover -s tests -v`.
- tests/test_step0.py: schema file has 23 Phase 0 tables, 1A-LITE tables
  NOT yet applied, RLS enabled, .gitignore excludes secrets/dumps but
  not db/schema.sql, schema.sql is tracked in git, requirements lists
  psycopg2, storage traversal rejection + roundtrip, auth seed-once +
  check + hash-only file, and a DB test that skips when no DATABASE_URL
  is set (so it does not falsely fail Step 0) and really connects when
  one is set.
- Test result for this run: ./scripts/run_tests.sh
  Ran 10 tests in 0.024s, OK (skipped=1).
  9 passed, 1 skipped: the DB test skipped because KLIPR_DATABASE_URL
  is not set (see test code - it skips instead of falsely failing
  Step 0, and really connects when a URL is set).
  Tests cover: schema has 23 Phase 0 tables, 1A-LITE tables NOT yet
  applied, RLS enabled, .gitignore excludes secrets/dumps but not
  db/schema.sql, schema.sql is tracked in git, requirements lists
  psycopg2, storage traversal rejection + roundtrip, auth seed-once +
  check + hash-only file.

## What was NOT done in Step 0

- Old spec was NOT moved to docs/ARCHIVE-library-migration-2026-11-03.md
  yet, because that move is part of adopting the revised spec as the
  controlling document, and the schema diff itself has not been applied.
  The old 27-table design remains in chat history and in MEMORY.md, and
  the 1A-LITE revised spec from the previous turn is the design to
  review before Step 6. Archiving the old spec file should happen when
  the schema diff is applied, so the archive and the new spec are
  committed together, not as a lone file move.
- schema.sql was NOT changed. It still contains exactly the 23 Phase 0
  tables. No assets columns, no external_posts, no metric_snapshots,
  no inquiries, no blueprint column were added in Step 0.
- Step 6 (upload / activate / photo_motion render / external_post /
  metrics / inquiries endpoints) was NOT started.
- No managed Postgres account was created, no Contabo VPS was accessed,
  no credentials were stored, and no paid service was committed to.
