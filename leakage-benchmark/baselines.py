"""Training-free baselines for provenance detection.

The bar the language models must clear.  Every baseline is given its BEST
achievable threshold on the test data itself -- deliberately generous, because
a baseline that was never tuned is a strawman and we have already been burned
once today by a weak baseline.

Baselines
  B0  always AVAILABLE          the majority-class trap (89% accuracy, 0 recall)
  B1  name regex                the sieve's markers, applied to column names
  B2  univariate AUC            best threshold, values
  B3  |correlation|             best threshold, values
  B4  missingness asymmetry     |P(null | class A) - P(null | class B)|, best threshold
  B5  B1 OR B2                  cheap union -- can names plus values beat either?

Scored on the positive class (label-derived), because accuracy is meaningless
at 11% prevalence.
"""
import json, re, sys, os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.metrics import roc_auc_score, matthews_corrcoef

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H
from screen import PAT

TRUTH = os.path.dirname(os.path.abspath(__file__)) + "/provenance_truth.json"


def load_truth():
    inv = json.load(open(TRUTH))
    return {(r["ds"], r["col"]): (r["truth"] == "label-derived") for r in inv}


def features():
    """Per column: the signals every baseline is allowed to use."""
    truth = load_truth()
    rows = []
    for k in ["koi", "diabetes", "lc", "compas", "ai4i", "titanic"]:
        s = H.LOADERS[k]()
        df, y = s["df"], s["y"]
        cols = s["clean"] + s["leaky"]
        X = H.encode(df, cols)
        classes = np.unique(y)
        for c in cols:
            key = (s["name"], c)
            if key not in truth:
                continue
            v = pd.to_numeric(X[H.safe(c)], errors="coerce")
            raw = df[c] if c in df else v
            miss = raw.isna()
            vf = v.fillna(v.median())
            auc = cor = mrng = 0.0
            for cl in classes:
                t = (y == cl).astype(int)
                if vf.std() > 0:
                    try:
                        auc = max(auc, abs(roc_auc_score(t, vf) - .5) + .5)
                    except Exception:
                        pass
                    cor = max(cor, abs(np.corrcoef(vf, t)[0, 1]))
            if miss.nunique() > 1:
                rates = [miss[y == cl].mean() for cl in classes]
                mrng = max(rates) - min(rates)
            rows.append(dict(ds=s["name"], col=c, y=truth[key],
                             auc=auc, cor=cor if cor == cor else 0.0, miss=mrng,
                             regex=bool(PAT.search(str(c).replace("_", " ")))))
    return pd.DataFrame(rows)


def prf(y, pred):
    tp = int((y & pred).sum()); fp = int((~y & pred).sum()); fn = int((y & ~pred).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    mcc = matthews_corrcoef(y, pred) if pred.any() and (~pred).any() else 0.0
    return dict(tp=tp, fp=fp, fn=fn, precision=p, recall=r, f1=f, mcc=mcc)


def best_threshold(y, score):
    """Sweep every threshold, keep the best F1.  Generous by construction."""
    best = dict(f1=-1)
    for t in sorted(set(np.round(score, 4))):
        m = prf(y, score >= t)
        if m["f1"] > best["f1"]:
            best = dict(m, threshold=float(t))
    return best


if __name__ == "__main__":
    F = features()
    y = F.y.values.astype(bool)
    print(f"{len(F)} columns, {y.sum()} label-derived ({100*y.mean():.1f}%), "
          f"{F.ds.nunique()} datasets\n")
    out = {}
    out["B0 always AVAILABLE"] = prf(y, np.zeros(len(y), bool))
    out["B1 name regex"] = prf(y, F.regex.values.astype(bool))
    out["B2 univariate AUC"] = best_threshold(y, F.auc.values)
    out["B3 |correlation|"] = best_threshold(y, F.cor.values)
    out["B4 missingness asym"] = best_threshold(y, F.miss.values)
    out["B5 regex OR best-AUC"] = prf(
        y, F.regex.values.astype(bool) | (F.auc.values >= out["B2 univariate AUC"]["threshold"]))

    print(f"{'baseline':<24}{'P':>7}{'R':>7}{'F1':>7}{'MCC':>7}{'TP':>5}{'FP':>5}{'FN':>5}   note")
    for k, m in out.items():
        thr = f"  thr={m['threshold']:.3f}" if "threshold" in m else ""
        print(f"{k:<24}{m['precision']:>7.3f}{m['recall']:>7.3f}{m['f1']:>7.3f}"
              f"{m['mcc']:>7.3f}{m['tp']:>5}{m['fp']:>5}{m['fn']:>5}{thr}")
    print("\n  thresholds are tuned ON the test data -- these are UPPER bounds")
    print("  a model must beat the best F1 here to be worth anything")

    print("\nper-dataset recall of the best single baseline (B2):")
    pred = F.auc.values >= out["B2 univariate AUC"]["threshold"]
    for ds, g in F.groupby("ds"):
        idx = F.ds.values == ds
        yy, pp = y[idx], pred[idx]
        if yy.sum():
            print(f"   {ds:<12}{int((yy&pp).sum())}/{int(yy.sum())} positives found")
    F.to_csv(os.path.dirname(os.path.abspath(__file__)) + "/baseline_features.csv", index=False)
