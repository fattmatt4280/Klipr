#!/usr/bin/env python3
"""Create a user token for a Klipr user_id, storing only its hash.
Usage: KLIPR_USER_TOKEN_FILE=.klipr_user_tokens python3 scripts/seed_user_tokens.py <user_id> [--admin]
Prints the token ONCE. Deliver it securely, never log it, never commit the file.
The file is mode 600 and gitignored. Existing tokens are never re-printed.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.user_auth import UserAuth, default_token_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: seed_user_tokens.py <user_id> [--admin]", file=sys.stderr)
        sys.exit(2)
    tok = UserAuth(default_token_file()).create_token(sys.argv[1], is_admin="--admin" in sys.argv[2:])
    print(tok)
