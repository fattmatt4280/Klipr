"""Minimal Klipr API server, Phase 0 DWW mount.
Stdlib only + psycopg2. This is a TEST API, not the full Klipr app and not the
Phase 2 planning chat or Phase 3 editor.
Endpoints: GET /health (public), GET /templates, GET /brands, GET /jobs,
POST /jobs (enqueue, body: {kind, payload, credit_cost, brand_id, project_id}).
Protected endpoints require: Authorization: Bearer <admin token>
  (token hash checked via app/auth.py; token file is NOT in code, NOT in DWW).
CORS: only dreamwebworkz.com, *.lovable.app, and localhost (VM proof).
Worker must run separately on the same server (app/worker.py) — this server
enqueues jobs, it does not execute them inline.
Usage: KLIPR_DATABASE_URL=... KLIPR_AUTH_TOKEN_FILE=... python3 -m app.server --port 8890
"""
import argparse, json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import CONFIG
from app.auth import Auth
import app.queue as queue

ALLOWED_SUFFIXES = (".dreamwebworkz.com", "dreamwebworkz.com", ".lovable.app", "localhost", "127.0.0.1")

def _allowed_origin(origin):
    if not origin: return None
    try:
        host = urlparse(origin).hostname or ""
    except Exception: return None
    if host == "dreamwebworkz.com" or host.endswith(".lovable.app") or host in ("localhost", "127.0.0.1"):
        return origin
    return None

def _conn():
    import psycopg2
    if not CONFIG.database_url: raise RuntimeError("KLIPR_DATABASE_URL not set")
    return psycopg2.connect(CONFIG.database_url)

class H(BaseHTTPRequestHandler):
    def _cors(self):
        o = _allowed_origin(self.headers.get("Origin"))
        if o: self.send_header("Access-Control-Allow-Origin", o)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self._cors(); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _auth(self):
        tok = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        return Auth(CONFIG.auth_token_file).check_token(tok)
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "env": CONFIG.env, "billing_enabled": CONFIG.billing_enabled, "phase": "0", "dww_mount": True})
        if not self._auth(): return self._send(401, {"error": "unauthorized"})
        try:
            conn = _conn()
            with conn.cursor() as cur:
                queue._set_admin(cur)
                if self.path.startswith("/templates"):
                    cur.execute("SELECT id, content_type, version, recipe FROM templates ORDER BY id LIMIT 50")
                    rows = [{"id": r[0], "content_type": r[1], "version": r[2], "recipe": r[3]} for r in cur.fetchall()]
                    return self._send(200, {"templates": rows})
                if self.path.startswith("/brands"):
                    cur.execute("SELECT id, name FROM brands ORDER BY created_at DESC LIMIT 50")
                    return self._send(200, {"brands": [{"id": str(r[0]), "name": r[1]} for r in cur.fetchall()]})
                if self.path.startswith("/jobs"):
                    cur.execute("SELECT id, kind, status, attempts, credit_cost, created_at FROM jobs ORDER BY created_at DESC LIMIT 50")
                    return self._send(200, {"jobs": [{"id": str(r[0]), "kind": r[1], "status": r[2], "attempts": r[3], "credit_cost": r[4], "created_at": str(r[5])} for r in cur.fetchall()]})
            return self._send(404, {"error": "not found"})
        except Exception as e: return self._send(500, {"error": str(e)})
    def do_POST(self):
        if not self._auth(): return self._send(401, {"error": "unauthorized"})
        if self.path != "/jobs": return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            conn = _conn()
            jid = queue.enqueue(conn, body["user_id"], body["kind"], body.get("payload", {}),
                                credit_cost=int(body.get("credit_cost", 0)),
                                brand_id=body.get("brand_id"), project_id=body.get("project_id"))
            return self._send(201, {"job_id": str(jid), "status": "queued"})
        except Exception as e: return self._send(400, {"error": str(e)})
    def log_message(self, *a): pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8890); ap.add_argument("--host", default="127.0.0.1"); a = ap.parse_args()
    print(f"Klipr API (Phase 0 test) on {a.host}:{a.port} env={CONFIG.env} billing={CONFIG.billing_enabled}")
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()
