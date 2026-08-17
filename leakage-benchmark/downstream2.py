"""What the leakage costs downstream -- AUC *and* F1, with models worth trusting.

WHY THIS REPLACES downstream.py

  The first version reported AUC only, at default hyperparameters, with the
  implicit 0.5 decision threshold.  That is fine for AUC, which is
  threshold-free, and useless for F1: on an imbalanced target a default
  threshold produces a bad F1 no matter how good the model is, and the number
  then measures our threshold choice rather than the data.  A weak honest
  ceiling makes the whole comparison unreadable -- if ARM-GT scores F1 0.5,
  the right question is "did you train it properly?", not "how much did the
  leakage help?".

  So this file does three things the first one did not:

    1. CLASS WEIGHTING.  Every learner sees balanced class weights, so the
       minority class is not simply ignored.
    2. THRESHOLD SELECTION, HONESTLY.  Inside each outer fold, the decision
       threshold is chosen on out-of-fold predictions over the TRAINING part
       only (an inner 3-fold), then applied to the held-out part.  The test
       fold never participates in choosing its own threshold.
    3. REAL CAPACITY.  Deeper forests, early-stopped boosting.

  The discipline that makes the comparison still valid: **the identical
  procedure runs inside every arm**.  No arm gets tuning the others do not.
  The arms differ only in which columns are present, which was the point.

ARMS
  ALL      every column -- what a practitioner gets by default
  GT       documented positives removed -- the honest ceiling
  B3       what the tuned correlation baseline flags, removed
  <model>  what each LLM flagged at C6, removed -- one arm per model
"""
import json, os, sys, glob, collections, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN
from salvage import parse
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, GroupKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score

SEED = 0
B3_THRESHOLD = 0.3202
GROUP_KEY = {"DIABETES": "patient_nbr", "LC": "member_id", "COMPAS": "id"}

# every model whose C6 flags we can score a cleaning arm for
LLMS = ["gemini-3.7-flash", "gemini-3.5-flash", "gpt-5.6-sol-xhigh",
        "claude-opus-5-max", "Qwen3-Coder-480B"]


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
        return None if len(vc) < 2 else (y.astype(str) == vc.index[0]).astype(int).values
    u = pd.unique(y.dropna())
    if len(u) == 2:
        return (y == max(u)).astype(int).values
    return None if len(u) < 2 else (y > y.median()).astype(int).values


def make(learner, y_tr):
    """A model with enough capacity to be worth measuring, class-balanced."""
    if learner == "rf":
        return RandomForestClassifier(
            n_estimators=400, min_samples_leaf=2, max_features="sqrt",
            class_weight="balanced_subsample", random_state=SEED, n_jobs=-1)
    return HistGradientBoostingClassifier(
        max_iter=400, learning_rate=0.06, early_stopping=True,
        validation_fraction=0.15, n_iter_no_change=25,
        class_weight="balanced", random_state=SEED)


def best_threshold(y, p):
    """Threshold maximising F1. Chosen ONLY on training-fold predictions."""
    best, bt = -1.0, 0.5
    for t in np.unique(np.round(np.quantile(p, np.linspace(0.01, 0.99, 99)), 4)):
        f = f1_score(y, (p >= t).astype(int), zero_division=0)
        if f > best:
            best, bt = f, float(t)
    return bt


def evaluate(X, y, groups, learner):
    """5-fold outer CV. Threshold picked inside the training part only."""
    if X.shape[1] == 0 or len(np.unique(y)) < 2:
        return dict(auc=np.nan, f1=np.nan, p=np.nan, r=np.nan)
    if groups is not None and len(np.unique(groups)) >= 5:
        folds = list(GroupKFold(n_splits=5).split(X, y, groups))
    else:
        folds = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(X, y))
    A, F, P, R = [], [], [], []
    for tr, te in folds:
        if len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2:
            continue
        inner = StratifiedKFold(3, shuffle=True, random_state=SEED)
        oof = cross_val_predict(make(learner, y[tr]), X[tr], y[tr], cv=inner,
                                method="predict_proba", n_jobs=1)[:, 1]
        thr = best_threshold(y[tr], oof)
        m = make(learner, y[tr]).fit(X[tr], y[tr])
        pr = m.predict_proba(X[te])[:, 1]
        yh = (pr >= thr).astype(int)
        A.append(roc_auc_score(y[te], pr))
        F.append(f1_score(y[te], yh, zero_division=0))
        P.append(precision_score(y[te], yh, zero_division=0))
        R.append(recall_score(y[te], yh, zero_division=0))
    if not A:
        return dict(auc=np.nan, f1=np.nan, p=np.nan, r=np.nan)
    return dict(auc=float(np.mean(A)), f1=float(np.mean(F)),
                p=float(np.mean(P)), r=float(np.mean(R)))


