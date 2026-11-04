"""CRM logging, Phase 0. Append-only JSONL, one event per line.
Spec: every signup, project, render, AI call and credit spend feeds the CRM.
This is the local proof log; the production CRM integration (FridgeSpy-style setup)
is a VPS wiring step, not invented here. No secrets are ever written to this log.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

def log_event(path, event_type, user_id=None, **fields):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "type": event_type, "user_id": user_id, **fields}
    with p.open("a") as f: f.write(json.dumps(rec) + "\n")
    return rec
