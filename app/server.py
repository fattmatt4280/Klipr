"""Klipr API server, Phase 0 + Step 6.
Stdlib only + psycopg2.
Endpoints: GET /health (public).
Legacy Phase 0 (admin token or user token): GET /templates, GET /brands, GET /jobs, POST /jobs.
Step 6 (user token ONLY, never the admin token, never client-supplied user_id):
  POST /assets, POST /assets/<id>/activate, GET /assets,
  POST /projects, GET /projects, POST /projects/<id>/render, GET /renders,
  GET /renders/<id>/file (download the finished MP4, user token only),
  POST /external_posts, GET /external_posts,
  POST /metric_snapshots, POST /inquiries, GET /weekly_report?brand_id=<uuid>
Protected endpoints require: Authorization: Bearer <token>
  User tokens are resolved via app/user_auth.py (hash file, mode 600).
  The legacy admin token still works for legacy routes (audit / system),
  but Step 6 routes reject it: library operations must run as a real user,
  with Postgres session variables set transaction-locally from the token.
CORS: only dreamwebworkz.com, *.lovable.app, *.lovableproject.com, and localhost (VM proof).
Worker must run separately on the same server (app/worker.py) — this server
enqueues jobs, it does not execute them inline.
Usage: KLIPR_DATABASE_URL=... KLIPR_USER_TOKEN_FILE=... python3 -m app.server --port 8890
"""
import argparse, json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import CONFIG
from app.auth import Auth
from app.user_auth import UserAuth
from app.storage import get_storage
import app.queue as queue
import app.step6 as s6

ALLOWED_SUFFIXES = (".dreamwebworkz.com", "dreamwebworkz.com", ".lovable.app", ".lovableproject.com", "localhost", "127.0.0.1")

