#!/bin/bash
# Overnight run.
#
# Phases are sequential and every one of them is RESUMABLE: cached cells are
# skipped on a re-run, and failed cells are never cached (a quota error written
# to cache becomes a permanent zero-coverage "answer" the model never gave --
# that bug cost 91 cells before it was found). So a phase that dies part-way
# loses nothing, and re-running this script continues from exactly where it
# stopped rather than starting over.
#
# Phase order is by value, not by size: if the night runs out, the phases that
# completed are the ones the paper most needs.
cd "$(dirname "$0")"
source ./feather.env

M="moonshotai/Kimi-K3,zai-org/GLM-5.2,deepseek-ai/DeepSeek-V4-Pro,nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16"
# Featherless prices concurrency in UNITS, not requests.  Both keys are on
# separate organisations with a plan limit of 4 units each, and a 753B-class
# model costs 4 units per request -- so each key can carry exactly ONE big-model
# call at a time, and two keys means two workers.  Asking for more does not
# queue, it errors.
W=2

# At reasoning_effort=high these models think for minutes before emitting a
# token.  The default 300s ceiling produced `curl exit 28` on every cell of the
# first attempt -- a timeout that reads in the log exactly like a model failure
# and is not one.
T=900

say () { echo ""; echo "=== $(date -u +%H:%M:%S)  $*"; echo ""; }

say "PHASE 1  main corpus, C1+C6, 4 models @ reasoning=high   (96 calls)"
python3 -u runner.py --provider featherless --reasoning high --models "$M" \
    --all --conditions 1,6 --repeats 1 --workers $W --max-tokens 20000 --http-timeout $T

say "PHASE 2  explicit transfer set, C1+C2+C6, 3 shuffles     (108 calls)"
python3 -u runner.py --provider featherless --reasoning high --models "$M" \
    --datasets mi,crime,student --conditions 1,2,6 --repeats 3 \
    --workers $W --max-tokens 20000 --http-timeout $T

say "PHASE 3  main corpus, 2 more shuffles, for intervals     (+192 calls)"
python3 -u runner.py --provider featherless --reasoning high --models "$M" \
    --all --conditions 1,6 --repeats 3 --workers $W --max-tokens 20000 --http-timeout $T

say "PHASE 4  memorisation control, all 306 columns renamed   (+96 calls)"
python3 -u runner.py --provider featherless --reasoning high --models "$M" \
    --all --conditions 1,6 --repeats 1 --workers $W --max-tokens 20000 --http-timeout $T --paraphrase

say "ALL PHASES DONE"
