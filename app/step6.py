"""Step 6: upload / activate / render / external_posts / metrics / inquiries.

Design only in 1A-LITE spec, implemented here after Matt approved 1A-LITE
2026-11-04. Single-operator proof, multi-tenant architecture: every row
carries user_id + brand_id, RLS is enabled, and the API sets session
variables transaction-locally from the token, never from client input.

Session context: call set_user_context(cur, user_id, is_admin) as the
first statement in a transaction, then run all queries in that same
transaction, then commit. SET LOCAL is transaction-local, so it is
released on commit/rollback. Never use queue._set_admin for library
endpoints; that helper is for the trusted worker's queue operations only.
"""
import base64
import hashlib
import json
import os
import tempfile
import time
import uuid

ALLOWED_KINDS = ["photo", "video_clip", "audio", "finished_video", "reference_image", "reference_video"]
ALLOWED_CATEGORIES = [
    "source_photo", "source_video", "tattoo_documentation", "shop_atmosphere",
    "workstation_prep", "equipment_closeup", "gloved_hands", "needle_to_skin",
    "artist_working", "cleaning_wiping", "shop_interaction", "transition_broll",
    "character_reference", "environment_reference", "hook_clip", "transition_clip",
    "music", "voice", "sfx", "ambient", "finished_video",
]
ALLOWED_ORIGINS = ["authentic", "synthetic"]
ALLOWED_METHODS = ["original", "enhanced", "assembled"]
ALLOWED_PLATFORMS = ["instagram", "tiktok", "youtube", "facebook"]
ALLOWED_CHANNELS = ["dm", "comment", "form", "walk_in", "referral"]
BLUEPRINT_KEYS = ["hook_type", "first_frame", "shot_list", "length", "cta", "music", "recipe_name"]


def set_user_context(cur, user_id, is_admin=False):
    cur.execute("SELECT set_config('app.current_user_id', %s, true)", (str(user_id),))
    cur.execute("SELECT set_config('app.is_admin', %s, true)", ("true" if is_admin else "false",))


def _check_brand(cur, brand_id, user_id):
    cur.execute("SELECT id FROM brands WHERE id=%s AND user_id=%s", (brand_id, user_id))
    return cur.fetchone() is not None


def _check_asset_owner(cur, asset_id, user_id):
    cur.execute("SELECT id, brand_id, kind, category, source_origin, production_method, hash_sha256, status, storage_path FROM assets WHERE id=%s AND user_id=%s", (asset_id, user_id))
    return cur.fetchone()


