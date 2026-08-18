"""Validate every generated table against PREREG.md's gates.

Run after any change to `tables.py`.  Nothing goes to a model until this is
clean: a table that fails here would either void the run (B3 out of band) or
score a leak that is not a leak (a failed mechanical check).
"""
import collections
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from tables import BUILDERS

BAND = (0.45, 0.80)          # PREREG.md section 6
REAL_DENSITY = 0.131         # Stratum A, 40 leaks in 306 columns
NEED_PER_MECH = 40           # PREREG.md section 3


def b3(df, truth, target):
    """The paper's B3: |corr| with the threshold swept on the answers."""
    y = df[target].to_numpy()
    cols = [c for c in df.columns if c != target]
    r = {}
    for c in cols:
        v = df[c].to_numpy().astype(float)
        r[c] = 0.0 if v.std() == 0 else abs(np.corrcoef(v, y)[0, 1])
    r = {c: (0.0 if np.isnan(v) else v) for c, v in r.items()}
    pos = {c for c in cols if truth[c] is not None}
    best = 0.0
    for thr in sorted(set(r.values())):
        fl = {c for c in cols if r[c] >= thr}
        tp, fp, fn = len(fl & pos), len(fl - pos), len(pos - fl)
        p = tp / (tp + fp) if tp + fp else 0
        rc = tp / (tp + fn) if tp + fn else 0
        f = 2 * p * rc / (p + rc) if p + rc else 0
        best = max(best, f)
    return best, r, pos


def main():
    print("=" * 82)
    print("SYNTHETIC TABLES — PREREG gates")
    print("=" * 82)
    print(f'{"table":<24}{"rows":>6}{"cols":>5}{"leak%":>7}{"y=1":>7}'
          f'{"R/C/T":>9}{"B3":>7}  checks')
    mech = collections.Counter()
    tot_leak = tot_col = 0
    bad = []
    for fn in BUILDERS:
        t = fn()
        df, truth = t["df"], t["truth"]
        probs = [p for c in t["checks"] for p in c(df)]
        f, r, pos = b3(df, truth, t["target"])
        m = collections.Counter(truth[c] for c in pos)
        mech.update(m)
        ncol = len(df.columns) - 1
        tot_leak += len(pos); tot_col += ncol
        faint = min(r[c] for c in pos)
        loud = max(r[c] for c in r if c not in pos)
        flags = []
        if not (BAND[0] <= f <= BAND[1]):
            flags.append("B3 OUT OF BAND"); bad.append(t["name"])
        if faint >= loud:
            flags.append("SEPARABLE"); bad.append(t["name"])
        if probs:
            flags += probs; bad.append(t["name"])
        print(f'{t["name"]:<24}{len(df):>6}{ncol:>5}{len(pos)/ncol:>7.1%}'
              f'{df[t["target"]].mean():>7.1%}'
              f'{f"{m['REASON']}/{m['CONSEQUENCE']}/{m['TIMING']}":>9}{f:>7.3f}'
              f'  {"ok" if not flags else "FAIL"}')
        for x in flags:
            print(f'{"":24}   ! {x}')

    print(f'\n  tables {len(BUILDERS)}/20'
          f'   leak density {tot_leak}/{tot_col} = {tot_leak/tot_col:.1%}'
          f'  (real {REAL_DENSITY:.1%})')
    print(f'  mechanism totals: ' + '  '.join(
        f'{k} {v}/{NEED_PER_MECH}' for k, v in sorted(mech.items())))
    short = {k: NEED_PER_MECH - v for k, v in mech.items() if v < NEED_PER_MECH}
    if short:
        print(f'  still needed: {short}')
    print(f'\n  {"ALL GATES PASS" if not bad else "FAILING: " + ", ".join(sorted(set(bad)))}')
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
