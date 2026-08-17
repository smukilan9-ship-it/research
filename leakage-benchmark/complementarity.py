"""Are the statistical screen and the semantic screen blind in the same places?

The 10-dataset baselines showed a pattern that inverts the models':

    B3 |correlation|   REASON 89%   CONSEQUENCE 48%   TIMING 50%
    gemini-3.7 C1      REASON 44%   CONSEQUENCE 70%   TIMING 100%

That is not a coincidence and the mechanism is legible.  A REASON column
determines the label, so it correlates with it almost by construction and a
correlation screen cannot miss it -- but it is temporally PRIOR, so a model
reasoning about availability calls it available.  A CONSEQUENCE column is often
weakly correlated (`body` is 0.014) yet semantically obvious: a body number
exists because the passenger died.

If that is right, the union should beat either screen by more than the overlap
suggests, and the two should disagree systematically rather than randomly.
This module measures that, on exactly the columns both were asked about.

Reported as triage, not deletion: the practical question is how many columns a
human must read to catch a given share of the leaks.
"""
import json, os, glob, sys, collections
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
from salvage import parse
import runner as RN
from subtypes import subtype

ORDER = ["REASON", "CONSEQUENCE", "TIMING", "CONTESTED"]


def llm_flags(model, cond):
    """(dataset, column) -> flagged, for one model+condition."""
    out, newest = {}, {}
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if r.get("paraphrase") or r["model"] != model or r["condition"] != cond:
            continue
        k = (r["dataset"], r["condition"])
        if k not in newest or r.get("ts", "") > newest[k].get("ts", ""):
            newest[k] = r
    for r in newest.values():
        d, _ = parse(r.get("raw", ""))
        if not d:
            continue
        for c in d["columns"]:
            if isinstance(c, dict) and c.get("name"):
                out[(r["dataset"], c["name"])] = (c.get("verdict") == "UNAVAILABLE")
    return out


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main():
    F = pd.read_csv(HERE + "baseline10_features.csv")
    # B3's tuned threshold is recomputed with the corpus; hard-coding it meant
    # the union/agreement numbers silently referred to an older corpus.
    import numpy as np
    yv = F.y.values.astype(bool)
    best, thr = -1, 0.0
    for t in sorted(set(np.round(F.cor.values, 4))):
        pr = F.cor.values >= t
        tp_ = int((yv & pr).sum()); fp_ = int((~yv & pr).sum()); fn_ = int((yv & ~pr).sum())
        p_ = tp_ / (tp_ + fp_) if tp_ + fp_ else 0
        r_ = tp_ / (tp_ + fn_) if tp_ + fn_ else 0
        f_ = 2 * p_ * r_ / (p_ + r_) if p_ + r_ else 0
        if f_ > best:
            best, thr = f_, float(t)
    print(f"B3 threshold refitted on this corpus: {thr:.4f} (F1 {best:.3f})\n")
    model = "gemini-3.7-flash"

    for cond in (1, 6):
        flags = llm_flags(model, cond)
        rows = []
        for _, r in F.iterrows():
            key = (r.ds, r.col)
            if key not in flags:
                continue            # column the model was not asked about
            rows.append(dict(ds=r.ds, col=r.col, y=bool(r.y),
                             st=r.subtype if isinstance(r.subtype, str) else "",
                             b3=bool(r.cor >= thr), llm=bool(flags[key])))
        D = pd.DataFrame(rows)
        y = D.y.values
        b3, llm = D.b3.values, D.llm.values
        both, either = b3 & llm, b3 | llm

        print(f"=== {model}  C{cond}   ({len(D)} columns, {y.sum()} positives)\n")
        print(f"{'screen':<26}{'P':>7}{'R':>7}{'F1':>7}{'TP':>5}{'FP':>5}{'FN':>5}")
        for nm, pred in (("B3 |correlation|", b3), (f"LLM C{cond}", llm),
                         ("UNION  (B3 or LLM)", either),
                         ("AGREE  (B3 and LLM)", both)):
            tp = int((y & pred).sum()); fp = int((~y & pred).sum())
            fn = int((y & ~pred).sum())
            p, r, f = prf(tp, fp, fn)
            print(f"{nm:<26}{p:>7.3f}{r:>7.3f}{f:>7.3f}{tp:>5}{fp:>5}{fn:>5}")

        print(f"\n  recall by subtype")
        print(f"  {'subtype':<14}{'B3':>10}{'LLM':>10}{'UNION':>10}")
        for st in ORDER:
            idx = (D.st == st).values & y
            if not idx.sum():
                continue
            print(f"  {st:<14}{b3[idx].mean():>9.0%}{llm[idx].mean():>10.0%}"
                  f"{either[idx].mean():>10.0%}")

        # the disagreement, which is the actual claim
        only_b3 = int((y & b3 & ~llm).sum())
        only_llm = int((y & llm & ~b3).sum())
        print(f"\n  positives found ONLY by correlation: {only_b3}")
        for _, r in D[(D.y) & (D.b3) & (~D.llm)].iterrows():
            print(f"     {r.ds:<12}{r.col:<26}{r.st}")
        print(f"  positives found ONLY by the model:    {only_llm}")
        for _, r in D[(D.y) & (D.llm) & (~D.b3)].iterrows():
            print(f"     {r.ds:<12}{r.col:<26}{r.st}")
        missed = int((y & ~either).sum())
        print(f"  missed by BOTH: {missed}")
        for _, r in D[(D.y) & (~D.b3) & (~D.llm)].iterrows():
            print(f"     {r.ds:<12}{r.col:<26}{r.st}")

        # triage framing: reviewer effort
        n_flag = int(either.sum())
        print(f"\n  TRIAGE: union flags {n_flag}/{len(D)} columns "
              f"({n_flag/len(D):.0%}) and catches {int((y&either).sum())}/{int(y.sum())} "
              f"leaks ({(y&either).sum()/y.sum():.0%})")
        print()


if __name__ == "__main__":
    main()
