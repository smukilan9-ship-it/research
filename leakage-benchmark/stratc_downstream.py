"""Does dropping what a model flags on Stratum C recover honest performance?

WHAT A POSITIVE DELTA MEANS AND WHAT IT DOES NOT

  The quantity measured is F1(keep everything) - F1(drop what was flagged),
  per model and condition, on Stratum C datasets with a usable target.  A
  negative mean says the flags are removing signal rather than leakage.

  So a POSITIVE delta is the expected result and it is not a good score --
  it is the inflation that the leaking column was providing, now removed.  The
  quantity that matters is how close the model's delta lands to the ORACLE
  delta, the one produced by dropping exactly the coded positives.  A model
  that drops the right column and nothing else reproduces the oracle; a model
  that drops half the table beats the oracle on delta while destroying the
  feature set, which is why `n_dropped` is printed beside every delta and no
  ranking is offered on delta alone.

THREE REFERENCE ARMS, ALL NEEDED

  keep-all   every column.  The inflated number a careless practitioner gets.
  oracle     drop the coded positives.  The honest number.
  model      drop what this model flagged UNAVAILABLE at this condition.

  Reporting `model` without `oracle` would make a large delta look like success
  when it may be a model that dropped ten legitimate columns.

WHY THE PROTOCOL IS FIXED HERE RATHER THAN IMPORTED

  The main downstream harness memoises by column set and pools across fifteen
  datasets.  Stratum C is one dataset with eighteen columns; running it through
  that machinery would add a Stratum C row to a table whose denominators the
  paper has already reported.  This computes the same quantity in the same way
  -- RandomForest(300), 5-fold stratified, seed 0, macro F1 on the binarised
  target -- and keeps the result beside the frozen table rather than inside it.
"""
import os, sys, json, glob, collections

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)

import runner as RN
import verify_paper as VP
import stratc_specs as SC

SEED, FOLDS, TREES = 0, 5, 300
# Binarisation of each Stratum C target, chosen from the source's own coding
# and fixed before any model output was scored.  CIRRHOSIS: Status is C
# (censored), CL (censored, transplant) or D (death); death is the event.
#
# Every Stratum C target needs its own rule and NONE of them is obvious, so
# each is written down here rather than inferred from a dtype:
#
#   CIRRHOSIS   Status is C / CL / D.  Death is the event; the two censored
#               states are not.
#   KLAVERJAS   `outcome` is already boolean.
#   BIKESHARING `cnt` is an hourly COUNT, 540 distinct values -- a regression
#               target, and the only way to report it as F1 is to threshold it.
#               Split at the median so the two classes are balanced and the F1
#               is not dominated by a base rate.  This choice is a modelling
#               decision, it was NOT recorded when the 0.9953 / 0.9274 figures
#               were first produced, and it is stated here so the arms are
#               reproducible rather than merely repeatable-by-whoever-ran-them.
BINARISE = {
    "CIRRHOSIS": lambda s: (s.astype(str) == "D").astype(int),
    "KLAVERJAS": lambda s: s.astype(bool).astype(int),
    "BIKESHARING": lambda s: (s.astype(float) > s.astype(float).median()).astype(int),
}

# The rule as printed in the header.  It used to be hardcoded to "=='D'" for
# every dataset, so the Klaverjas and Bike Sharing blocks announced a
# binarisation they do not use -- a label that would have been copied into the
# paper as the stated protocol.  Kept beside BINARISE so the two cannot drift:
# an entry here without one there (or vice versa) raises at import.
RULE = {
    "CIRRHOSIS": "Status == 'D'  (death is the event; both censored states are not)",
    "KLAVERJAS": "outcome is already boolean",
    "BIKESHARING": "cnt > median(cnt)  (hourly count, 540 distinct values -- a "
                   "regression target, thresholded so the classes are balanced)",
}
assert set(RULE) == set(BINARISE), (
    f"RULE and BINARISE disagree: {set(RULE) ^ set(BINARISE)}")


