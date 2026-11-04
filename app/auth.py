"""Auth, Phase 0 proof.
Production OAuth: the public app's OAuth system (e.g. Supabase Auth) must map its
authenticated user to (user_id, is_admin) and set Postgres session settings
app.current_user_id / app.is_admin before any query — see db/schema.sql.
This file is the LOCAL proof implementation only: a single admin seed + bearer
tokens stored outside the DB, with no passwords stored in code or files.
It is NOT production OAuth, and must not be presented as such.
"""
import json, secrets, hashlib
from pathlib import Path

class Auth:
    def __init__(self, token_file):
        self.token_file = Path(token_file)
    def seed_admin_token(self):
        """Create (once) a bearer token for Matt/admin testing. Returns token only here,
        never log it to CRM or memory. Store file mode 600."""
        if self.token_file.exists():
            return None  # already seeded; do not re-issue / print existing token
        token = secrets.token_urlsafe(32)
        self.token_file.write_text(hashlib.sha256(token.encode()).hexdigest() + "\n")
        try: self.token_file.chmod(0o600)
        except Exception: pass
        return token
    def check_token(self, token):
        if not token or not self.token_file.exists(): return False
        want = self.token_file.read_text().strip()
        return secrets.compare_digest(hashlib.sha256(token.encode()).hexdigest(), want)
