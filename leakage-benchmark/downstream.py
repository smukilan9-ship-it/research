"""What the leakage actually costs, and how much of it a model recovers.

THE QUESTION
  Everything so far scores the detector against a list of column names.  That
  measures agreement with documentation; it does not show that the columns
  matter.  A reviewer is entitled to ask: if I leave them in, how wrong is my
  reported performance, and does dropping what the LLM flags fix it?

THREE ARMS, ONE LEARNER AT A TIME
  ALL     every column -- what a practitioner gets by default
  GT      documented positives removed -- the honest ceiling
  MODEL   the columns the LLM flagged at C6 removed
  B3      the columns the tuned correlation baseline flagged removed

  B3 is included because it is the arm that shows whether the LLM is doing
  anything a threshold could not.  Its threshold (|corr| >= 0.3202) was swept
  on the answers, so it is a BEST CASE for the baseline and still an unfair
  comparison in the baseline's favour.

  The quantity of interest is not any single AUC.  It is the INFLATION,
  AUC(ALL) - AUC(GT), and then the fraction of that inflation each automatic
  arm removes.  Reporting AUCs alone would let a dataset where nothing leaks
  dominate the average with noise.

WHY TWO LEARNERS
  Leakage is a property of the data, not of the estimator, so the inflation
  should appear under both a random forest and gradient boosting.  If it
  appears under only one, the effect is an artefact of the learner and the
  claim does not hold.

WHAT IS DELIBERATELY NOT DONE
  No tuning, no feature engineering, no imputation cleverness.  The arms must
  differ ONLY in which columns are present; any per-arm choice would confound
  the comparison with modelling skill.
"""
import json, os, sys, glob, collections, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN
from salvage import parse
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, GroupKFold
from sklearn.metrics import roc_auc_score

SEED = 0
# A group key means repeated units.  Splitting them at random puts the same
# unit on both sides and inflates every arm equally, which would hide the
# effect we are measuring rather than exaggerate it.
GROUP_KEY = {"DIABETES": "patient_nbr", "LC": "member_id", "COMPAS": "id"}


def frame(key):
    if key in RN.EXPANSION or key in RN.TRANSFER:
        import newdata as ND
        return ND.NEW[key]()["df"]
    if key in RN.EXPLICIT:
        import explicit_specs as ES
        return pd.read_csv(f"{HERE}uci/{ES.SPECS[key]['uci']}/data.csv")
    import harness as H
    return H.LOADERS[key]()["df"]


def encode(df):
    """Ordinal-encode objects, median-fill numerics.  Identical in every arm."""
    # `dtype == object` is NOT a test for "not numeric" under pandas' string
    # dtype: a str-dtyped column fails it, falls through to to_numeric, becomes
    # all-NaN and is then median-filled to a constant.  Every categorical
    # feature would have been silently deleted in all three arms.
    out = pd.DataFrame(index=df.index)
    for c in df.columns:
        s = df[c]
        if not pd.api.types.is_numeric_dtype(s):
            out[c] = pd.factorize(s.astype(str))[0]
        else:
            s = pd.to_numeric(s, errors="coerce")
            out[c] = s.fillna(s.median() if s.notna().any() else 0.0)
    return out.astype(float)


def binarise(y):
    y = pd.Series(y)
    if not pd.api.types.is_numeric_dtype(y):
        vc = y.astype(str).value_counts()
        if len(vc) < 2:
            return None
        return (y.astype(str) == vc.index[0]).astype(int).values
    u = pd.unique(y.dropna())
    if len(u) == 2:
        return (y == max(u)).astype(int).values
    if len(u) < 2:
        return None
    return (y > y.median()).astype(int).values


def auc(X, y, groups, learner):
    if X.shape[1] == 0 or len(np.unique(y)) < 2:
        return np.nan
    if groups is not None and len(np.unique(groups)) >= 5:
        splitter = GroupKFold(n_splits=5).split(X, y, groups)
    else:
        splitter = StratifiedKFold(5, shuffle=True, random_state=SEED).split(X, y)
    scores = []
    for tr, te in splitter:
        if len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2:
            continue
        m = (RandomForestClassifier(300, random_state=SEED, n_jobs=-1)
             if learner == "rf" else
             HistGradientBoostingClassifier(random_state=SEED))
        m.fit(X[tr], y[tr])
        scores.append(roc_auc_score(y[te], m.predict_proba(X[te])[:, 1]))
    return float(np.mean(scores)) if scores else np.nan


B3_THRESHOLD = 0.3202          # swept on the answers in baselines10.py


def b3_flags(dataset):
    """Columns the correlation baseline would delete."""
    import pandas as pd
    f = HERE + "baseline10_features.csv"
    if not os.path.exists(f):
        return set()
    d = pd.read_csv(f)
    d = d[d.ds == dataset]
    return set(d.loc[d.cor.abs() >= B3_THRESHOLD, "col"])


