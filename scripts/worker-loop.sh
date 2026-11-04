#!/bin/bash
# Worker loop used by klipr-worker.service. Runs --once every 10s, forever.
cd "$(dirname "$0")/.."
while true; do
  .venv/bin/python -m app.worker --once || true
  sleep 10
done
