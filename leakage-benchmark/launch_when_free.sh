#!/bin/bash
# Killing curl does not cancel the request on Featherless' side: the model keeps
# generating until it finishes, and the account stays at its concurrency limit
# for as long as that takes.  So a relaunch has to WAIT for the orphaned
# requests from the previous attempt to drain, rather than starting into a wall
# of concurrency errors and burning the phase.
cd "$(dirname "$0")"
source ./feather.env
KEY=$(grep -m1 -o "rc_[a-f0-9]*" feather.env)
for i in $(seq 1 90); do
  BODY='{"model":"zai-org/GLM-5.2","max_tokens":8,"messages":[{"role":"user","content":"hi"}]}'
  OUT=$(curl -sS --max-time 60 -H "Authorization: Bearer $KEY" \
        -H "content-type: application/json" -d "$BODY" \
        https://api.featherless.ai/v1/chat/completions)
  if ! echo "$OUT" | grep -q concurrency_limit_exceeded; then
    echo "$(date -u +%H:%M:%S) capacity free after $i probe(s); starting overnight run"
    exec ./overnight.sh
  fi
  echo "$(date -u +%H:%M:%S) probe $i: still at limit, waiting 60s"
  sleep 60
done
echo "gave up waiting for capacity after 90 minutes"