def model_flags(dataset, condition=6, model_sub="gemini-3.7"):
    """Columns the LLM called UNAVAILABLE, pooled across seeds by majority."""
    votes = collections.defaultdict(lambda: [0, 0])
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if r["dataset"] != dataset or r["condition"] != condition:
            continue
        if r.get("paraphrase") or model_sub not in r["model"]:
            continue
        d, _ = parse(r.get("raw", ""))
        if not d:
            continue
        for c in d["columns"]:
            if isinstance(c, dict) and c.get("name"):
                votes[c["name"]][1] += 1
                if c.get("verdict") == "UNAVAILABLE":
                    votes[c["name"]][0] += 1
    return {c for c, (u, n) in votes.items() if n and u * 2 > n}


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    keys = only or RN.ALLSETS
    rows = []
    for key in keys:
        try:
            b = RN.spec_bundle(key)
            df = frame(key)
        except Exception as e:
            print(f"  {key:<12}SKIP {type(e).__name__}: {str(e)[:70]}")
            continue
        df.columns = [str(c).strip() for c in df.columns]
        name, tgt = b["name"], b["target"]
        if tgt not in df.columns:
            print(f"  {name:<12}SKIP target {tgt!r} absent")
            continue
        y = binarise(df[tgt])
        if y is None:
            print(f"  {name:<12}SKIP target not binarisable")
            continue
        feats = [c for c in b["columns"] if c in df.columns]
        gk = GROUP_KEY.get(name)
        groups = df[gk].values if gk and gk in df.columns else None
        gt = {c for c, p in b["truth"].items() if p}
        flags = model_flags(name) & set(feats)
        b3 = b3_flags(name) & set(feats)
        X = encode(df[feats])
        Xv = X.values
        for learner in ("rf", "gb"):
            a_all = auc(Xv, y, groups, learner)
            a_gt = auc(X[[c for c in feats if c not in gt]].values, y, groups, learner)
            a_md = auc(X[[c for c in feats if c not in flags]].values, y, groups, learner)
            a_b3 = auc(X[[c for c in feats if c not in b3]].values, y, groups, learner)
            rows.append(dict(dataset=name, learner=learner, n=len(df),
                             n_feat=len(feats), n_gt=len(gt), n_flag=len(flags),
                             n_b3=len(b3), all=a_all, gt=a_gt, model=a_md, b3=a_b3))
            print(f"  {name:<12}{learner:<4}{len(feats):>4}f {len(gt):>3}gt "
                  f"{len(flags):>3}flag {len(b3):>3}b3   ALL {a_all:.3f}  "
                  f"GT {a_gt:.3f}  MODEL {a_md:.3f}  B3 {a_b3:.3f}", flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(HERE + "downstream.csv", index=False)

    print(f"\ninflation = AUC(ALL) - AUC(GT);  recovered = "
          f"(ALL - MODEL) / (ALL - GT)\n")
    d["infl"] = d["all"] - d["gt"]
    leaky = d[d["n_gt"] > 0].copy()
    print(f"{'learner':<9}{'ds':>4}{'mean infl':>11}{'median':>9}"
          f"{'max':>8}{'LLM recovers':>14}{'B3 recovers':>13}")
    for learner, g in leaky.groupby("learner"):
        den = g["infl"].where(g["infl"].abs() > 1e-9)
        # clipped to [-1, 2]: an arm that drops a legitimate column can score
        # above 1, and without a clip one such dataset dominates the mean
        rec = np.clip((g["all"] - g["model"]) / den, -1, 2)
        rb3 = np.clip((g["all"] - g["b3"]) / den, -1, 2)
        print(f"{learner:<9}{len(g):>4}{g['infl'].mean():>11.3f}"
              f"{g['infl'].median():>9.3f}{g['infl'].max():>8.3f}"
              f"{np.nanmean(rec):>14.2f}{np.nanmean(rb3):>13.2f}")
    # The ratio (ALL-arm)/(ALL-GT) reads ~1.00 for both arms and hides the
    # thing that actually differs: an arm can overshoot the honest ceiling by
    # deleting a legitimate column and still score 1.00.  Distance from GT does
    # not have that blind spot, so it is the number reported.
    leaky["dm"] = (leaky["model"] - leaky["gt"]).abs()
    leaky["db"] = (leaky["b3"] - leaky["gt"]).abs()
    print(f"\ndistance from the honest ceiling |arm - GT|, lower is better\n")
    print(f"{'learner':<9}{'ds':>4}{'|LLM-GT|':>11}{'|B3-GT|':>10}"
          f"{'LLM closer':>12}{'B3 closer':>11}{'tie':>5}")
    for learner, g in leaky.groupby("learner"):
        w = int((g.dm < g.db - 1e-6).sum()); l = int((g.db < g.dm - 1e-6).sum())
        print(f"{learner:<9}{len(g):>4}{g.dm.mean():>11.3f}{g.db.mean():>10.3f}"
              f"{w:>12}{l:>11}{len(g)-w-l:>5}")

    print(f"\nper dataset (rf), sorted by inflation")
    r = leaky[leaky.learner == "rf"].sort_values("infl", ascending=False)
    print(f"{'dataset':<12}{'ALL':>7}{'GT':>7}{'MODEL':>7}{'B3':>7}"
          f"{'infl':>8}{'flags':>7}{'b3':>5}")
    for _, x in r.iterrows():
        print(f"{x['dataset']:<12}{x['all']:>7.3f}{x['gt']:>7.3f}"
              f"{x['model']:>7.3f}{x['b3']:>7.3f}{x['infl']:>8.3f}"
              f"{x['n_flag']:>7.0f}{x['n_b3']:>5.0f}")
    print(f"\nwrote downstream.csv")


if __name__ == "__main__":
    main()
