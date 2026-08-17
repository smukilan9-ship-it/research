"""Stratum D — positives that need no coder, because a rule decides them.

WHAT THIS STRATUM IS FOR

  Every other positive in this benchmark is licensed by a sentence somebody
  wrote, and §8 concedes that reading a sentence is a judgement.  The referee's
  sharpest question was the obvious consequence: 68 positives, one coder, no
  reliability statistic.

  A record enters Stratum D only if the target is reconstructible from the
  column by a rule that holds on EVERY row.  Agreement 1.000, no threshold to
  choose, no quotation to read.  A second coder cannot disagree with a crosstab,
  so for these records inter-coder reliability is not merely unnecessary, it is
  undefined -- there is nothing to read.

WHY THE LEAK COLUMN'S UCI ROLE IS AN ADMISSION CRITERION

  An exact rule is not sufficient on its own.  UCI marks each column `Target`,
  `Feature`, `ID` or `Other`, and two of the eight exact-rule hits have a leak
  column that the archive ITSELF marks `Target`:

    579 MI            RAZRIV <- LET_IS      (12 targets in the table)
    198 Steel Plates  Other_Faults <- 6 siblings  (7 targets)

  Predicting one designated outcome from another is not the failure this paper
  is about.  MI has twelve targets, so admitting that pair would license 132
  more from one table, and choosing one of them would be arbitrary.  MI is
  therefore EXCLUDED, on the same ground that leaves ChessFraud uncoded in
  §6.4.4: a column that is itself an outcome is not a feature.

  STEEL is kept and the fact is disclosed (§4.x), because there the practitioner
  scenario is real -- the seven fault columns are one seven-class problem in a
  single CSV, a modeller does pick `Other_Faults` as the label, and the other
  six sit in the frame.  The role metadata is a warning that the modeller has
  to go and look for; the paper's whole subject is warnings nobody reads.

  Which makes the roles worth scoring as an instrument in their own right, and
  they are, below: a "check the archive's role fields" rule catches the two
  target-on-target cases and misses every genuine one.

NOTHING HERE IS TAKEN ON TRUST

  The rules are re-verified from the downloaded CSV on every run, row by row.
  A rule that does not hold on 100% of rows is refused, not rounded.
"""
import os, sys, json, collections
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
TREES, FOLDS, SEED = 300, 5, 0

# (uci_id, name, target, leak columns, rule label, rule fn -> bool Series)
SPECS = [
    (887, "NHANES Age Prediction Subset", "age_group", ["RIDAGEYR"],
     "age_group == (RIDAGEYR >= 65)",
     lambda d: _cat(d["age_group"]) == (d["RIDAGEYR"] >= 65).astype(int)),
    (426, "Autism Screening Adult", "class", ["result"],
     "class == (result >= 7), the AQ-10 screening score",
     lambda d: _yes(d["class"]) == (d["result"] >= 7).astype(int)),
    (419, "ASD Screening Data for Children", "class", ["result"],
     "class == (result >= 7), the AQ-10 screening score",
     lambda d: _yes(d["class"]) == (d["result"] >= 7).astype(int)),
    (857, "Chronic Kidney Disease Risk Factor", "class", ["affected"],
     "affected is a 1:1 relabelling of class",
     lambda d: _one_to_one(d["affected"], d["class"])),
    (275, "Bike Sharing", "cnt", ["casual", "registered"],
     "casual + registered == cnt",
     lambda d: (d["casual"] + d["registered"] - d["cnt"]).abs() < 1e-9),
]
# excluded after the role check, with the reason recorded rather than dropped
EXCLUDED = [
    (579, "Myocardial infarction complications", "RAZRIV", "LET_IS",
     "LET_IS is itself a UCI Target; the table has 12"),
    (368, "Facebook Metrics", "Total Interactions", "like/share/comment",
     "no designated outcome — a derivation among features (§6.4.3)"),
]


def _cat(s):
    """Two-level column to 0/1, senior/positive level as 1."""
    v = sorted(pd.unique(s.dropna()))
    return (s == v[-1]).astype(int)


def _yes(s):
    return s.astype(str).str.strip().str.upper().isin(("YES", "1", "TRUE")).astype(int)


def _one_to_one(a, b):
    """True on every row iff each level of `a` maps to exactly one level of b."""
    m = pd.crosstab(a, b)
    ok = (m > 0).sum(axis=1).eq(1).all() and (m > 0).sum(axis=0).eq(1).all()
    return pd.Series(bool(ok), index=a.index if hasattr(a, "index") else None)


def roles(uid):
    p = HERE + f"ucimeta/{uid}.json"
    if not os.path.exists(p):
        return {}
    return {v["name"]: v.get("role")
            for v in (json.load(open(p))["data"].get("variables") or [])}


