# Klipr - Backup Daily Schedule (Step 0 close, A4)
Plain statement first: NO daily schedule is running off-VM at the time
of this commit. Claiming otherwise would be false.
What is ready:
- scripts/backup-durable.sh: pg_dump to backups/ in the workspace
  (home, survives VM replacement, gitignored), plus storage manifest
  and SHA-256 checksum per dump. Supports KLIPR_DATABASE_URL mode
  (pg_dump via URL) and local mode (sudo -u postgres).
- scripts/restore-proof.sh: restores a backup into klipr_restore_test,
  verifies table count, drops the test DB. Now supports DATABASE_URL
  mode (admin/test URLs derived from KLIPR_DATABASE_URL by replacing
  the database name, URL never echoed). Proven locally in DATABASE_URL
  mode: backup 41K, checksum OK, restore 23/23, test DB dropped.
  Managed-DB proof is still pending a real managed URL (see below).
What is NOT ready, and why:
1. Managed DB project does not exist yet. KLIPR_DATABASE_URL has NOT
   been provided. Therefore:
   - Provider built-in backups (Supabase / Neon) cannot be verified,
     enabled, or scheduled yet. They are the first layer of the plan,
     not a running backup.
   - No daily backup-durable.sh run is scheduled against a managed DB,
     because there is no managed DB to back up.
2. Offsite copy target has NOT been approved yet. Therefore:
   - No off-VM copy is running. Backups in backups/ are on-VM (workspace)
     only, which survives VM replacement but is NOT offsite and is NOT
     a separate provider.
   - backup-durable.sh prints KLIPR_BACKUP_REMOTE if set, but does NOT
     copy automatically. The copy must be run explicitly with a verified
     rclone/rsync config, and restore must then be proven from the
     offsite copy, not just from the local file.
Planned daily schedule, to be wired once A2 + offsite approval are done:
- Daily, provider built-in backup (Supabase/Neon schedule, as configured
  in that project - retention per provider plan).
- Daily, backup-durable.sh dump from the managed DB, with manifest +
  checksum, copied off the VM to the approved offsite target.
- Weekly (or after any schema change), restore-proof.sh from the
  offsite copy into a throwaway DB, verifying table count.
- Daily schedule must run OFF the Muse VM (on the managed provider,
  on Contabo once root is reset, or via a durable scheduler), NOT as
  a cron on this ephemeral VM, because a VM cron would not survive
  VM replacement and would back up a local DB that is not the durable DB.
Contabo (A5): NOT touched, listed as unchecked until root is reset.
Do not schedule, access, or delete anything on Contabo based on this doc.
What would unblock this schedule:
- Matt provides KLIPR_DATABASE_URL for the managed project (store in
  .env only, never commit .env, never paste the URL into chat logs
  or git).
- Matt approves an offsite target (provider / bucket / rsync destination
  and credentials via secure vault, not in chat).
Once both are provided, the next run should: apply schema to the managed
DB, run backup-durable.sh + restore-proof.sh in DATABASE_URL mode
against the managed DB and report table counts, then wire the daily
schedule on the durable host and verify it runs once.
