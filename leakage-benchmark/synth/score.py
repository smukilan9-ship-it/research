"""Score Stratum E and evaluate PREREG.md's decision rule.

DELIBERATELY NOT IN verify_paper.py

  Stratum C's rule, applied here: a post-hoc addition must run BESIDE the
  frozen result, never inside it.  Every number in NUMBERS.txt is computed on
  Strata A-D; folding Stratum E into the same aggregates would silently move
  figures the manuscripts already quote.  This file reads the same response
  cache through the same parser and reports separately.

WHAT IT COMPUTES

  D1  CONSEQUENCE recall - REASON recall, at C1, mean over models.
      Real corpus: +23.2 points.
  D2  REASON recall at C6 - REASON recall at C1.
      Real corpus: +24.8 points.

  Plus the 95% cluster bootstrap over TABLES, 2,000 draws, seed 20260816 --
  the same resampling unit and seed section 19 uses, so the interval here is
  comparable with the interval there.

  The decision rule is applied mechanically and printed.  It is not re-derived
  by hand and it is not adjustable here: the thresholds are read from the
  constants below, which match PREREG.md section 5.
"""
import collections
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from salvage import parse                                   # noqa: E402
import export as EX                                         # noqa: E402

D1_BAR = 10.0          # PREREG section 5
D2_BAR = 10.0
BOOT_N, BOOT_SEED = 2000, 20260816
REAL_D1, REAL_D2 = 23.2, 24.8


def cells(model_sub):
    """Cached Stratum E cells for one model, newest-wins, same guard as
    verify_paper.cells_for -- a cross-regime substring match must not pool."""
    names = set(EX.names())
    out, stamp = {}, {}
    for f in sorted(glob.glob(ROOT + "responses/*.json")):
        r = json.load(open(f))
        if r["dataset"] not in names or r.get("paraphrase"):
            continue
        nm = r["model"]
        if nm != model_sub:
            if model_sub not in nm:
                continue
            if "::" in nm and "::" not in model_sub:
                continue
        d, _ = parse(r.get("raw", ""))
        if not d:
            continue
        k = (r["dataset"], r["condition"])
        this = (r.get("ts") or "", f)
        if k in stamp and this < stamp[k]:
            continue
        stamp[k] = this
        out[k] = {c["name"]: c.get("verdict") for c in d["columns"]
                  if isinstance(c, dict) and c.get("name")}
    return out


def recall_by_subtype(got, cond, tables):
    """hits and totals per mechanism, over the tables answered at `cond`."""
    hit = collections.Counter(); tot = collections.Counter()
    per_table = collections.defaultdict(lambda: (collections.Counter(),
                                                 collections.Counter()))
    for name in tables:
        g = got.get((name, cond))
        if not g:
            continue
        b = EX.bundle(name, want_sample=False)
        for col, mech in b["subtype"].items():
            if not mech:
                continue
            tot[mech] += 1
            h, t = per_table[name]
            t[mech] += 1
            if g.get(col) == "UNAVAILABLE":
                hit[mech] += 1
                h[mech] += 1
    return hit, tot, per_table


def _pct(h, t):
    return 100.0 * h / t if t else float("nan")