def upload_asset(conn, storage, user_id, brand_id, kind, category, source_origin,
                 production_method, filename, content_b64, generator_provider=None,
                 generator_model=None, mime=None):
    """Store a file, hash it, create a quarantined asset. Returns asset dict.
    If an archived asset with the same user+brand+hash exists, reactivate
    that ID to quarantined instead of creating a duplicate row (import path)."""
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"invalid kind: {kind}")
    if category not in ALLOWED_CATEGORIES:
        raise ValueError(f"invalid category: {category}")
    if source_origin is not None and source_origin not in ALLOWED_ORIGINS:
        raise ValueError(f"invalid source_origin: {source_origin}")
    if production_method is not None and production_method not in ALLOWED_METHODS:
        raise ValueError(f"invalid production_method: {production_method}")
    if source_origin == "synthetic" and category in ("tattoo_documentation", "needle_to_skin"):
        raise ValueError("tattoo gate: synthetic assets can never be tattoo_documentation or needle_to_skin")
    if not filename or "/" in filename or "\\" in filename or filename in (".", ".."):
        raise ValueError("invalid filename")
    try:
        file_bytes = base64.b64decode(content_b64, validate=True)
    except Exception:
        raise ValueError("content_base64 is not valid base64")
    if not file_bytes:
        raise ValueError("empty file")
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    with conn.cursor() as cur:
        set_user_context(cur, user_id, False)
        if not _check_brand(cur, brand_id, user_id):
            raise ValueError("brand not found or not owned by this user")
        cur.execute("SELECT id, storage_path, status FROM assets WHERE user_id=%s AND brand_id=%s AND hash_sha256=%s AND status='archived'",
                    (user_id, brand_id, file_hash))
        archived = cur.fetchone()
        if archived:
            cur.execute("UPDATE assets SET status='quarantined' WHERE id=%s RETURNING id, status, storage_path, hash_sha256",
                        (archived[0],))
            row = cur.fetchone()
            conn.commit()
            return {"id": str(row[0]), "status": row[1], "storage_path": row[2], "hash_sha256": row[3], "reactivated": True}
        # Store the new file, then insert the asset row in the same transaction.
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, filename)
            with open(src, "wb") as f:
                f.write(file_bytes)
            rel_path = storage.put(str(user_id), str(brand_id), kind, filename, src)
        if not mime:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "mp4": "video/mp4", "mov": "video/quicktime", "mp3": "audio/mpeg", "wav": "audio/wav"}.get(ext, "application/octet-stream")
        cur.execute("""INSERT INTO assets (user_id, brand_id, type, storage_path, kind, category,
                       source_origin, production_method, hash_sha256, mime, status,
                       generator_provider, generator_model)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'quarantined',%s,%s)
                       RETURNING id, status, storage_path, hash_sha256""",
                    (user_id, brand_id, kind, rel_path, kind, category, source_origin,
                     production_method, file_hash, mime, generator_provider, generator_model))
        row = cur.fetchone()
    conn.commit()
    return {"id": str(row[0]), "status": row[1], "storage_path": row[2], "hash_sha256": row[3], "reactivated": False}


def activate_asset(conn, user_id, asset_id):
    with conn.cursor() as cur:
        set_user_context(cur, user_id, False)
        row = _check_asset_owner(cur, asset_id, user_id)
        if not row:
            raise ValueError("asset not found")
        _id, _brand, _kind, category, source_origin, _method, _hash, status, _path = row
        if status == "active":
            raise ValueError("asset already active")
        if source_origin == "synthetic" and category in ("tattoo_documentation", "needle_to_skin"):
            raise ValueError("tattoo gate: synthetic assets can never be tattoo_documentation or needle_to_skin")
        try:
            cur.execute("UPDATE assets SET status='active' WHERE id=%s RETURNING id, status", (asset_id,))
            out = cur.fetchone()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"activation failed (likely duplicate active hash): {e}")
    conn.commit()
    return {"id": str(out[0]), "status": out[1]}


def create_project(conn, user_id, brand_id, blueprint, asset_ids):
    if not isinstance(blueprint, dict):
        raise ValueError("blueprint must be an object")
    missing = [k for k in BLUEPRINT_KEYS if k not in blueprint]
    if missing:
        raise ValueError(f"blueprint missing keys: {', '.join(missing)}")
    if not isinstance(blueprint.get("shot_list"), list) or not blueprint["shot_list"]:
        raise ValueError("blueprint.shot_list must be a non-empty list")
    asset_ids = asset_ids or []
    with conn.cursor() as cur:
        set_user_context(cur, user_id, False)
        if not _check_brand(cur, brand_id, user_id):
            raise ValueError("brand not found or not owned by this user")
        for aid in asset_ids:
            if not _check_asset_owner(cur, aid, user_id):
                raise ValueError(f"planned asset not found or not owned: {aid}")
        cur.execute("""INSERT INTO projects (user_id, brand_id, input_assets, edl, blueprint)
                       VALUES (%s,%s,%s::uuid[],%s::jsonb,%s::jsonb) RETURNING id""",
                    (user_id, brand_id, asset_ids, json.dumps({}), json.dumps(blueprint)))
        pid = cur.fetchone()[0]
        for idx, aid in enumerate(asset_ids):
            slot = "shot"
            try:
                shot = blueprint["shot_list"][idx]
                if isinstance(shot, dict) and shot.get("role"):
                    slot = str(shot["role"])
            except Exception:
                pass
            cur.execute("""INSERT INTO project_assets (user_id, brand_id, project_id, asset_id, slot_role, sequence_index)
                           VALUES (%s,%s,%s,%s,%s,%s)""",
                        (user_id, brand_id, pid, aid, slot, idx))
    conn.commit()
    return {"project_id": str(pid)}


