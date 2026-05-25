#!/usr/bin/env bash
# Durable launcher for the scope-C drip-feed enrichment.
#
# Run this from your OWN terminal (NOT inside an automated/agent session) so the
# process survives that session closing:
#
#     cd /Volumes/extraSupply/Projects/psdl-inspector/backend
#     nohup bash scripts/run_drip.sh >> data/vocabulary/batch/run_drip.boot 2>&1 &
#     disown
#
# Then close the terminal whenever — it keeps running. Check progress with:
#     tail -f data/vocabulary/batch/drip.log
#
# Safe to run more than once: the orchestrator holds a single-instance flock, so
# a second launch exits immediately without doing work (no double-submit/spend).
# Resumable: if the orchestrator dies unexpectedly, this supervisor restarts it
# and it picks up from the manifest. It stops on clean completion or a fail-stop.

set -u
cd "$(dirname "$0")/.." || exit 99          # -> backend/
BACKEND="$(pwd)"
BATCHDIR="$BACKEND/data/vocabulary/batch"
SUPLOG="$BATCHDIR/drip_supervisor.log"
mkdir -p "$BATCHDIR"

# shellcheck disable=SC1091
source .venv/bin/activate

# Refuse to start a second supervisor if the orchestrator is already locked/running.
if [ -f "$BATCHDIR/drip.lock" ] && pgrep -f "scripts/drip_feed_enrich.py" >/dev/null 2>&1; then
  echo "$(date -u +%FT%TZ) run_drip: orchestrator already running — not starting another" | tee -a "$SUPLOG"
  exit 0
fi

echo "$(date -u +%FT%TZ) run_drip: supervisor up (pid $$)" >> "$SUPLOG"
while true; do
  echo "$(date -u +%FT%TZ) run_drip: starting orchestrator" >> "$SUPLOG"
  python scripts/drip_feed_enrich.py >> "$BATCHDIR/drip_bootstrap.log" 2>&1
  ec=$?
  echo "$(date -u +%FT%TZ) run_drip: orchestrator exited ec=$ec" >> "$SUPLOG"
  case "$ec" in
    0) echo "$(date -u +%FT%TZ) run_drip: DONE (all waves complete or another instance owns the lock) — stopping" >> "$SUPLOG"; break ;;
    3) echo "$(date -u +%FT%TZ) run_drip: FAIL-STOP (a wave failed) — NOT restarting; needs a human look" >> "$SUPLOG"; break ;;
    *) echo "$(date -u +%FT%TZ) run_drip: unexpected ec=$ec — resuming in 30s" >> "$SUPLOG"; sleep 30 ;;
  esac
done
