"""Emit every Stratum E figure into NUMBERS_E.txt, so the paper can quote them.

WHY A SEPARATE FILE

  `synth/score.py` runs beside the frozen result rather than inside it, for the
  reason its docstring gives: folding Stratum E into NUMBERS.txt's aggregates
  would silently move figures the manuscripts already quote.  Same logic here.
  NUMBERS_E.txt is a sibling, parsed the same way by prose_pins, and nothing in
  NUMBERS.txt changes.

THE BASELINE MISTAKE THIS FILE EXISTS TO PREVENT

  There are TWO correlation baselines in this project and they are not
  interchangeable:

    POOLED   one global threshold swept over every column of every table at
             once.  This is `baselines.best_threshold(y, F.cor.values)`, it is
             what NUMBERS.txt section 5 reports, and it is the ONLY one
             comparable with the paper's 0.630.
    PER-TABLE  a threshold swept within each table and the best kept -- a
             per-table oracle, strictly more generous.  This is
             `synth/check.b3`, and it is correct for what it does: PREREG
             section 6's band gate asks whether each table INDIVIDUALLY has
             statistical structure.

  On the synthetic tables the pooled figure is 0.665 and the per-table mean is
  0.717.  Those 5 points were quoted against the real corpus's pooled 0.630 for
  most of a day, which made the models' margin look far worse than it is: the
  best-model margin is +0.187 at C6, not the +0.135 that comparison implied,
  and exceedance is 9 of 10 rather than 8 of 10.  Both numbers are printed
  below, each labelled, and the comparison line names which one it used.
"""
import glob
import importlib.util
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "."); sys.path.insert(0, "synth")
import export as EX                                          # noqa: E402
import verify_paper as V                                     # noqa: E402

_spec = importlib.util.spec_from_file_location("synth_score", "synth/score.py")
SC = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(SC)

NAMES = EX.names()
REAL_B3, REAL_N, REAL_C1, REAL_C6 = 0.630, 16, 12, 14        # NUMBERS.txt sec 5/6


def pooled_b3():
    """The paper's B3, computed the paper's way: ONE threshold, all columns."""
    score, pos = [], []
    for name in NAMES:
        b = EX.bundle(name, want_sample=False)
        df = pd.read_csv(f"synth/tables/{name}/data.csv")
        y = df[b["target"]].to_numpy().astype(float)
        for c in b["columns"]:
            v = pd.to_numeric(df[c], errors="coerce").to_numpy().astype(float)
            m = ~np.isnan(v)
            r = 0.0 if m.sum() < 3 or v[m].std() == 0 else \
                abs(np.corrcoef(v[m], y[m])[0, 1])
            score.append(0.0 if np.isnan(r) else r); pos.append(bool(b["truth"][c]))
    score = np.array(score); pos = np.array(pos)
    best = None
    for t in sorted(set(score.tolist())):
        fl = score >= t
        tp = int((fl & pos).sum()); fp = int((fl & ~pos).sum()); fn = int((~fl & pos).sum())
        p = tp/(tp+fp) if tp+fp else 0.0
        r = tp/(tp+fn) if tp+fn else 0.0
        f = 2*p*r/(p+r) if p+r else 0.0
        if best is None or f > best["F1"]:
            best = dict(P=p, R=r, F1=f, thr=float(t), tp=tp, fp=fp, fn=fn)
    best["cols"] = len(score); best["pos"] = int(pos.sum())
    return best


def per_table_b3():
    """PREREG section 6's gate figure.  NOT comparable with the paper's 0.630."""
    sys.path.insert(0, "synth")
    from check import b3 as tb3
    out = {}
    for name in NAMES:
        b = EX.bundle(name, want_sample=False)
        df = pd.read_csv(f"synth/tables/{name}/data.csv")
        truth = {c: (b["subtype"][c] if b["truth"][c] else None) for c in b["columns"]}
        out[name] = tb3(df, truth, b["target"])[0]
    return out


def model_f1(model, cond):
    got = SC.cells(model)
    tp = fp = fn = 0; n = 0
    for name in NAMES:
        g = got.get((name, cond))
        if not g: continue
        n += 1
        b = EX.bundle(name, want_sample=False)
        for col, pos in b["truth"].items():
            fl = g.get(col) == "UNAVAILABLE"
            if pos: tp += fl; fn += not fl
            elif fl: fp += 1
    if n < len(NAMES) or tp + fn == 0:          # completeness gate, as score.py
        return None
    p = tp/(tp+fp) if tp+fp else 0.0
    r = tp/(tp+fn) if tp+fn else 0.0
    return dict(P=p, R=r, F1=2*p*r/(p+r) if p+r else 0.0, tp=tp, fp=fp, fn=fn)


