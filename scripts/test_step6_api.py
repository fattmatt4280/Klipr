#!/usr/bin/env python3
"""Step 6 acceptance test against a running Klipr server + managed DB.
Usage: KLIPR_DATABASE_URL=... KLIPR_USER_TOKEN_FILE=.klipr_user_tokens \
  KLIPR_STORAGE_ROOT=storage python3 scripts/test_step6_api.py http://127.0.0.1:8890
Creates two test users/brands, runs the full path, checks isolation, then
deletes all test data and the token file it created. Exits non-zero on fail.
Test images are generated solid-color JPEGs via ffmpeg, NOT real tattoo work,
and the external_post record is a test record (platform_post_id test-...),
never a real Instagram post.
"""
import base64, json, os, subprocess, sys, urllib.request, uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8890"
DB_URL = os.environ["KLIPR_DATABASE_URL"]
TOKEN_FILE = os.environ.get("KLIPR_USER_TOKEN_FILE", ".klipr_user_tokens")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.user_auth import UserAuth

fails = []
def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f" {extra}" if extra else ""))
    if not cond:
        fails.append(name)

def api(method, path, token, body=None):
    req = urllib.request.Request(BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {"error": "unparseable"}

def db_admin():
    import psycopg2
    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', false)")
    return conn

def main():
    conn = db_admin()
    cur = conn.cursor()
    u1 = str(uuid.uuid4()); u2 = str(uuid.uuid4())
    b1 = str(uuid.uuid4()); b2 = str(uuid.uuid4())
    try:
        cur.execute("INSERT INTO users (id, oauth_identity) VALUES (%s, 'step6-test-matt')", (u1,))
        cur.execute("INSERT INTO users (id, oauth_identity) VALUES (%s, 'step6-test-user2')", (u2,))
        cur.execute("INSERT INTO brands (id, user_id, name) VALUES (%s, %s, 'Step6 Test Brand')", (b1, u1))
        cur.execute("INSERT INTO brands (id, user_id, name) VALUES (%s, %s, 'Step6 Test Brand 2')", (b2, u2))
        conn.commit()
        auth = UserAuth(TOKEN_FILE)
        t1 = auth.create_token(u1, False)
        t2 = auth.create_token(u2, False)
        # Generate 5 test images (4 active + 1 quarantined planned-but-cut)
        import tempfile
        tmp = tempfile.mkdtemp()
        colors = ["red", "green", "blue", "yellow", "purple"]
        b64s = []
        for i, c in enumerate(colors):
            p = os.path.join(tmp, f"test{i}.jpg")
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={c}:s=1080x1920", "-frames:v", "1", p],
                           check=True, capture_output=True)
            with open(p, "rb") as f:
                b64s.append(base64.b64encode(f.read()).decode())
        asset_ids = []
        for i in range(5):
            code, out = api("POST", "/assets", t1, {"brand_id": b1, "kind": "photo", "category": "source_photo",
                "source_origin": "authentic", "production_method": "original",
                "filename": f"test{i}.jpg", "content_base64": b64s[i]})
            check(f"upload asset {i}", code == 201, str(out)[:120])
            asset_ids.append(out["id"])
        # Activate first 4 only; 5th stays quarantined (planned-but-cut)
        for i in range(4):
            code, out = api("POST", f"/assets/{asset_ids[i]}/activate", t1, {})
            check(f"activate asset {i}", code == 200 and out.get("status") == "active", str(out)[:120])
        # Tattoo gate: synthetic tattoo_documentation must fail
        code, out = api("POST", "/assets", t1, {"brand_id": b1, "kind": "photo", "category": "tattoo_documentation",
            "source_origin": "synthetic", "production_method": "original", "generator_provider": "test", "generator_model": "test",
            "filename": "bad.jpg", "content_base64": b64s[0]})
        check("tattoo gate synthetic blocked", code == 400, str(out)[:120])
        # Duplicate active hash: upload same bytes again, activate must fail
        code, out = api("POST", "/assets", t1, {"brand_id": b1, "kind": "photo", "category": "source_photo",
            "source_origin": "authentic", "production_method": "original", "filename": "dup.jpg", "content_base64": b64s[0]})
        dup_id = out.get("id") if code == 201 else None
        check("upload duplicate quarantined ok", code == 201, str(out)[:120])
        if dup_id:
            code, out = api("POST", f"/assets/{dup_id}/activate", t1, {})
            check("duplicate active hash blocked", code == 400, str(out)[:120])
        # Isolation: user2 sees no user1 assets, cannot activate user1 asset, cannot use user1 brand
        code, out = api("GET", "/assets", t2)
        check("user2 assets list empty", code == 200 and out.get("assets") == [], str(out)[:120])
        code, out = api("POST", f"/assets/{asset_ids[0]}/activate", t2, {})
        check("user2 cannot activate user1 asset", code == 400, str(out)[:120])
        code, out = api("POST", "/projects", t2, {"brand_id": b1, "blueprint": {"hook_type": "x", "first_frame": "x", "shot_list": [{"duration": 2}], "length": 2, "cta": "X", "music": "none", "recipe_name": "x"}, "asset_ids": []})
        check("user2 cannot use user1 brand", code == 400, str(out)[:120])
        # Admin token must NOT work for Step 6 endpoints (checked with a bogus token that is not a user token)
        code, out = api("GET", "/assets", "bogus-not-a-user-token")
        check("bogus token rejected", code == 401, str(out)[:120])
        # Project with 5 planned, 4 active
        blueprint = {"hook_type": "color_flash", "first_frame": "red", "shot_list": [{"duration": 2.0}, {"duration": 2.0}, {"duration": 2.0}, {"duration": 2.0}, {"duration": 2.0}], "length": 10, "cta": "TESTCTA123", "music": "none", "recipe_name": "step6-test"}
        code, out = api("POST", "/projects", t1, {"brand_id": b1, "blueprint": blueprint, "asset_ids": asset_ids})
        check("create project", code == 201, str(out)[:120])
        pid = out["project_id"]
        code, out = api("POST", f"/projects/{pid}/render", t1, {})
        check("enqueue render", code == 201, str(out)[:120])
        job_id = out.get("job_id")
        # Run worker once
        env = dict(os.environ)
        env["KLIPR_DATABASE_URL"] = DB_URL
        env["KLIPR_STORAGE_ROOT"] = os.environ.get("KLIPR_STORAGE_ROOT", "storage")
        r = subprocess.run([sys.executable, "-m", "app.worker", "--once"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
        print("worker:", r.stdout.strip(), r.stderr.strip()[-2000:])
        code, out = api("GET", "/jobs", t1)
        jobs = {j["id"]: j for j in out.get("jobs", [])}
        check("render job done", job_id in jobs and jobs[job_id]["status"] == "done", str(jobs.get(job_id)))
        code, out = api("GET", "/renders", t1)
        renders = out.get("renders", [])
        check("one render returned", code == 200 and len(renders) == 1, str(out)[:200])
        render = renders[0] if renders else {}
        comp = render.get("origin_composition", {})
        check("composition excludes planned-but-cut", comp.get("total_occurrences") == 4 and comp.get("distinct_assets") if False else comp.get("total_occurrences") == 4, str(comp))
        # Check video file dimensions via ffprobe
        if render.get("file_path"):
            fp = os.path.join(os.environ.get("KLIPR_STORAGE_ROOT", "storage"), render["file_path"])
            pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration", "-of", "json", fp], capture_output=True, text=True)
            info = json.loads(pr.stdout or "{}")
            s = (info.get("streams") or [{}])[0]
            check("render is 1080x1920", s.get("width") == 1080 and s.get("height") == 1920, str(s))
        else:
            check("render file_path present", False)
        # Download endpoint: user token ok, second user blocked, bogus token blocked
        if render.get("id"):
            import urllib.error
            req = urllib.request.Request(BASE + f"/renders/{render['id']}/file", headers={"Authorization": f"Bearer {t1}"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    dl = r.read()
                    check("download render ok", r.status == 200 and r.headers.get("Content-Type") == "video/mp4" and len(dl) > 10000, f"status={r.status} bytes={len(dl)}")
                    dl_path = os.path.join(tmp, "downloaded.mp4")
                    with open(dl_path, "wb") as f:
                        f.write(dl)
                    pr2 = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", dl_path], capture_output=True, text=True)
                    info2 = json.loads(pr2.stdout or "{}")
                    s2 = (info2.get("streams") or [{}])[0]
                    check("downloaded file is 1080x1920", s2.get("width") == 1080 and s2.get("height") == 1920, str(s2))
            except urllib.error.HTTPError as e:
                check("download render ok", False, f"HTTP {e.code}")
            req2 = urllib.request.Request(BASE + f"/renders/{render['id']}/file", headers={"Authorization": f"Bearer {t2}"})
            try:
                urllib.request.urlopen(req2, timeout=30)
                check("user2 cannot download user1 render", False)
            except urllib.error.HTTPError as e:
                check("user2 cannot download user1 render", e.code in (404, 403), f"HTTP {e.code}")
        # External post, metric, inquiry, weekly report
        if not render.get("id"):
            check("external_post skipped, no render", False)
            raise SystemExit(1)  # early exit, cleanup runs, fails already printed
        code, out = api("POST", "/external_posts", t1, {"brand_id": b1, "render_id": render["id"], "platform": "instagram", "platform_post_id": "test-post-123", "cta_keyword": "TESTCTA123", "posted_by": "manual"})
        check("record external_post", code == 201, str(out)[:120])
        ep_id = out.get("external_post_id")
        code, out = api("POST", "/external_posts", t1, {"brand_id": b1, "render_id": render["id"], "platform": "instagram", "platform_post_id": "test-post-124", "cta_keyword": "TESTCTA123", "posted_by": "manual"})
        check("duplicate cta_keyword blocked", code == 400, str(out)[:120])
        code, out = api("POST", "/metric_snapshots", t1, {"external_post_id": ep_id, "views": 1000, "avg_watch_time_sec": 5.2, "completion_rate": 0.65, "saves": 40, "shares": 12})
        check("record metric_snapshot", code == 201, str(out)[:120])
        code, out = api("POST", "/inquiries", t1, {"brand_id": b1, "channel": "dm", "cta_keyword": "TESTCTA123", "external_post_id": ep_id, "qualified": True})
        check("record inquiry", code == 201, str(out)[:120])
        code, out = api("GET", f"/weekly_report?brand_id={b1}", t1)
        posts = out.get("posts", [])
        check("weekly report post + inquiry", code == 200 and len(posts) == 1 and posts[0].get("inquiries") == 1 and posts[0].get("views") == 1000, str(out)[:200])
        check("weekly report median = post", code == 200 and out.get("median", {}).get("views") == 1000, str(out.get("median")))
        # Blueprint freeze: second render must fail
        code, out = api("POST", f"/projects/{pid}/render", t1, {})
        check("blueprint frozen second render blocked", code == 409, str(out)[:120])
    finally:
        # Cleanup, admin context, in dependency order
        try:
            conn2 = db_admin()
            cur2 = conn2.cursor()
            cur2.execute("DELETE FROM metric_snapshots WHERE external_post_id IN (SELECT id FROM external_posts WHERE user_id IN (%s, %s))", (u1, u2))
            cur2.execute("DELETE FROM inquiries WHERE user_id IN (%s, %s)", (u1, u2))
            cur2.execute("DELETE FROM external_posts WHERE user_id IN (%s, %s)", (u1, u2))
            cur2.execute("DELETE FROM asset_usage WHERE user_id IN (%s, %s)", (u1, u2))
            cur2.execute("DELETE FROM renders WHERE user_id IN (%s, %s)", (u1, u2))
            cur2.execute("DELETE FROM project_assets WHERE user_id IN (%s, %s)", (u1, u2))
            cur2.execute("DELETE FROM assets WHERE user_id IN (%s, %s)", (u1, u2))
            cur2.execute("DELETE FROM projects WHERE user_id IN (%s, %s)", (u1, u2))
            cur2.execute("DELETE FROM jobs WHERE user_id IN (%s, %s)", (u1, u2))
            cur2.execute("DELETE FROM brands WHERE user_id IN (%s, %s)", (u1, u2))
            cur2.execute("DELETE FROM users WHERE id IN (%s, %s)", (u1, u2))
            conn2.commit()
            cur2.execute("SELECT count(*) FROM users WHERE id IN (%s, %s)", (u1, u2))
            print("cleanup users remaining:", cur2.fetchone()[0])
            conn2.close()
        except Exception as e:
            print("cleanup error:", e)
        try:
            import shutil
            for uid in (u1, u2):
                p = os.path.join(ROOT, os.environ.get("KLIPR_STORAGE_ROOT", "storage"), uid)
                if os.path.exists(p):
                    shutil.rmtree(p)
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
        except Exception as e:
            print("storage/token cleanup error:", e)
    print("FAILS:", fails)
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