def _compute_composition(cur, render_id):
    cur.execute("""SELECT assets.source_origin, assets.production_method, count(*), count(DISTINCT asset_usage.asset_id),
                   coalesce(sum(asset_usage.duration), 0)
                   FROM asset_usage JOIN assets ON assets.id = asset_usage.asset_id
                   WHERE asset_usage.render_id=%s AND asset_usage.usage_state='rendered'
                   GROUP BY assets.source_origin, assets.production_method ORDER BY assets.source_origin, assets.production_method""",
                (render_id,))
    groups = []
    total_occ = 0
    total_dur = 0.0
    for origin, method, occ, distinct, dur in cur.fetchall():
        groups.append({"source_origin": origin, "production_method": method,
                       "occurrences": int(occ), "distinct_assets": int(distinct),
                       "total_duration_sec": float(dur)})
        total_occ += int(occ)
        total_dur += float(dur)
    return {"groups": groups, "total_occurrences": total_occ, "total_duration_sec": total_dur}


def render_project(conn, storage, video_adapter, user_id, project_id):
    user_id = str(user_id)
    project_id = str(project_id)
    """Render a project in ONE transaction. Returns render dict.
    Caller (worker) is responsible for job status; this function raises
    on any validation or render failure, and rolls back on failure."""
    start = time.time()
    with conn.cursor() as cur:
        set_user_context(cur, user_id, False)
        cur.execute("SELECT id, brand_id, blueprint FROM projects WHERE id=%s AND user_id=%s", (project_id, user_id))
        proj = cur.fetchone()
        if not proj:
            raise ValueError("project not found")
        _pid, brand_id, blueprint = proj
        brand_id = str(brand_id)
        cur.execute("SELECT id FROM renders WHERE project_id=%s AND file_path IS NOT NULL", (project_id,))
        if cur.fetchone():
            raise ValueError("blueprint frozen: project already has a completed render")
        cur.execute("""SELECT pa.asset_id, pa.sequence_index, pa.slot_role,
                       a.storage_path, a.kind, a.status
                       FROM project_assets pa JOIN assets a ON a.id = pa.asset_id
                       WHERE pa.project_id=%s AND pa.user_id=%s
                       ORDER BY pa.sequence_index""",
                    (project_id, user_id))
        planned = cur.fetchall()
        active = [(str(r[0]), int(r[1]), str(r[2]), r[3], r[4], r[5]) for r in planned if r[5] == "active"]
        if not (3 <= len(active) <= 6):
            raise ValueError(f"render needs 3-6 active assets, got {len(active)} active of {len(planned)} planned")
        for r in active:
            if r[4] != "photo":
                raise ValueError(f"photo_motion only handles photo assets, got kind={r[4]} for asset {r[0]}")
        shot_list = blueprint.get("shot_list", []) if isinstance(blueprint, dict) else []
        sources = []
        durations = []
        for idx, r in enumerate(active):
            sources.append(storage.get_path(r[3]))
            dur = 2.0
            try:
                shot = shot_list[idx]
                if isinstance(shot, dict) and shot.get("duration"):
                    dur = float(shot["duration"])
            except Exception:
                pass
            durations.append(dur)
    # Render outside the DB transaction (ffmpeg), then write all DB rows in one transaction.
    render_id = uuid.uuid4()
    render_id_str = str(render_id)
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, f"render-{render_id}.mp4")
        video_adapter.photo_motion_multi(sources, out_path, durations)
        with open(out_path, "rb") as f:
            rendered_bytes = f.read()
        rendered_hash = hashlib.sha256(rendered_bytes).hexdigest()
        rel_path = storage.put(str(user_id), str(brand_id), "finished_video", f"render-{render_id}.mp4", out_path)
    elapsed = int(time.time() - start)
    with conn.cursor() as cur:
        set_user_context(cur, user_id, False)
        cur.execute("""INSERT INTO assets (user_id, brand_id, type, storage_path, kind, category,
                       source_origin, production_method, hash_sha256, mime, status)
                       VALUES (%s,%s,'finished_video',%s,'finished_video','finished_video',NULL,'assembled',%s,'video/mp4','active')
                       RETURNING id""",
                    (user_id, brand_id, rel_path, rendered_hash))
        finished_asset_id = str(cur.fetchone()[0])
        cur.execute("""INSERT INTO renders (id, user_id, project_id, brand_id, asset_id,
                       origin_composition, aspect_ratio, file_path, time_to_render_sec)
                       VALUES (%s,%s,%s,%s,%s,%s::jsonb,'9:16',%s,%s) RETURNING id""",
                    (render_id_str, user_id, project_id, brand_id, finished_asset_id, json.dumps({}), rel_path, elapsed))
        for idx, r in enumerate(active):
            cur.execute("""INSERT INTO asset_usage (user_id, brand_id, project_id, render_id, asset_id,
                           usage_state, slot_role, sequence_index, occurrence_index, duration, rendered_at)
                           VALUES (%s,%s,%s,%s,%s,'rendered',%s,%s,1,%s,now())""",
                        (user_id, brand_id, project_id, render_id_str, r[0], r[2], r[1], durations[idx]))
        composition = _compute_composition(cur, render_id_str)
        cur.execute("UPDATE renders SET origin_composition=%s::jsonb WHERE id=%s", (json.dumps(composition), render_id_str))
    conn.commit()
    return {"render_id": str(render_id), "file_path": rel_path, "asset_id": str(finished_asset_id),
            "duration_sec": sum(durations), "origin_composition": composition, "assets_rendered": len(active)}