def main():
    pb = pooled_b3(); ptb = per_table_b3()
    rows = []
    for m in V.MODELS:
        a, b = model_f1(m, 1), model_f1(m, 6)
        if a and b: rows.append((m, a, b))
    complete, total = len(rows), len(V.MODELS)

    L = []
    W = 78
    L.append("=" * W)
    L.append("NUMBERS_E — Stratum E, the unseen-tables experiment")
    L.append("=" * W)
    L.append(f"roster: {complete} of {total} models complete")
    if complete < total:
        L.append("STATUS: PRELIMINARY.  PREREG section 3 fixes the roster, and no")
        L.append("figure here may be quoted in the paper until this reads "
                 f"{total} of {total}.")
    else:
        L.append("STATUS: COMPLETE ROSTER.  Quotable.")
    L.append("")
    L.append("1. BASELINES")
    L.append(f"  B3 |correlation| POOLED   P {pb['P']:.3f}  R {pb['R']:.3f}  "
             f"F1 {pb['F1']:.3f}  thr {pb['thr']:.4f}")
    L.append(f"     one global threshold over {pb['cols']} columns, "
             f"{pb['pos']} positives — the ONLY figure comparable with the real "
             f"corpus's {REAL_B3:.3f}")
    mean_pt = sum(ptb.values())/len(ptb)
    L.append(f"  B3 |correlation| PER-TABLE  mean {mean_pt:.3f}  "
             f"min {min(ptb.values()):.3f}  max {max(ptb.values()):.3f}")
    L.append(f"     PREREG section 6's band gate [0.45, 0.80], a per-table "
             f"oracle.  NOT comparable with {REAL_B3:.3f}.")
    L.append("")
    L.append("2. PER-MODEL F1")
    L.append(f'  {"model":<44}{"C1":>8}{"C6":>8}')
    for m, a, b in sorted(rows, key=lambda r: -r[2]["F1"]):
        L.append(f'  {m[:42]:<44}{a["F1"]:>8.3f}{b["F1"]:>8.3f}')
    L.append("")
    L.append("3. BASELINE EXCEEDANCE  (against the POOLED B3 above)")
    c1 = sum(1 for _, a, _ in rows if a["F1"] > pb["F1"])
    c6 = sum(1 for _, _, b in rows if b["F1"] > pb["F1"])
    L.append(f"  exceed at C1: {c1} of {complete}")
    L.append(f"  exceed at C6: {c6} of {complete}")
    L.append(f"  real corpus for comparison: {REAL_C1} of {REAL_N} at C1, "
             f"{REAL_C6} of {REAL_N} at C6, against B3 {REAL_B3:.3f}")
    if rows:
        L.append(f"  best margin C1: {max(a['F1'] for _, a, _ in rows) - pb['F1']:+.3f}")
        L.append(f"  best margin C6: {max(b['F1'] for _, _, b in rows) - pb['F1']:+.3f}")
    L.append("")
    L.append("4. SUBTYPE ASYMMETRY  (PREREG's dependent variables)")
    d1s, d2s = [], []
    L.append(f'  {"model":<44}{"C1REA":>8}{"C1CON":>8}{"C6REA":>8}{"D1":>8}{"D2":>8}')
    for m, _, _ in rows:
        got = SC.cells(m)
        h1, t1, _ = SC.recall_by_subtype(got, 1, NAMES)
        h6, t6, _ = SC.recall_by_subtype(got, 6, NAMES)
        r1 = SC._pct(h1["REASON"], t1["REASON"]); c1c = SC._pct(h1["CONSEQUENCE"], t1["CONSEQUENCE"])
        r6 = SC._pct(h6["REASON"], t6["REASON"])
        d1s.append(c1c - r1); d2s.append(r6 - r1)
        L.append(f'  {m[:42]:<44}{r1:>7.1f}%{c1c:>7.1f}%{r6:>7.1f}%'
                 f'{c1c-r1:>+8.1f}{r6-r1:>+8.1f}')
    if d1s:
        L.append(f"  D1 mean {sum(d1s)/len(d1s):+.1f}   D2 mean {sum(d2s)/len(d2s):+.1f}"
                 f"   (real corpus +23.2 and +24.8)")
    L.append("")
    out = "\n".join(L) + "\n"
    open("NUMBERS_E.txt", "w").write(out)
    print(out)
    print(f"wrote NUMBERS_E.txt   ({complete}/{total} models"
          f"{' — PRELIMINARY, not quotable' if complete < total else ' — quotable'})")
    return 0 if complete == total else 1


if __name__ == "__main__":
    sys.exit(main())