def frame(key):
    m = SC.SPECS[key]
    # The spec carries a `data` path.  This used to read
    # f"uci/{m['uci']}/data.csv", a key the SPECS no longer have -- so this
    # script raised KeyError on its FIRST dataset and had stopped regenerating
    # the deltas it is cited for.  Read what the spec actually declares, so
    # adding a non-UCI Stratum C record cannot silently break it again.
    df = pd.read_csv(HERE + m["data"])
    df.columns = [str(c).strip() for c in df.columns]
    b = RN.spec_bundle(key)
    y = BINARISE[b["name"]](df[b["target"]])
    X = pd.DataFrame({c: numeric(df[c]) for c in b["columns"]})
    return b, X, y


def numeric(s):
    if not pd.api.types.is_numeric_dtype(s):
        return pd.Series(pd.factorize(s.astype(str))[0],
                         index=s.index).astype(float)
    return s.astype(float).fillna(-1.0)


def f1(X, y, cols):
    if not cols:
        return float("nan")
    cv = StratifiedKFold(FOLDS, shuffle=True, random_state=SEED)
    # n_jobs only parallelises the fit.  sklearn draws each tree's seed from the
    # estimator's RandomState sequentially BEFORE dispatching, so a fixed
    # random_state gives bit-identical forests at any n_jobs -- verified here by
    # re-running cirrhosis and diffing against the single-threaded output.  It
    # is needed because Klaverjas2018 is 100,000 rows and eight arms of
    # RandomForest(300) x 5 folds do not finish single-threaded.
    return cross_val_score(RandomForestClassifier(TREES, random_state=SEED,
                                                  n_jobs=-1),
                           X[cols], y, cv=cv, scoring="f1").mean()


def main():
    conds = [int(c) for c in (sys.argv[1] if len(sys.argv) > 1
                              else "1,6").split(",")]
    for key in RN.STRATC:
        b, X, y = frame(key)
        allc = list(X.columns)
        pos = [c for c, v in b["truth"].items() if v]
        base = f1(X, y, allc)
        oracle = f1(X, y, [c for c in allc if c not in pos])
        print(f"\n===== {b['name']}  {len(allc)} columns, {len(pos)} positive "
              f"{pos}, target {b['target']} binarised as {RULE[b['name']]}")
        print(f"  keep-all F1 {base:.3f}    oracle F1 {oracle:.3f}    "
              f"oracle delta {base-oracle:+.3f}")
        print(f"\n  {'model':<40}{'cond':<6}{'dropped':<9}{'F1':<8}"
              f"{'delta':<9}{'vs oracle':<10}")
        models = sorted({json.load(open(f))["model"]
                         for f in glob.glob(HERE + "responses/*.json")})
        rows = []
        for m in models:
            cells = VP.cells_for(m, para=False)
            for (d, cond, seed), got in sorted(cells.items()):
                if d != b["name"] or cond not in conds:
                    continue
                flagged = [c for c in allc
                           if got.get(c, {}).get("verdict") == "UNAVAILABLE"]
                keep = [c for c in allc if c not in flagged]
                s = f1(X, y, keep)
                rows.append((m, cond, len(flagged), s, base - s,
                             (base - s) - (base - oracle)))
        for m, cond, nd, s, dl, vs in sorted(rows, key=lambda r: (r[1], -r[3])):
            print(f"  {m[:38]:<40}C{cond:<5}{nd:<9}{s:<8.3f}{dl:<+9.3f}"
                  f"{vs:<+10.3f}")
        if rows:
            mean = float(np.mean([r[4] for r in rows]))
            npos = sum(1 for r in rows if r[4] > 0)
            print(f"\n  mean delta {mean:+.3f} over {len(rows)} model-condition "
                  f"cells; {npos} of {len(rows)} positive")
            print(f"  a POSITIVE mean is the expected direction -- dropping "
                  f"leakage removes inflation,\n  it does not improve the score.")
            print(f"  mean is {'POSITIVE' if mean > 0 else 'NOT POSITIVE'} "
                  f"on this dataset.")
        print("\n  'dropped' is printed beside every delta on purpose: a model "
              "that drops half the\n  table earns a large delta by destroying "
              "the feature set, not by finding leakage.")


if __name__ == "__main__":
    main()
