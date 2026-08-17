#!/bin/bash
# Supervisor for overnight.sh.
#
# The overnight run died silently at 19:56 immediately after printing the
# Phase 2 header -- the process group was reaped and nothing noticed for six
# hours. Phases are resumable, so the correct response to "the driver is gone"
# is simply to start it again; the only thing that was ever missing is
# something to notice.
#
# Loops until overnight.sh reports ALL PHASES DONE. Cached cells are skipped on
# every restart, so a restart costs nothing but the cells that were in flight.
cd "$(dirname "$0")"

for round in $(seq 1 40); do
  echo ""
  echo "############ supervisor round $round  $(date -u +%H:%M:%S)"
  ./overnight.sh
  if grep -q "ALL PHASES DONE" overnight.log 2>/dev/null; then
    echo "############ finished at $(date -u +%H:%M:%S)"
    exit 0
  fi
  echo "############ driver exited without finishing; restarting in 60s"
  sleep 60
done
echo "############ supervisor gave up after 40 rounds"
