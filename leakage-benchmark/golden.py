"""Does the leaky column qualify as a "golden variable"?

The EMNLP-2025 tabular feature-engineering evaluation defines the ground truth
for a good feature as

    F_golden = { f_j : |Covariance(f_j, y)| >= gamma }

and scores an LLM by how highly it ranks those variables:

    S_Rank(f) = 1 - (Rank(f) - 1) / |F|         (1.0 = ranked first)

A label-derived field is, by construction, among the highest-covariance columns
in the table.  So an agent that surfaces it should receive a near-maximal score.
This measures whether that is actually true on datasets whose feature provenance
we have verified by hand.

Covariance is scale-dependent, so we report the authors' literal statistic AND
the scale-free correlation.  If the two disagree, that is itself a finding about
the metric.
"""
import warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import harness as H

SPECS = ["koi", "diabetes", "diabetes_pure", "lc", "compas", "ai4i", "titanic"]
rows = []

for key in SPECS:
    spec = H.LOADERS[key]()
    df, y = spec["df"], spec["y"]
    cols = spec["clean"] + spec["leaky"]
    X = H.encode(df, cols)
    leaky_safe = {H.safe(c) for c in spec["leaky"]}
    F = len(cols)

    # one-vs-rest per class, as the definition is stated against a target class
    for cl in np.unique(y):
        t = (y == cl).astype(float)
        cov, cor = {}, {}
        for c in X.columns:
            v = pd.to_numeric(X[c], errors="coerce")
            v = v.fillna(v.median())
            if v.std() == 0:
                cov[c], cor[c] = 0.0, 0.0
                continue
            cov[c] = abs(np.cov(v, t)[0, 1])
            cor[c] = abs(np.corrcoef(v, t)[0, 1])
        rank_cov = pd.Series(cov).rank(ascending=False, method="min")
        rank_cor = pd.Series(cor).rank(ascending=False, method="min")
        for c in sorted(leaky_safe):
            rc, rr = int(rank_cov[c]), int(rank_cor[c])
            rows.append(dict(dataset=spec["name"], target=str(cl), feature=c,
                             F=F,
                             rank_cov=rc, s_rank_cov=1 - (rc - 1) / F,
                             rank_cor=rr, s_rank_cor=1 - (rr - 1) / F,
                             cov=cov[c], cor=cor[c]))

R = pd.DataFrame(rows)

print("=" * 92)
print("Rank of each LEAKY column among all columns, by the benchmark's own statistic")
print("=" * 92)
print(f"{'dataset':<14}{'target class':<16}{'leaky feature':<26}{'|F|':>5}"
      f"{'rank':>6}{'S_Rank':>8}   {'rank':>5}{'S_Rank':>8}")
print(f"{'':<14}{'':<16}{'':<26}{'':>5}{'--- covariance ---':>14}   {'-- correlation --':>13}")
for _, r in R.iterrows():
    print(f"{r.dataset:<14}{r.target:<16}{r.feature:<26}{r.F:>5}"
          f"{r.rank_cov:>6}{r.s_rank_cov:>8.3f}   {r.rank_cor:>5}{r.s_rank_cor:>8.3f}")

print("\n" + "=" * 92)
print("SUMMARY  -- taking, for each dataset, the leaky feature's BEST rank over classes")
print("=" * 92)
best = (R.groupby(["dataset", "feature"])
         .agg(F=("F", "first"), rank_cov=("rank_cov", "min"),
              rank_cor=("rank_cor", "min")).reset_index())
best["s_cov"] = 1 - (best.rank_cov - 1) / best.F
best["s_cor"] = 1 - (best.rank_cor - 1) / best.F
for _, r in best.iterrows():
    tag_c = "GOLDEN" if r.rank_cor <= 3 else ""
    print(f"  {r.dataset:<14}{r.feature:<26} cov rank {r.rank_cov:>3}/{r.F:<4}"
          f"S={r.s_cov:.3f}   cor rank {r.rank_cor:>3}/{r.F:<4}S={r.s_cor:.3f}  {tag_c}")

n_top1 = (best.rank_cor == 1).sum()
n_top3 = (best.rank_cor <= 3).sum()
print(f"\n  leaky features ranked #1 by |correlation| : {n_top1}/{len(best)}")
print(f"  leaky features in the top 3               : {n_top3}/{len(best)}")
print(f"  mean S_Rank an agent earns for surfacing the leak (correlation): "
      f"{best.s_cor.mean():.3f}   (1.0 = maximum possible)")
print(f"  mean S_Rank under the authors' literal covariance statistic    : "
      f"{best.s_cov.mean():.3f}")
R.to_csv(H.HERE + "golden_ranks.csv", index=False)
