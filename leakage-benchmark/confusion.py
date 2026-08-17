"""Pooled confusion matrices for the leaked and clean arms.

WHY A SEPARATE PASS
  downstream2.py records auc/f1/precision/recall AVERAGED over folds.  A
  confusion matrix cannot be recovered from fold-averaged rates -- the
  arithmetic only closes if the counts are pooled.  Reconstructing TP/FP/FN/TN
  from mean precision and mean recall would give plausible numbers that are
  not the ones the models produced, which is exactly the sort of fabricated
  detail this project has spent two days removing.

  So this refits the same two arms with the same procedure and sums the raw
  cell counts across folds instead.  Only ALL and GT are run: 48 evaluations
  rather than 192, because those are the two arms a confusion matrix is
  actually asked about.

  Everything else -- class weighting, capacity, threshold chosen on inner
  out-of-fold predictions over the training part only -- is unchanged from
  downstream2, so the matrices correspond to the F1 numbers already reported.
"""
import os, sys, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN
from downstream2 import (frame, encode, binarise, make, best_threshold,
                         GROUP_KEY, SEED)
from sklearn.model_selection import StratifiedKFold, GroupKFold, cross_val_predict
from sklearn.metrics import confusion_matrix


def pooled(X, y, groups, learner):
    """5-fold CV, counts POOLED over folds so the matrix is exact."""
    if X.shape[1] == 0 or len(np.unique(y)) < 2:
        return None
    if groups is not None and len(np.unique(groups)) >= 5:
        folds = list(GroupKFold(n_splits=5).split(X, y, groups))
    else:
        folds = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(X, y))
    TN = FP = FN = TP = 0
    for tr, te in folds:
        if len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2:
            continue
        oof = cross_val_predict(make(learner, y[tr]), X[tr], y[tr],
                                cv=StratifiedKFold(3, shuffle=True, random_state=SEED),
                                method="predict_proba", n_jobs=1)[:, 1]
        thr = best_threshold(y[tr], oof)
        m = make(learner, y[tr]).fit(X[tr], y[tr])
        yh = (m.predict_proba(X[te])[:, 1] >= thr).astype(int)
        tn, fp, fn, tp = confusion_matrix(y[te], yh, labels=[0, 1]).ravel()
        TN += tn; FP += fp; FN += fn; TP += tp
    p = TP / (TP + FP) if TP + FP else 0.0
    r = TP / (TP + FN) if TP + FN else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return dict(tn=int(TN), fp=int(FP), fn=int(FN), tp=int(TP),
                precision=p, recall=r, f1=f)


def main():
    keys = [a for a in sys.argv[1:] if not a.startswith("-")] or RN.ALLSETS
    rows = []
    for key in keys:
        try:
            b = RN.spec_bundle(key); df = frame(key)
        except Exception as e:
            print(f"  {key}: SKIP {type(e).__name__}"); continue
        df.columns = [str(c).strip() for c in df.columns]
        name, tgt = b["name"], b["target"]
        if tgt not in df.columns:
            continue
        y = binarise(df[tgt])
        if y is None:
            continue
        feats = [c for c in b["columns"] if c in df.columns]
        gk = GROUP_KEY.get(name)
        groups = df[gk].values if gk and gk in df.columns else None
        X = encode(df[feats])
        gt = {c for c, p in b["truth"].items() if p}
        for learner in ("rf", "gb"):
            for arm, drop in (("LEAKED", set()), ("CLEAN", gt)):
                cols = [c for c in feats if c not in drop]
                r = pooled(X[cols].values, y, groups, learner)
                if r is None:
                    continue
                rows.append(dict(dataset=name, learner=learner, arm=arm,
                                 n=len(df), n_dropped=len(drop), **r))
                print(f"  {name:<12}{learner:<4}{arm:<8}"
                      f"TN={r['tn']:>6} FP={r['fp']:>5} FN={r['fn']:>5} TP={r['tp']:>5}   "
                      f"P {r['precision']:.3f}  R {r['recall']:.3f}  F1 {r['f1']:.3f}",
                      flush=True)
    pd.DataFrame(rows).to_csv(HERE + "confusion.csv", index=False)
    print(f"\nwrote confusion.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