def record_external_post(conn, user_id, brand_id, render_id, platform, platform_post_id, cta_keyword, posted_by="manual"):
    if platform not in ALLOWED_PLATFORMS:
        raise ValueError(f"invalid platform: {platform}")
    if posted_by not in ("manual", "muse", "api"):
        raise ValueError(f"invalid posted_by: {posted_by}")
    if not cta_keyword:
        raise ValueError("cta_keyword is required")
    with conn.cursor() as cur:
        set_user_context(cur, user_id, False)
        if not _check_brand(cur, brand_id, user_id):
            raise ValueError("brand not found or not owned by this user")
        cur.execute("SELECT id FROM renders WHERE id=%s AND user_id=%s AND brand_id=%s", (render_id, user_id, brand_id))
        if not cur.fetchone():
            raise ValueError("render not found for this user/brand")
        try:
            cur.execute("""INSERT INTO external_posts (user_id, brand_id, render_id, platform, platform_post_id, cta_keyword, posted_by)
                           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (user_id, brand_id, render_id, platform, platform_post_id, cta_keyword, posted_by))
            out = cur.fetchone()
        except Exception as e:
            conn.rollback()
            raise ValueError(f"external_post failed (likely duplicate cta_keyword for this brand): {e}")
    conn.commit()
    return {"external_post_id": str(out[0])}


def record_metric_snapshot(conn, user_id, external_post_id, **fields):
    allowed = ["hours_since_post", "views", "reach", "avg_watch_time_sec", "completion_rate",
               "likes", "comments", "shares", "saves", "profile_visits", "follows"]
    cols = []
    vals = []
    for k in allowed:
        if k in fields and fields[k] is not None:
            cols.append(k)
            vals.append(fields[k])
    with conn.cursor() as cur:
        set_user_context(cur, user_id, False)
        cur.execute("SELECT id FROM external_posts WHERE id=%s AND user_id=%s", (external_post_id, user_id))
        if not cur.fetchone():
            raise ValueError("external_post not found")
        col_sql = ", ".join(cols)
        ph = ", ".join(["%s"] * len(cols))
        if cols:
            cur.execute(f"INSERT INTO metric_snapshots (external_post_id, {col_sql}) VALUES (%s, {ph}) RETURNING id",
                        [external_post_id] + vals)
        else:
            cur.execute("INSERT INTO metric_snapshots (external_post_id) VALUES (%s) RETURNING id", (external_post_id,))
        out = cur.fetchone()
    conn.commit()
    return {"metric_snapshot_id": str(out[0])}


def record_inquiry(conn, user_id, brand_id, channel, cta_keyword=None, external_post_id=None,
                   qualified=False, deposit_taken=False, notes=None):
    if channel not in ALLOWED_CHANNELS:
        raise ValueError(f"invalid channel: {channel}")
    with conn.cursor() as cur:
        set_user_context(cur, user_id, False)
        if not _check_brand(cur, brand_id, user_id):
            raise ValueError("brand not found or not owned by this user")
        if external_post_id:
            cur.execute("SELECT id FROM external_posts WHERE id=%s AND user_id=%s", (external_post_id, user_id))
            if not cur.fetchone():
                raise ValueError("external_post not found")
        cur.execute("""INSERT INTO inquiries (user_id, brand_id, channel, cta_keyword, external_post_id, qualified, deposit_taken, notes)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (user_id, brand_id, channel, cta_keyword, external_post_id, qualified, deposit_taken, notes))
        out = cur.fetchone()
    conn.commit()
    return {"inquiry_id": str(out[0])}


