"""Per-user token auth for Step 6 library operations, NOT the Phase 0 admin token.

The Phase 0 admin token must NOT be used for library operations in 1A-LITE.
This module maps a bearer token to (user_id, is_admin) from a server-side
file that holds only SHA-256 hashes, mode 600, outside git. The file format
is JSON: {sha256(token): {"user_id": "<uuid>", "is_admin": false}, ...}

Role is taken from the users row in the DB at request time when possible,
but the mapping file is the source of truth for which user a token belongs
to. The client never supplies user_id or role; the server resolves both
from the token, then sets Postgres session variables transaction-locally.

Honest limitation, from the spec: Postgres custom session variables are
freely settable by any session owner, so a party already holding
application-role SQL execution can set them arbitrarily. Full prevention
needs per-user Postgres authentication or a function-only access layer,
both deferred. What this module does enforce, through the API, is that
a user token can only read/write rows whose user_id matches the token's
user_id (via RLS owner_or_admin policies), and admin tokens are separate.
Admin read-all is audit only; admin write to another user's private
assets is blocked in server code for Step 6 endpoints.
"""
import hashlib
import json
import os
import secrets
from pathlib import Path


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class UserAuth:
    def __init__(self, token_file):
        self.token_file = Path(token_file)

    def load(self):
        if not self.token_file.exists():
            return {}
        try:
            data = json.loads(self.token_file.read_text())
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def resolve(self, token):
        """Return (user_id, is_admin) or None if the token is unknown."""
        if not token:
            return None
        entry = self.load().get(token_hash(token))
        if not entry or not isinstance(entry, dict):
            return None
        user_id = entry.get("user_id")
        if not user_id:
            return None
        return (str(user_id), bool(entry.get("is_admin", False)))

    def create_token(self, user_id, is_admin=False):
        """Create a new token for a user_id, store only its hash, return
        the token once. Caller must deliver it securely to the user and
        never log it, never commit the file, and keep the file mode 600."""
        token = secrets.token_urlsafe(16)  # 22 chars, fits on one Termius line; 128-bit. Was (32)/43 chars, which wrapped and kept getting copied in pieces.
        data = self.load()
        data[token_hash(token)] = {"user_id": str(user_id), "is_admin": bool(is_admin)}
        self.token_file.write_text(json.dumps(data, indent=2) + "\n")
        try:
            self.token_file.chmod(0o600)
        except Exception:
            pass
        return token


def default_token_file():
    return os.environ.get("KLIPR_USER_TOKEN_FILE", ".klipr_user_tokens")
