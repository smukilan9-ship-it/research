#!/bin/bash
cd "$(dirname "$0")"
echo "time      $(date -u +%H:%M:%S)"
echo "log age   $(( ( $(date +%s) - $(stat -c %Y overnight.log 2>/dev/null || echo 0) ) / 60 )) min"
echo "runner    $(pgrep -fc '[r]unner[.]py --provider' || echo 0) proc(s)"
echo "watchdog  $(pgrep -fc '[w]atchdog[.]sh' || echo 0) proc(s)"
echo "phase     $(grep -o 'PHASE [0-9]' overnight.log | tail -1)"
echo "last cell $(grep '^  \[' overnight.log | tail -1 | sed 's/  */ /g')"
python3 - <<'PY'
import json,glob,collections
c=collections.Counter()
for f in glob.glob('responses/*.json'):
    r=json.load(open(f))
    if '::high' in r['model']: c[r['model'].split('/')[-1]]+=1
print("landed   ", dict(c), "total", sum(c.values()))
PY
