#!/bin/bash
# Liveness watchdog for the overnight run.
#
# TWO FAILURE MODES, AND supervise.sh ONLY HANDLES ONE
#
#   (a) the driver EXITS  -- supervise.sh notices and restarts it.
#   (b) the driver HANGS  -- supervise.sh is blocked in `./overnight.sh` and
#       will wait forever. This is what actually happened twice: the log's last
#       write was 19:56 and 02:00, and nothing noticed for hours.
#
# So liveness cannot be judged by "is the process alive". It has to be judged
# by "is the process still producing cells". This watchdog reads the log's
# mtime: if nothing has been written for STALE_MIN minutes, the run is wedged
# regardless of what `ps` says, and it gets killed and restarted.
#
# Restarting is cheap and safe: cached cells are skipped, and failed cells are
# never cached, so the only cost is the one or two calls in flight.
cd "$(dirname "$0")"

LOG=overnight.log
STALE_MIN=12          # a legitimate cell takes ~90s; 12 min is far beyond it
CHECK_SEC=120

start_run () {
  echo "$(date -u +%H:%M:%S) [watchdog] starting supervisor"
  setsid ./supervise.sh >> "$LOG" 2>&1 &
  sleep 20
}

while true; do
  if grep -q "ALL PHASES DONE" "$LOG" 2>/dev/null; then
    echo "$(date -u +%H:%M:%S) [watchdog] all phases done; exiting"
    exit 0
  fi

  now=$(date +%s)
  mt=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
  age=$(( (now - mt) / 60 ))
  alive=$(pgrep -fc "runner.py --provider featherless" || true)

  if [ "$age" -ge "$STALE_MIN" ]; then
    echo "$(date -u +%H:%M:%S) [watchdog] log stale ${age}m (procs=$alive) -- restarting"
    pkill -9 -f "supervise.sh"        >/dev/null 2>&1
    pkill -9 -f "overnight.sh"        >/dev/null 2>&1
    pkill -9 -f "runner.py --provider" >/dev/null 2>&1
    sleep 5
    # Featherless keeps generating server-side after curl is killed, so the
    # account stays at its concurrency limit for a while. Give it a moment
    # rather than restarting straight into a wall of concurrency errors.
    sleep 60
    start_run
  elif [ "$alive" -eq 0 ]; then
    echo "$(date -u +%H:%M:%S) [watchdog] no runner process -- restarting"
    start_run
  fi

  sleep "$CHECK_SEC"
done
