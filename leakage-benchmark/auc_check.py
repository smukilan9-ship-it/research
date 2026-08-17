"""Does AUC systematically underrank BINARY features relative to correlation?

If so, AUC-based leak screens are blind by construction to leaks encoded as
0/1 flags -- which is most of them.  Test: rank every column by (a) max
one-vs-rest AUC and (b) max |correlation|, then ask whether the rank gap
depends on how many distinct values the column takes.
"""
import warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.metrics import roc_auc_score
import harness as H

rows = []
for k in ["koi", "diabetes", "lc", "compas", "ai4i", "titanic"]:
    s = H.LOADERS[k]()
    df, y = s["df"], s["y"]
    cols = s["clean"] + s["leaky"]
    X = H.encode(df, cols)
    auc, cor, nun = {}, {}, {}
    for c in cols:
        v = pd.to_numeric(X[H.safe(c)], errors="coerce")
        v = v.fillna(v.median())
        nun[c] = int(v.nunique())
        a = b = 0.0
        for cl in np.unique(y):
            t = (y == cl).astype(int)
            if v.std() == 0:
                continue
            try:
                a = max(a, abs(roc_auc_score(t, v) - .5) + .5)
            except Exception:
                pass
            b = max(b, abs(np.corrcoef(v, t)[0, 1]))
        auc[c], cor[c] = a or .5, b
    ra = pd.Series(auc).rank(ascending=False, method="min")
    rc = pd.Series(cor).rank(ascending=False, method="min")
    for c in cols:
        rows.append(dict(ds=s["name"], col=c, nun=nun[c],
                         binary=nun[c] <= 2, leaky=c in s["leaky"],
                         rank_auc=int(ra[c]), rank_cor=int(rc[c]),
                         gap=int(ra[c] - rc[c])))

R = pd.DataFrame(rows)
print(f"{len(R)} columns across {R.ds.nunique()} datasets\n")
print("mean rank gap (AUC rank minus CORRELATION rank; positive = AUC ranks it WORSE)")
print(R.groupby("binary").gap.agg(["mean", "median", "count"]).round(2).to_string())
print()
print("restricted to LEAKY columns only")
print(R[R.leaky].groupby("binary").gap.agg(["mean", "median", "count"]).round(2).to_string())
print()
from scipy import stats
b, nb = R[R.binary].gap, R[~R.binary].gap
u, p = stats.mannwhitneyu(b, nb, alternative="greater")
print(f"Mann-Whitney (binary gap > non-binary gap): U={u:.0f}  p={p:.2e}")
print(f"binary n={len(b)}  non-binary n={len(nb)}")
print()
print("worst-penalised binary columns (AUC ranks them far below correlation):")
w = R[R.binary].nlargest(10, "gap")[["ds", "col", "nun", "leaky", "rank_auc", "rank_cor", "gap"]]
print(w.to_string(index=False))
R.to_csv("auc_vs_corr.csv", index=False)
