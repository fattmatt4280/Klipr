"""Job queue, Phase 0.
Spec wants Redis-backed queue. VM proof uses the Postgres jobs table (same
fields: status, retry policy, credit cost) so the queue shape, retry logic and
metering can be tested without Redis. VPS step: swap this store for Redis
without changing job kinds/payloads. A job kind is never executed inline in
request code — it is always enqueued, then the worker picks it up.
"""
import json

def _set_admin(cur):
    # Worker is a trusted server process: it acts as admin for queue operations.
    # Untrusted app clients must NOT do this — they set app.current_user_id to
    # their own id and app.is_admin='false', and RLS then limits them to own rows.
    cur.execute("SELECT set_config('app.is_admin', 'true', false)")

def enqueue(conn, user_id, kind, payload, credit_cost=0, brand_id=None, project_id=None):
    with conn.cursor() as cur:
        _set_admin(cur)
        cur.execute("""INSERT INTO jobs (user_id, brand_id, project_id, kind, payload, credit_cost)
                       VALUES (%s,%s,%s,%s,%s::jsonb,%s) RETURNING id""",
                    (user_id, brand_id, project_id, kind, json.dumps(payload), credit_cost))
        jid = cur.fetchone()[0]
    conn.commit(); return jid

def claim_next(conn):
    """Claim one queued job, honouring max_attempts. Returns row or None."""
    with conn.cursor() as cur:
        _set_admin(cur)
        cur.execute("""UPDATE jobs SET status='running', attempts=attempts+1, updated_at=now()
                       WHERE id=(SELECT id FROM jobs WHERE status='queued' AND attempts < max_attempts
                                 ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED)
                       RETURNING id, kind, payload, attempts, max_attempts, credit_cost, user_id""")
        row = cur.fetchone()
    conn.commit(); return row

def finish(conn, job_id, ok, error=None):
    with conn.cursor() as cur:
        _set_admin(cur)
        if ok:
            cur.execute("UPDATE jobs SET status='done', updated_at=now() WHERE id=%s", (job_id,))
        else:
            cur.execute("""UPDATE jobs SET status=CASE WHEN attempts >= max_attempts THEN 'failed' ELSE 'queued' END,
                           error=%s, updated_at=now() WHERE id=%s""", (error, job_id))
    conn.commit()
