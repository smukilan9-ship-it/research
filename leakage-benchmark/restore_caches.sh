#!/bin/sh
# Four sweep caches are committed gzipped: uncompressed they are 195 MB and
# two of them are over GitHub's 50 MB warning threshold, which would make the
# repository unpleasant to clone for no benefit -- nothing reads them until you
# re-run a sweep.  This puts them back.
#
# openml_meta/features.json in particular is NOT optional if you re-run
# openml_scan.py: the script reads it before touching the network, because the
# OpenML API is unreachable from some environments and a silent fallback to a
# live call returned "0 anchored" once instead of failing loudly.
set -e
cd "$(dirname "$0")"
for f in hf_meta/cards.json kaggle_meta/full.json kaggle_meta/deep_index.json \
         openml_meta/features.json; do
    if [ -f "$f.gz" ]; then
        gunzip -k -f "$f.gz"
        echo "restored $f"
    elif [ -f "$f" ]; then
        echo "already present: $f"
    else
        echo "MISSING: neither $f nor $f.gz" >&2
    fi
done