FLAGS = {}


def build_flag_index(condition=6):
    """Scan responses/ ONCE -> {(model, dataset): majority-flagged columns}.

    The per-lookup version globbed and parsed all 1,009 cached responses on
    every call, and was called once per (model, dataset) -- 60 full passes over
    the cache before a single classifier was fitted.  That, not the nested CV,
    was why the first run produced no output for ten minutes.
    """
    votes = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if r["condition"] != condition or r.get("paraphrase"):
            continue
        sub = next((m for m in LLMS if m in r["model"]), None)
        if sub is None:
            continue
        d, _ = parse(r.get("raw", ""))
        if not d:
            continue
        v = votes[(sub, r["dataset"])]
        for c in d["columns"]:
            if isinstance(c, dict) and c.get("name"):
                v[c["name"]][1] += 1
                if c.get("verdict") == "UNAVAILABLE":
                    v[c["name"]][0] += 1
    return {k: {c for c, (u, n) in cols.items() if n and u * 2 > n}
            for k, cols in votes.items()}


def b3_flags(dataset):
    f = HERE + "baseline10_features.csv"
    if not os.path.exists(f):
        return set()
    d = pd.read_csv(f)
    d = d[d.ds == dataset]
    return set(d.loc[d.cor.abs() >= B3_THRESHOLD, "col"])


def main():
    global FLAGS
    print("indexing cached model responses ...", flush=True)
    FLAGS = build_flag_index()
    got = collections.Counter(k[0] for k in FLAGS)
    print(f"  {len(FLAGS)} (model, dataset) flag sets: {dict(got)}\n", flush=True)
    keys = [a for a in sys.argv[1:] if not a.startswith("-")] or RN.ALLSETS
    rows = []
    for key in keys:
        try:
            b = RN.spec_bundle(key)
            df = frame(key)
        except Exception as e:
            print(f"  {key:<12}SKIP {type(e).__name__}"); continue
        df.columns = [str(c).strip() for c in df.columns]
        name, tgt = b["name"], b["target"]
        if tgt not in df.columns:
            print(f"  {name:<12}SKIP target absent"); continue
        y = binarise(df[tgt])
        if y is None:
            print(f"  {name:<12}SKIP target not binarisable"); continue
        feats = [c for c in b["columns"] if c in df.columns]
        gk = GROUP_KEY.get(name)
        groups = df[gk].values if gk and gk in df.columns else None
        X = encode(df[feats])

        arms = {"ALL": set(),
                "GT": {c for c, p in b["truth"].items() if p},
                "B3": b3_flags(name) & set(feats)}
        for m in LLMS:
            if (m, name) in FLAGS:      # only models that actually ran here
                arms[m] = FLAGS[(m, name)] & set(feats)

        base = float(np.mean(y))
        print(f"\n  {name}  n={len(df)}  feats={len(feats)}  positives={base:.1%}")
        for learner in ("rf", "gb"):
            # An arm is defined by the columns it REMOVES, and the five model
            # arms usually remove the same ones -- on AI4I and HEARTFAIL eight
            # arms collapse to two distinct column sets, and across the corpus
            # 54 of 96 arm-fits (56%) were refitting identical inputs.
            # Everything here is seeded, so identical inputs give identical
            # outputs and one fit can serve every arm that shares a set.
            memo, memo_arm = {}, {}
            for arm, drop in arms.items():
                cols = tuple(c for c in feats if c not in drop)
                if cols in memo:
                    r, note = memo[cols], f"  (= {memo_arm[cols]})"
                else:
                    r = evaluate(X[list(cols)].values, y, groups, learner)
                    memo[cols], memo_arm[cols], note = r, arm, ""
                rows.append(dict(dataset=name, learner=learner, arm=arm,
                                 n_dropped=len(drop), **r))
                print(f"    {learner}  {arm:<20}drop={len(drop):>3}  "
                      f"AUC {r['auc']:.3f}  F1 {r['f1']:.3f}  "
                      f"P {r['p']:.3f}  R {r['r']:.3f}{note}", flush=True)

    d = pd.DataFrame(rows)
    d.to_csv(HERE + "downstream2.csv", index=False)
    print(f"\nwrote downstream2.csv ({len(d)} rows)")


if __name__ == "__main__":
    main()