def f1(X, y):
    if len(np.unique(y)) < 2 or X.shape[1] == 0:
        return float("nan")
    cv = StratifiedKFold(FOLDS, shuffle=True, random_state=SEED)
    return cross_val_score(RandomForestClassifier(TREES, random_state=SEED,
                                                  n_jobs=-1,
                                                  class_weight="balanced"),
                           X, y, cv=cv, scoring="f1").mean()


def numeric(df):
    out = pd.DataFrame(index=df.index)
    for c in df.columns:
        s = df[c]
        if s.dtype == bool:
            out[c] = s.astype(int)
        elif pd.api.types.is_numeric_dtype(s):
            out[c] = s.astype(float)
        else:
            out[c] = pd.factorize(s.astype(str))[0].astype(float)
    return out.fillna(-1.0)


def main():
    print("=" * 88)
    print("STRATUM D — mechanically verified positives (agreement 1.000, no coder)")
    print("=" * 88)
    print("  Rules re-verified row by row from the downloaded CSV on every run.")
    print("  A record is admitted only if its rule holds on 100% of rows AND the")
    print("  leaking column is not itself a UCI-designated Target.\n")
    print(f"  {'uci':>4}  {'dataset':<34}{'rule holds':>11}{'n':>7}"
          f"{'leak role':>11}{'dF1':>8}  status")
    rows = []
    for uid, name, tgt, leaks, label, rule in SPECS:
        p = HERE + f"uci/{uid}/data.csv"
        if not os.path.exists(p):
            print(f"  {uid:>4}  {name[:32]:<34}{'NO DATA':>11}")
            continue
        d = pd.read_csv(p)
        d.columns = [str(c).strip() for c in d.columns]
        miss = [c for c in [tgt] + leaks if c not in d.columns]
        if miss:
            print(f"  {uid:>4}  {name[:32]:<34}  MISSING COLUMNS {miss}")
            continue
        ok = rule(d)
        held = bool(ok.all()) if hasattr(ok, "all") else bool(ok)
        rl = roles(uid)
        leak_roles = {c: rl.get(c) for c in leaks}
        is_target = any(v == "Target" for v in leak_roles.values())

        y = d[tgt]
        yb = _yes(y) if y.dtype == object else (
            _cat(y) if y.nunique() <= 2 else (y > y.median()).astype(int))
        feats = [c for c in d.columns if c != tgt]
        keep = f1(numeric(d[feats]), yb)
        drop = f1(numeric(d[[c for c in feats if c not in leaks]]), yb)
        dl = keep - drop
        status = ("EXCLUDED (leak column is a Target)" if is_target
                  else "admitted" if held else "REFUSED (rule fails)")
        print(f"  {uid:>4}  {name[:32]:<34}{str(held):>11}{len(d):>7}"
              f"{str(list(leak_roles.values())[0]):>11}{dl:>+8.3f}  {status}")
        rows.append((uid, name, tgt, leaks, label, held, len(d), keep, drop, dl,
                     is_target))

    print("\n  excluded before the downstream step, reason recorded:")
    for uid, name, tgt, leak, why in EXCLUDED:
        print(f"  {uid:>4}  {name[:32]:<34}{tgt} <- {leak}")
        print(f"        {why}")

    print("\n  --- keep-all vs leak-removed, RandomForest(300), 5-fold, balanced")
    print(f"  {'dataset':<36}{'keep':>8}{'drop':>8}{'dF1':>9}")
    for uid, name, tgt, leaks, label, held, n, keep, drop, dl, tg in rows:
        if tg:
            continue
        print(f"  {name[:34]:<36}{keep:>8.4f}{drop:>8.4f}{dl:>+9.4f}")

    # ---- the role field scored as an instrument -----------------------------
    # The population must include STEEL, which is in the paper already as
    # Stratum A and is one of the two cases this rule is supposed to catch.
    # Leaving it out counted the rule's successes at 1 while the prose claimed
    # 2, which is the kind of mismatch this project keeps finding in its own
    # prose and must not reproduce in its own code.
    print("\n  --- UCI's own role metadata, scored as a detector")
    allc = [(u, n, t, l) for u, n, t, l, _lab, _fn in SPECS] + \
           [(u, n, t, [l]) for u, n, t, l, _ in EXCLUDED] + \
           [(198, "Steel Plates Faults", "Other_Faults",
             ["Pastry", "Z_Scratch", "K_Scratch", "Stains", "Dirtiness",
              "Bumps"])]
    caught, tot, hits = 0, 0, []
    for uid, name, tgt, leaks in allc:
        rl = roles(uid)
        hit = any(rl.get(c) == "Target" for c in leaks)
        caught += hit
        tot += 1
        if hit:
            hits.append(name.split()[0])
    print(f"  A rule of 'refuse any column the archive marks Target' fires on")
    print(f"  {caught} of the {tot} exact-rule records — {', '.join(hits)} — "
          f"the two target-on-target")
    print(f"  cases, and MISSES every record where the leak is a genuine")
    print(f"  feature — NHANES, both autism screens, CKD. Like §4.4's dictionary")
    print(f"  rule, it is cheap, machine-readable, and mostly does not work.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
