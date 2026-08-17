"""Baselines recomputed on the 10-dataset corpus.

The B3 figure quoted throughout (F1 0.812, |correlation| at a threshold tuned on
the answers) was measured on six datasets and 17 positives.  Carrying it over to
a 10-dataset, 38-positive corpus would compare the models against a bar computed
on different data -- the same category of error as scoring a partial run against
a full one.  This recomputes every baseline on exactly the columns the models
were asked about.

Thresholds are still swept on the test answers, so these remain UPPER bounds on
what a statistical screen could do without knowing them.  That is deliberate:
a baseline that was never tuned is a strawman.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.metrics import roc_auc_score, matthews_corrcoef

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN, harness as H
from screen import PAT
from subtypes import subtype


def features():
    rows = []
    for key in RN.ALLSETS:
        try:
            b = RN.spec_bundle(key)
        except Exception as e:
            print(f"  skip {key}: {type(e).__name__}")
            continue
        # the frame and target for this spec
        if key in RN.EXPANSION or key in RN.TRANSFER:
            import newspecs as NS, newdata as ND
            spec = ND.NEW[key]()
            df, tgt = spec["df"], NS.SPECS[key]["target"]
        else:
            s = H.LOADERS[key]()
            df, tgt = s["df"], RN.TARGET[b["name"]]
        y = df[tgt].map(str).values
        cols = [c for c in b["columns"] if c in df.columns]
        X = H.encode(df, cols)
        classes = np.unique(y)
        for c in cols:
            v = pd.to_numeric(X[H.safe(c)], errors="coerce")
            raw = df[c]
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
                    cc = np.corrcoef(vf, t)[0, 1]
                    if cc == cc:
                        cor = max(cor, abs(cc))
            if miss.nunique() > 1:
                rates = [miss[y == cl].mean() for cl in classes]
                mrng = max(rates) - min(rates)
            rows.append(dict(ds=b["name"], col=c, y=bool(b["truth"][c]),
                             subtype=subtype(b["name"], c) or "",
                             auc=auc, cor=cor, miss=mrng,
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
    best = dict(f1=-1)
    for t in sorted(set(np.round(score, 4))):
        m = prf(y, score >= t)
        if m["f1"] > best["f1"]:
            best = dict(m, threshold=float(t))
    return best


if __name__ == "__main__":
    F = features()
    y = F.y.values.astype(bool)
    print(f"\n{len(F)} columns, {y.sum()} label-derived ({100*y.mean():.1f}%), "
          f"{F.ds.nunique()} datasets\n")
    out = {}
    out["B0 always AVAILABLE"] = prf(y, np.zeros(len(y), bool))
    out["B1 name regex"] = prf(y, F.regex.values.astype(bool))
    out["B2 univariate AUC"] = best_threshold(y, F.auc.values)
    out["B3 |correlation|"] = best_threshold(y, F.cor.values)
    out["B4 missingness asym"] = best_threshold(y, F.miss.values)
    print(f"{'baseline':<24}{'P':>7}{'R':>7}{'F1':>7}{'MCC':>7}{'TP':>5}{'FP':>5}{'FN':>5}")
    for k, m in out.items():
        thr = f"  thr={m['threshold']:.3f}" if "threshold" in m else ""
        print(f"{k:<24}{m['precision']:>7.3f}{m['recall']:>7.3f}{m['f1']:>7.3f}"
              f"{m['mcc']:>7.3f}{m['tp']:>5}{m['fp']:>5}{m['fn']:>5}{thr}")
    print("\n  thresholds tuned ON the answers -- UPPER bounds")

    b3 = out["B3 |correlation|"]
    pred = F.cor.values >= b3["threshold"]
    print(f"\nB3 recall by subtype (the comparison that matters):")
    for st in ("REASON", "CONSEQUENCE", "TIMING", "CONTESTED"):
        idx = (F.subtype == st).values & y
        if idx.sum():
            print(f"   {st:<14}{int(pred[idx].sum())}/{int(idx.sum())}"
                  f"  {pred[idx].mean():.0%}")
    print("\nB3 false positives -- legitimate columns it would delete:")
    fp = F[(~F.y) & (F.cor >= b3["threshold"])]
    for _, r in fp.head(12).iterrows():
        print(f"   {r.ds:<12}{r.col:<26}|cor|={r.cor:.3f}")
    print(f"   ({len(fp)} total)")
    F.to_csv(HERE + "baseline10_features.csv", index=False)
