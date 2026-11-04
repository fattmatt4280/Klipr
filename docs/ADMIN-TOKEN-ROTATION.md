# Klipr admin token - rotation / reset procedure (1A-LITE Step 0)

## What is true, and what is not

- The admin token itself is NEVER stored. Only its SHA-256 hash is stored,
  in the file named by KLIPR_AUTH_TOKEN_FILE (default: `.klipr_admin_token`),
  mode 600, via `Auth.seed_admin_token()` in `app/auth.py`.
- A lost token CANNOT be recovered. There is no retrieval path, by design.
  Anyone who claims to retrieve it is wrong - the token value was only ever
  printed once, at seed time, and was never logged to CRM or memory.
- A lost token CAN be rotated. Rotation replaces the old hash with a new one.
  The old token stops working immediately after rotation, because the hash
  file no longer matches it.

## Rotation procedure (admin / migration role only, not via the API)

1. Stop the Klipr API/worker if it is running, or accept that requests in
   flight with the old token will start failing after step 3.
2. Delete the old token file:
   `rm /path/to/.klipr_admin_token`
   Do NOT try to read the old token from the file - the file contains only
   a hash, not the token.
3. Re-seed a new token. In Python, from the klipr directory:
   `python3 -c "from app.auth import Auth; print(Auth('.klipr_admin_token').seed_admin_token())"`
   This prints the new token ONCE. Copy it immediately into your password
   manager / secure vault. Do not paste it into chat, email, CRM logs, or git.
   If you lose this printout, repeat the procedure - do not try to recover it.
4. Confirm the new token file is mode 600:
   `chmod 600 /path/to/.klipr_admin_token && ls -l /path/to/.klipr_admin_token`
5. Restart the API/worker.
6. Verify: a request with the new token succeeds, a request with the old
   token fails with 401. Do not test by logging the token anywhere.

## What NOT to do

- Do NOT commit `.klipr_admin_token`, `.env`, or any token value to git.
  `.gitignore` already excludes `.env`, `.klipr_admin_token`, and `*.token`.
- Do NOT store the token in `docs/`, `README.md`, or any file in this repo.
- Do NOT use the Phase 0 shared admin token for owner-context library
  operations in 1A-LITE. Library operations must use per-user token mapping
  (server sets `app.current_user_id` from the token mapping, never from a
  client-supplied user_id). The admin token is for system/admin operations
  only, and its use for library writes is deferred out of 1A-LITE.
- Do NOT rotate by editing the hash file by hand. The hash must be produced
  by `seed_admin_token()` (SHA-256 of the token, plus a trailing newline),
  otherwise `check_token()` will never match.

## If rotation fails

- If `seed_admin_token()` returns `None`, the token file already exists.
  Delete it first (step 2) and re-run step 3. Do not edit the existing file.
- If the new token still fails, check: (a) the server was restarted and is
  reading the same token file path as `KLIPR_AUTH_TOKEN_FILE`, (b) the file
  mode is 600 and readable by the server user, (c) no second token file in
  a different working directory is being used instead.