def _allowed_origin(origin):
    if not origin: return None
    try:
        host = urlparse(origin).hostname or ""
    except Exception: return None
    if host == "dreamwebworkz.com" or host.endswith(".lovable.app") or host.endswith(".lovableproject.com") or host in ("localhost", "127.0.0.1"):
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
        b = json.dumps(obj, default=str).encode()
        self.send_response(code); self._cors(); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _token(self):
        return (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
    def _auth_user(self):
        """Return (user_id, is_admin) for a user token, or None."""
        return UserAuth(CONFIG.user_token_file).resolve(self._token())
    def _auth_admin(self):
        return Auth(CONFIG.auth_token_file).check_token(self._token())
    def _auth_any(self):
        u = self._auth_user()
        if u: return u
        if self._auth_admin(): return (None, True)
        return None
    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")
    def _send_file(self, file_path, filename):
        with open(file_path, "rb") as f:
            data = f.read()
        self.send_response(200); self._cors(); self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def _send_inline_file(self, file_path, mime):
        with open(file_path, "rb") as f:
            data = f.read()
        self.send_response(200); self._cors(); self.send_header("Content-Type", mime)
        self.send_header("Content-Disposition", "inline")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        if path == "/health":
            return self._send(200, {"status": "ok", "env": CONFIG.env, "billing_enabled": CONFIG.billing_enabled, "phase": "6", "dww_mount": True})
        # Step 6 render download: user token only, render must belong to the token user.
        if path.startswith("/renders/") and path.endswith("/file"):
            auth = self._auth_user()
            if not auth: return self._send(401, {"error": "unauthorized: user token required"})
            user_id, is_admin = auth
            if is_admin: return self._send(403, {"error": "admin token cannot download another user's private renders via Step 6 endpoints"})
            render_id = path.split("/")[2]
            try:
                conn = _conn()
                with conn.cursor() as cur:
                    s6.set_user_context(cur, user_id, False)
                    cur.execute("SELECT file_path FROM renders WHERE id=%s AND user_id=%s", (render_id, user_id))
                    row = cur.fetchone()
                    if not row or not row[0]: return self._send(404, {"error": "render not found"})
                    full = get_storage(CONFIG).get_path(row[0])
                import os as _os
                if not _os.path.exists(full): return self._send(404, {"error": "render file not found on backend storage"})
                return self._send_file(full, f"render-{render_id}.mp4")
            except Exception as e:
                return self._send(500, {"error": str(e)})
        # Step 6 asset file: user token only, asset must belong to the token user.
        # Serves the original photo/video inline so the app can show thumbnails
        # and previews. Archived (deleted) assets are not served.
        if path.startswith("/assets/") and path.endswith("/file"):
            auth = self._auth_user()
            if not auth: return self._send(401, {"error": "unauthorized: user token required"})
            user_id, is_admin = auth
            if is_admin: return self._send(403, {"error": "admin token cannot download another user's private assets via Step 6 endpoints"})
            asset_id = path.split("/")[2]
            try:
                conn = _conn()
                with conn.cursor() as cur:
                    s6.set_user_context(cur, user_id, False)
                    cur.execute("SELECT storage_path, mime FROM assets WHERE id=%s AND user_id=%s AND status != 'archived'", (asset_id, user_id))
                    row = cur.fetchone()
                    if not row: return self._send(404, {"error": "asset not found"})
                    storage_path, mime = row
                    full = get_storage(CONFIG).get_path(storage_path)
                import os as _os
                if not _os.path.exists(full): return self._send(404, {"error": "asset file not found on backend storage"})
                if not mime:
                    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "mp4": "video/mp4", "mov": "video/quicktime"}.get(full.rsplit(".", 1)[-1].lower() if "." in full else "", "application/octet-stream")
                return self._send_inline_file(full, mime)
            except Exception as e:
                return self._send(500, {"error": str(e)})
        # Step 6 reads: user token only
        if path in ("/assets", "/projects", "/renders", "/external_posts", "/weekly_report"):
            auth = self._auth_user()
            if not auth: return self._send(401, {"error": "unauthorized: user token required"})
            user_id, is_admin = auth
            try:
                conn = _conn()
                with conn.cursor() as cur:
                    s6.set_user_context(cur, user_id, is_admin)
                    if path == "/assets":
                        cur.execute("SELECT id, brand_id, kind, category, source_origin, production_method, hash_sha256, status, storage_path FROM assets WHERE user_id=%s AND status != 'archived' ORDER BY created_at DESC LIMIT 100", (user_id,))
                        rows = [{"id": str(r[0]), "brand_id": str(r[1]), "kind": r[2], "category": r[3], "source_origin": r[4], "production_method": r[5], "hash_sha256": r[6], "status": r[7], "storage_path": r[8]} for r in cur.fetchall()]
                        return self._send(200, {"assets": rows})
                    if path == "/projects":
                        cur.execute("SELECT id, brand_id, blueprint FROM projects WHERE user_id=%s ORDER BY created_at DESC LIMIT 50", (user_id,))
                        return self._send(200, {"projects": [{"id": str(r[0]), "brand_id": str(r[1]), "blueprint": r[2]} for r in cur.fetchall()]})
                    if path == "/renders":
                        cur.execute("SELECT id, project_id, brand_id, asset_id, origin_composition, file_path FROM renders WHERE user_id=%s ORDER BY created_at DESC LIMIT 50", (user_id,))
                        return self._send(200, {"renders": [{"id": str(r[0]), "project_id": str(r[1]), "brand_id": str(r[2]), "asset_id": str(r[3]), "origin_composition": r[4], "file_path": r[5]} for r in cur.fetchall()]})
                    if path == "/external_posts":
                        cur.execute("SELECT id, brand_id, render_id, platform, platform_post_id, cta_keyword, posted_at, posted_by FROM external_posts WHERE user_id=%s ORDER BY posted_at DESC LIMIT 50", (user_id,))
                        return self._send(200, {"external_posts": [{"id": str(r[0]), "brand_id": str(r[1]), "render_id": str(r[2]), "platform": r[3], "platform_post_id": r[4], "cta_keyword": r[5], "posted_at": str(r[6]), "posted_by": r[7]} for r in cur.fetchall()]})
                    if path == "/weekly_report":
                        brand_id = (qs.get("brand_id") or [None])[0]
                        if not brand_id: return self._send(400, {"error": "brand_id query param required"})
                        return self._send(200, s6.weekly_report(conn, user_id, brand_id))
            except Exception as e:
                return self._send(500, {"error": str(e)})
        # Legacy reads: user token (own rows) or admin token (all rows)
        auth = self._auth_any()
        if not auth: return self._send(401, {"error": "unauthorized"})
        user_id, is_admin = auth
        try:
            conn = _conn()
            with conn.cursor() as cur:
                if is_admin and user_id is None:
                    queue._set_admin(cur)
                else:
                    s6.set_user_context(cur, user_id, is_admin)
                if path.startswith("/templates"):
                    if user_id:
                        cur.execute("SELECT id, content_type, version, recipe FROM templates WHERE user_id=%s ORDER BY id LIMIT 50", (user_id,))
                    else:
                        cur.execute("SELECT id, content_type, version, recipe FROM templates ORDER BY id LIMIT 50")
                    rows = [{"id": r[0], "content_type": r[1], "version": r[2], "recipe": r[3]} for r in cur.fetchall()]
                    return self._send(200, {"templates": rows})
                if path.startswith("/brands"):
                    if user_id:
                        cur.execute("SELECT id, name FROM brands WHERE user_id=%s ORDER BY created_at DESC LIMIT 50", (user_id,))
                    else:
                        cur.execute("SELECT id, name FROM brands ORDER BY created_at DESC LIMIT 50")
                    return self._send(200, {"brands": [{"id": str(r[0]), "name": r[1]} for r in cur.fetchall()]})
                if path.startswith("/jobs"):
                    if user_id:
                        cur.execute("SELECT id, kind, status, attempts, credit_cost, created_at, error FROM jobs WHERE user_id=%s ORDER BY created_at DESC LIMIT 50", (user_id,))
                    else:
                        cur.execute("SELECT id, kind, status, attempts, credit_cost, created_at, error FROM jobs ORDER BY created_at DESC LIMIT 50")
                    return self._send(200, {"jobs": [{"id": str(r[0]), "kind": r[1], "status": r[2], "attempts": r[3], "credit_cost": r[4], "created_at": str(r[5]), "error": r[6]} for r in cur.fetchall()]})
            return self._send(404, {"error": "not found"})
        except Exception as e: return self._send(500, {"error": str(e)})
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        # Step 6 writes: user token only
        if path in ("/assets", "/projects", "/external_posts", "/metric_snapshots", "/inquiries") or path.startswith("/assets/") and path.endswith("/activate") or path.startswith("/assets/") and path.endswith("/archive") or path.startswith("/projects/") and path.endswith("/render"):
            auth = self._auth_user()
            if not auth: return self._send(401, {"error": "unauthorized: user token required"})
            user_id, is_admin = auth
            if is_admin:
                return self._send(403, {"error": "admin token cannot write another user's private assets via Step 6 endpoints"})
            try:
                body = self._body() if path not in ("/assets/",) else {}
                conn = _conn()
                if path == "/assets":
                    out = s6.upload_asset(conn, get_storage(CONFIG), user_id, body["brand_id"], body["kind"], body["category"],
                                          body.get("source_origin"), body.get("production_method"), body["filename"],
                                          body["content_base64"], body.get("generator_provider"), body.get("generator_model"), body.get("mime"))
                    return self._send(201, out)
                if path.startswith("/assets/") and path.endswith("/activate"):
                    asset_id = path.split("/")[2]
                    out = s6.activate_asset(conn, user_id, asset_id)
                    return self._send(200, out)
                if path.startswith("/assets/") and path.endswith("/archive"):
                    asset_id = path.split("/")[2]
                    out = s6.archive_asset(conn, user_id, asset_id)
                    return self._send(200, out)
                if path == "/projects":
                    out = s6.create_project(conn, user_id, body["brand_id"], body["blueprint"], body.get("asset_ids", []))
                    return self._send(201, out)
                if path.startswith("/projects/") and path.endswith("/render"):
                    project_id = path.split("/")[2]
                    # Validate ownership + blueprint freeze before enqueueing, as the user.
                    with conn.cursor() as cur:
                        s6.set_user_context(cur, user_id, False)
                        cur.execute("SELECT brand_id FROM projects WHERE id=%s AND user_id=%s", (project_id, user_id))
                        row = cur.fetchone()
                        if not row: return self._send(404, {"error": "project not found"})
                        cur.execute("SELECT id FROM renders WHERE project_id=%s AND file_path IS NOT NULL", (project_id,))
                        if cur.fetchone(): return self._send(409, {"error": "blueprint frozen: project already has a completed render"})
                    conn.rollback()
                    jid = queue.enqueue(conn, user_id, "render_photo_motion", {"project_id": project_id},
                                        brand_id=str(row[0]), project_id=project_id, is_admin=False)
                    return self._send(201, {"job_id": str(jid), "status": "queued", "project_id": project_id})
                if path == "/external_posts":
                    out = s6.record_external_post(conn, user_id, body["brand_id"], body["render_id"], body["platform"],
                                                  body["platform_post_id"], body["cta_keyword"], body.get("posted_by", "manual"))
                    return self._send(201, out)
                if path == "/metric_snapshots":
                    out = s6.record_metric_snapshot(conn, user_id, body["external_post_id"], **{k: v for k, v in body.items() if k != "external_post_id"})
                    return self._send(201, out)
                if path == "/inquiries":
                    out = s6.record_inquiry(conn, user_id, body["brand_id"], body["channel"], body.get("cta_keyword"),
                                            body.get("external_post_id"), body.get("qualified", False), body.get("deposit_taken", False), body.get("notes"))
                    return self._send(201, out)
            except Exception as e:
                return self._send(400, {"error": str(e)})
            return self._send(404, {"error": "not found"})
        # Legacy POST /jobs
        auth = self._auth_any()
        if not auth: return self._send(401, {"error": "unauthorized"})
        if path != "/jobs": return self._send(404, {"error": "not found"})
        try:
            body = self._body()
            conn = _conn()
            uid, is_admin = auth
            # Legacy jobs: if a user token is used, the job user_id must match the token.
            job_user = body["user_id"]
            if uid and str(job_user) != str(uid):
                return self._send(403, {"error": "job user_id must match token user_id"})
            jid = queue.enqueue(conn, job_user, body["kind"], body.get("payload", {}),
                                credit_cost=int(body.get("credit_cost", 0)),
                                brand_id=body.get("brand_id"), project_id=body.get("project_id"), is_admin=is_admin)
            return self._send(201, {"job_id": str(jid), "status": "queued"})
        except Exception as e: return self._send(400, {"error": str(e)})
    def log_message(self, *a): pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8890); ap.add_argument("--host", default="127.0.0.1"); a = ap.parse_args()
    print(f"Klipr API (Step 6) on {a.host}:{a.port} env={CONFIG.env} billing={CONFIG.billing_enabled}")
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()