def weekly_report(conn, user_id, brand_id):
    """Per post, latest snapshot metrics + inquiries by CTA, vs brand median.
    Medians are computed across that brand's posts with a snapshot, using
    percentile_cont. Posts without a snapshot are listed with null metrics
    and do not affect the median."""
    with conn.cursor() as cur:
        set_user_context(cur, user_id, False)
        if not _check_brand(cur, brand_id, user_id):
            raise ValueError("brand not found or not owned by this user")
        cur.execute("""SELECT ep.id, ep.platform, ep.platform_post_id, ep.cta_keyword, ep.posted_at,
                       ms.views, ms.avg_watch_time_sec, ms.completion_rate, ms.saves, ms.shares,
                       (SELECT count(*) FROM inquiries i WHERE i.brand_id=ep.brand_id AND i.cta_keyword=ep.cta_keyword) AS inquiries
                       FROM external_posts ep
                       LEFT JOIN LATERAL (
                         SELECT * FROM metric_snapshots WHERE external_post_id=ep.id ORDER BY captured_at DESC LIMIT 1
                       ) ms ON true
                       WHERE ep.user_id=%s AND ep.brand_id=%s ORDER BY ep.posted_at DESC""",
                    (user_id, brand_id))
        posts = []
        for r in cur.fetchall():
            posts.append({"external_post_id": str(r[0]), "platform": r[1], "platform_post_id": r[2],
                          "cta_keyword": r[3], "posted_at": str(r[4]), "views": r[5],
                          "avg_watch_time_sec": float(r[6]) if r[6] is not None else None,
                          "completion_rate": float(r[7]) if r[7] is not None else None,
                          "saves": r[8], "shares": r[9], "inquiries": int(r[10])})
        cur.execute("""SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY ms.views),
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY ms.avg_watch_time_sec),
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY ms.completion_rate),
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY ms.saves),
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY ms.shares)
                       FROM external_posts ep JOIN metric_snapshots ms ON ms.external_post_id=ep.id
                       AND ms.captured_at = (SELECT max(captured_at) FROM metric_snapshots WHERE external_post_id=ep.id)
                       WHERE ep.user_id=%s AND ep.brand_id=%s""",
                    (user_id, brand_id))
        med = cur.fetchone()
        median = {"views": float(med[0]) if med[0] is not None else None,
                  "avg_watch_time_sec": float(med[1]) if med[1] is not None else None,
                  "completion_rate": float(med[2]) if med[2] is not None else None,
                  "saves": float(med[3]) if med[3] is not None else None,
                  "shares": float(med[4]) if med[4] is not None else None}
    return {"brand_id": str(brand_id), "posts": posts, "median": median}