def main(models):
    tables = EX.names()
    print("=" * 78)
    print("STRATUM E — synthetic tables the models have not seen")
    print("=" * 78)
    print(f"  {len(tables)} tables, cluster bootstrap over tables, "
          f"{BOOT_N} draws, seed {BOOT_SEED}\n")

    # COMPLETENESS GATE.  A model is admitted only when it has answered every
    # table at both conditions.  Without this the pooled D1 is a mean over rows
    # computed on different numbers of tables, and a model with five cells of
    # forty carries the same weight as one with forty -- which is the
    # "incomparable unit folded into an aggregate" failure incomplete_rosters()
    # exists to prevent, reproduced here.  It first printed a verdict of FAILS
    # TO REPLICATE that was entirely an artefact of one 12%-complete row.
    need = len(tables) * 2
    rows, per_model_tables, partial = [], {}, []
    print(f'{"model":<40}{"cells":>7}{"C1 REA":>8}{"C1 CON":>8}{"C6 REA":>8}{"D1":>8}{"D2":>8}')
    for m in models:
        got = cells(m)
        if not got:
            continue
        if len(got) < need:
            partial.append((m, len(got)))
            continue
        h1, t1, pt1 = recall_by_subtype(got, 1, tables)
        h6, t6, pt6 = recall_by_subtype(got, 6, tables)
        if not t1.get("REASON") or not t6.get("REASON"):
            continue
        c1r, c1c = _pct(h1["REASON"], t1["REASON"]), _pct(h1["CONSEQUENCE"], t1["CONSEQUENCE"])
        c6r = _pct(h6["REASON"], t6["REASON"])
        rows.append((m, c1r, c1c, c6r))
        per_model_tables[m] = (pt1, pt6)
        print(f'{m[:38]:<40}{len(got):>4}/{need:<2}{c1r:>7.1f}%{c1c:>7.1f}%'
              f'{c6r:>7.1f}%{c1c - c1r:>+8.1f}{c6r - c1r:>+8.1f}')

    for m, n in partial:
        print(f'{m[:38]:<40}{n:>4}/{need:<2}   in progress — excluded')

    if not rows:
        print("\n  no model has a complete roster yet; no verdict is available.")
        return 0

    d1 = float(np.mean([c - r for _, r, c, _ in rows]))
    d2 = float(np.mean([s - r for _, r, _, s in rows]))

    # cluster bootstrap over TABLES
    rng = np.random.default_rng(BOOT_SEED)
    draws = []
    for _ in range(BOOT_N):
        pick = rng.choice(len(tables), len(tables), replace=True)
        chosen = [tables[i] for i in pick]
        vals = []
        for m, _, _, _ in rows:
            pt1, _ = per_model_tables[m]
            h = collections.Counter(); t = collections.Counter()
            for nm in chosen:
                if nm in pt1:
                    hh, tt = pt1[nm]; h.update(hh); t.update(tt)
            if t["REASON"] and t["CONSEQUENCE"]:
                vals.append(_pct(h["CONSEQUENCE"], t["CONSEQUENCE"])
                            - _pct(h["REASON"], t["REASON"]))
        if vals:
            draws.append(np.mean(vals))
    lo, hi = (np.percentile(draws, [2.5, 97.5]) if draws else (float("nan"),) * 2)

    print(f'\n  D1  CONSEQUENCE - REASON at C1 : {d1:+.1f} points   '
          f'95% CI [{lo:+.1f}, {hi:+.1f}]   (real corpus {REAL_D1:+.1f})')
    print(f'  D2  REASON C6 - REASON C1      : {d2:+.1f} points   '
          f'(real corpus {REAL_D2:+.1f})')

    replicates = d1 >= D1_BAR and d2 >= D2_BAR and lo > 0
    fails = d1 < D1_BAR or lo <= 0
    verdict = ("REPLICATES" if replicates
               else "FAILS TO REPLICATE" if fails else "INDETERMINATE")
    print(f'\n  PREREG section 5 decision rule '
          f'(D1>={D1_BAR}, D2>={D2_BAR}, CI excludes 0)')
    if len(rows) < len(models):
        print(f'  PRELIMINARY — {len(rows)} of {len(models)} roster models complete.')
        print(f'  Reading on this subset: {verdict}')
        print(f'  This is NOT the verdict.  PREREG section 3 fixes the roster,')
        print(f'  and a decision announced on part of it is the substitution')
        print(f'  this plan exists to prevent.')
    else:
        print(f'  VERDICT: {verdict}   ({len(rows)} models, full roster)')
    return 0


if __name__ == "__main__":
    import verify_paper as V
    sys.exit(main(V.MODELS))
