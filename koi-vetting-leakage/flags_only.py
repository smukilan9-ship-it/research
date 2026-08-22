"""Step H4 — the decisive experiment: can the vetting flags alone reconstruct the label?

  The dossier calls this "the paper's strongest single figure". If six columns
  the Robovetter emitted AS ITS REASONS for a disposition can recover that
  disposition on their own, the models in the census are not doing astrophysics.

  Matched on the clean arm's own folds. data/koi-index.json carries the fold
  assignment for every KOI in the published 0.8618 run, so the contaminated arm
  is scored on the same partition rather than on a fresh split -- otherwise the
  delta mixes the effect of the columns with the effect of a different CV draw.
"""
import json, csv, collections, sys
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report

U = "/root/.claude/uploads/1dfa598a-70c3-5cb5-8d7b-ecd921e451d9/"
CUM = U + "e818b7de-cumulative_2026.08.08_07.34.36.csv"
FLAGS = ["koi_fpflag_nt", "koi_fpflag_ss", "koi_fpflag_co", "koi_fpflag_ec"]

idx = json.load(open("data/koi-index.json"))
fold = {r["objectId"]: r["fold"] for r in idx}
truth = {r["objectId"]: r["actual"] for r in idx}

rows = [r for r in csv.DictReader(l for l in open(CUM) if not l.startswith("#"))]
print(f"  cumulative table: {len(rows)} rows | OOF index: {len(idx)} objects")

def num(v):
    try: return float(v)
    except Exception: return np.nan

ARMS = {
    "flags only (4 fpflags)":            FLAGS,
    "flags + koi_score":                 FLAGS + ["koi_score"],
    "flags + score + pdisposition":      FLAGS + ["koi_score", "koi_pdisposition"],
    "koi_score alone":                   ["koi_score"],
    "koi_pdisposition alone":            ["koi_pdisposition"],
}

for name, cols in ARMS.items():
    X, y, f, kept = [], [], [], 0
    for r in rows:
        oid = r["kepoi_name"]
        if oid not in fold: continue
        vec = []
        for c in cols:
            v = r.get(c, "")
            if c == "koi_pdisposition":
                vec.append(1.0 if v.strip().upper() == "CANDIDATE" else 0.0)
            else:
                vec.append(num(v))
        X.append(vec); y.append(truth[oid]); f.append(fold[oid]); kept += 1
    X = np.array(X, float); y = np.array(y); f = np.array(f)
    pred = np.empty(len(y), dtype=object)
    for k in sorted(set(f)):
        te = f == k; tr = ~te
        m = HistGradientBoostingClassifier(random_state=0).fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    acc = accuracy_score(y, pred); wf1 = f1_score(y, pred, average="weighted")
    print(f"\n  {name:<34} n={kept}  acc={acc:.4f}  weighted-F1={wf1:.4f}")
    if name == "flags only (4 fpflags)":
        best = (y, pred)

print("\n" + "="*70)
print("  CLEAN ARM (published, 98 astrophysical features): acc 0.8618  wF1 0.8624")
print("="*70)
y, pred = best
print(classification_report(y, pred, digits=3))
