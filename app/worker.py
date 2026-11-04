"""Phase 0 worker: claims jobs, runs the proof handler, meters credits.
Proof handler for kind='analyze': runs VisionAdapter.analyze (no spend, no model).
Real pipeline handlers are Phase 1. Credit ledger entry is written ONLY when
a job completes with credit_cost > 0 and billing is on OR admin testing is off
— in Phase 0 billing is off, so entries are recorded as metered=0 with the
estimated cost in the CRM log, so real pricing data is collected without blocking.
Usage: KLIPR_DATABASE_URL=... python3 -m app.worker --once
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import CONFIG
from app.adapters import OpenRouterAdapter, VisionAdapter
from app.crm import log_event
import app.queue as queue

def get_conn():
    import psycopg2
    return psycopg2.connect(CONFIG.database_url)

def run_once():
    conn = get_conn()
    row = queue.claim_next(conn)
    if not row: print("no queued jobs"); return False
    jid, kind, payload, attempts, max_attempts, credit_cost, user_id, brand_id, project_id = row
    try:
        if kind == "analyze":
            out = VisionAdapter(OpenRouterAdapter(CONFIG, CONFIG.crm_log_path)).analyze(payload, user_id=user_id, job_id=jid)
            log_event(CONFIG.crm_log_path, "job_done", user_id=str(user_id), job_id=str(jid), kind=kind, output=out)
        elif kind in ("render", "render_photo_motion"):
            from app.adapters import VideoAdapter
            from app.storage import get_storage
            from app import step6 as s6
            pid = payload.get("project_id") or project_id
            if not pid:
                raise RuntimeError("render job missing project_id")
            out = s6.render_project(conn, get_storage(CONFIG), VideoAdapter(OpenRouterAdapter(CONFIG, CONFIG.crm_log_path)), user_id, pid)
            log_event(CONFIG.crm_log_path, "job_done", user_id=str(user_id), job_id=str(jid), kind=kind, output=out)
        else:
            raise RuntimeError(f"unknown job kind: {kind}")
        queue.finish(conn, jid, True); print(f"done {jid} {kind}"); return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except Exception:
            pass
        queue.finish(conn, jid, False, error=str(e)); print(f"failed {jid}: {e}"); return False

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--once", action="store_true"); ap.parse_args()
    run_once()
