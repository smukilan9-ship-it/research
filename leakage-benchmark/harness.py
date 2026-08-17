"""One protocol, seven specs, five domains.  (v2 -- see AUDIT below.)

Each dataset contains a field that records WHY an instance received one
particular label.  Because it records a reason, it is null or constant across
every instance not given that label.  We ask, identically in every case:

  1. how far does the aggregate metric move when the field is added?
  2. does the field do anything for the boundary it is silent about?
     (matched denominator -- raw pair counts across arms are not comparable)
  3. does a univariate screen flag it?   (values AND missingness both scored)
  4. does a small-subset scan flag it?

AUDIT FIXES over v1 -- each of these changed numbers or could have:

 A1  Subset-scan statistic.  v1 used best-single-class F1, which on an
     imbalanced problem is just the majority-class F1 and is ~constant across
     every subset (AI4I nulls 0.9866, DIABETES nulls 0.7044).  The statistic
     was nearly blind exactly where leakage matters most.  v2 reports macro F1
     as primary and keeps max-class F1 as a secondary for continuity with v1.
 A2  Null subsets were drawn i.i.d. with replacement.  When C(|clean|,k) was
     smaller than n_null the "120 nulls" were a handful of distinct subsets
     repeated (AI4I: 15 distinct; TITANIC: 21).  v2 enumerates exhaustively
     when C(|clean|,k) <= n_null and otherwise samples DISTINCT subsets, and
     reports how many were actually distinct.
 A3  k=1 leaks make the subset scan identical to the univariate screen by
     construction.  v1 reported that as a detector failure.  v2 labels it
     degenerate and declines to score it.
 A4  LC issue_d / earliest_cr_line are "Dec-11" strings; v1 fell through to
     category codes, which order months ALPHABETICALLY.  v2 parses them to a
     month ordinal.
 A5  COMPAS was unfiltered.  The ProPublica convention drops rows whose charge
     date is far from the screening date and rows with is_recid == -1 (missing,
     not negative).  v2 applies it and reports n before/after.
 A6  DIABETES discharge_disposition_id is a MIXED column: the terminal levels
     are label-derived, but "discharged to home" vs "to a skilled nursing
     facility" is legitimately predictive.  v1 attributed the whole column to
     leakage.  v2 adds diabetes_pure, whose leak is the terminal-discharge
     indicator alone, so the mechanism is isolated.
 A7  pair_rates silently assumed exactly three classes (p != marked implies p
     is in the pair).  Now asserted.
 A8  The verdict string collapsed "no degradation" and "significant
     improvement" into one message.  Now three-way.
 A9  Seeds vary the CV partition only; the learner seed is fixed.  Stated
     explicitly rather than left implicit.

  spec           domain            leaky field(s)             marks         pair
  koi            astronomy         koi_fpflag_* (4)           FALSE POSITIVE CAND/CONF
  diabetes       healthcare        discharge_disposition_id   NO            <30 / >30
  diabetes_pure  healthcare        terminal_discharge         NO            <30 / >30
  lc             consumer credit   recoveries, coll_rec_fee   Charged Off   Paid/Current
  compas         criminal justice  r_charge_degree, r_* (4)   recidivated   -- binary
  ai4i           manufacturing     TWF HDF PWF OSF            failure       -- binary
  titanic        historical        boat, body                 survived      -- binary
"""
import os, sys, json, warnings, itertools, numpy as np, pandas as pd
from math import comb

os.environ.setdefault("OMP_NUM_THREADS", "2")
warnings.filterwarnings("ignore")
from sklearn.model_selection import StratifiedKFold, StratifiedGroupKFold
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score, confusion_matrix
from scipy import stats
import lightgbm as lgb

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"

# Where the KOI cumulative table lives.
#
# This was an absolute path into the upload directory of the container this
# project was built in, which meant KOI could not load on any other machine --
# and `09_ENVIRONMENT.md`'s own rule ("scripts resolve paths relative to their
# own file, not the working directory") was broken by exactly one line.  It now
# falls back to the repository directory, which is where `missing_data.py`
# tells a reader to put the file.
#
# The FILENAME stays exact and is deliberately not globbed: NASA re-issues the
# cumulative table under the same name, so a different snapshot is a different
# corpus (MANIFEST.md).  Matching the date is the point, not an inconvenience.
_UPLOADS = "/root/.claude/uploads/1dfa598a-70c3-5cb5-8d7b-ecd921e451d9/"
U = _UPLOADS if os.path.isdir(_UPLOADS) else HERE
NJOBS = 2
SCAN_CAP = 15000          # row ceiling for the subset scan only


# ---------------------------------------------------------------- loaders

def load_koi():
    df = pd.read_csv(U + "e818b7de-cumulative_2026.08.08_07.34.36.csv",
                     comment="#", low_memory=False)
    leaky = ["koi_fpflag_nt", "koi_fpflag_ss", "koi_fpflag_co", "koi_fpflag_ec"]
    # A10: the flags are documented as 0/1.  Exactly one row (K00477.01,
    # kepid 10934674) carries koi_fpflag_nt = 465.  The true value is
    # unrecoverable and the out-of-range value is unique, so a tree can split on
    # it and memorise that single row.  Excluded, and reported as a data-quality
    # finding rather than silently repaired.
    n0 = len(df)
    ok = np.ones(len(df), dtype=bool)
    for c in leaky:
        ok &= df[c].isin([0, 1]).values
    df = df[ok].reset_index(drop=True)
    drop = set(["kepid", "kepoi_name", "kepler_name", "koi_disposition",
                "koi_pdisposition", "koi_score", "koi_tce_delivname"] + leaky)
    return dict(name="KOI", domain="astronomy", df=df,
                y=df.koi_disposition.values, groups=df.kepid.values,
                clean=[c for c in df.columns if c not in drop], leaky=leaky,
                marked="FALSE POSITIVE", pair=("CANDIDATE", "CONFIRMED"),
                note=f"out-of-range flag values excluded: {n0} -> {len(df)} rows")


# discharge_disposition_id levels meaning the patient died or entered hospice.
# A patient in these states cannot generate a readmission, so the field records
# an outcome, not a pre-discharge fact.
TERMINAL = {11, 13, 14, 19, 20, 21}


def _diabetes_frame():
    df = pd.read_csv(HERE + "diabetic.csv", low_memory=False)
    return df.replace("?", np.nan)


def load_diabetes():
    df = _diabetes_frame()
    leaky = ["discharge_disposition_id"]
    drop = set(["encounter_id", "patient_nbr", "readmitted"] + leaky)
    return dict(name="DIABETES", domain="healthcare", df=df,
                y=df.readmitted.values, groups=df.patient_nbr.values,
                clean=[c for c in df.columns if c not in drop], leaky=leaky,
                marked="NO", pair=("<30", ">30"))


def load_diabetes_pure():
    """A6: isolate the label-derived part of discharge_disposition_id.

    The full column mixes legitimate signal (discharged home vs to a nursing
    facility) with a label-derived part (died / hospice).  Here the legitimate
    part stays in the clean arm and only the terminal indicator is the leak."""
    df = _diabetes_frame()
    df["terminal_discharge"] = df.discharge_disposition_id.isin(TERMINAL).astype(int)
    leaky = ["terminal_discharge"]
    # A16: discharge_disposition_id must leave the clean arm too.  It is the
    # column terminal_discharge is DERIVED from, so leaving it in makes the
    # leaky feature redundant and the ablation measures nothing.
    drop = set(["encounter_id", "patient_nbr", "readmitted",
                "discharge_disposition_id"] + leaky)
    return dict(name="DIABETES_PURE", domain="healthcare", df=df,
                y=df.readmitted.values, groups=df.patient_nbr.values,
                clean=[c for c in df.columns if c not in drop], leaky=leaky,
                marked="NO", pair=("<30", ">30"))


def _month_ordinal(s):
    """A4: 'Dec-11' -> months since epoch.  Category codes would sort Apr<Aug<Dec."""
    d = pd.to_datetime(s, format="%b-%y", errors="coerce")
    return d.dt.year * 12 + d.dt.month


def load_lc():
    df = pd.read_csv(HERE + "loan.csv", low_memory=False)
    df = df.copy()
    df["issue_d"] = _month_ordinal(df["issue_d"])
    df["earliest_cr_line"] = _month_ordinal(df["earliest_cr_line"])
    clean = ["loan_amnt", "funded_amnt", "funded_amnt_inv", "term", "int_rate",
             "installment", "grade", "sub_grade", "emp_length", "home_ownership",
             "annual_inc", "verification_status", "issue_d", "purpose",
             "addr_state", "dti", "delinq_2yrs", "earliest_cr_line",
             "inq_last_6mths", "mths_since_last_delinq", "mths_since_last_record",
             "open_acc", "pub_rec", "revol_bal", "revol_util", "total_acc",
             "pub_rec_bankruptcies"]
    return dict(name="LC", domain="consumer credit", df=df,
                y=df.loan_status.values, groups=np.arange(len(df)),
                clean=clean, leaky=["recoveries", "collection_recovery_fee"],
                marked="Charged Off", pair=("Fully Paid", "Current"))


def load_compas():
    """A5: apply the ProPublica selection before doing anything else."""
    raw = pd.read_csv(HERE + "compas.csv", low_memory=False)
    n0 = len(raw)
    df = raw[(raw.days_b_screening_arrest <= 30)
             & (raw.days_b_screening_arrest >= -30)
             & (raw.is_recid != -1)
             & (raw.c_charge_degree != "O")
             & (raw.score_text != "N/A")].reset_index(drop=True)
    clean = ["sex", "age", "age_cat", "race", "juv_fel_count", "juv_misd_count",
             "juv_other_count", "priors_count", "c_charge_degree",
             "c_charge_desc", "days_b_screening_arrest"]
    # r_* describe the recidivism charge, so they exist only if there was one.
    # is_recid and decile_score are excluded from BOTH arms: the first is the
    # label under another name, the second is a third party's model output.
    leaky = ["r_charge_degree", "r_days_from_arrest", "r_offense_date",
             "r_charge_desc"]
    return dict(name="COMPAS", domain="criminal justice", df=df,
                y=df.two_year_recid.astype(str).values, groups=np.arange(len(df)),
                clean=clean, leaky=leaky, marked=None, pair=None,
                note=f"ProPublica filter: {n0} -> {len(df)} rows")


def load_ai4i():
    df = pd.read_csv(HERE + "ai4i2.csv")
    df.columns = [c.strip().lstrip("﻿") for c in df.columns]
    clean = ["Type", "Air temperature [K]", "Process temperature [K]",
             "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]
    # RNF is excluded from BOTH arms: P(failure | RNF=1) = 0.053, so unlike the
    # other four it does not record a reason for the label.
    return dict(name="AI4I", domain="manufacturing", df=df,
                y=df["Machine failure"].astype(str).values,
                groups=np.arange(len(df)),
                clean=clean, leaky=["TWF", "HDF", "PWF", "OSF"],
                marked=None, pair=None)


def load_titanic():
    df = pd.read_csv(HERE + "titanic3.csv")
    return dict(name="TITANIC", domain="historical", df=df,
                y=df.survived.astype(str).values, groups=np.arange(len(df)),
                clean=["pclass", "sex", "age", "sibsp", "parch", "fare", "embarked"],
                leaky=["boat", "body"], marked=None, pair=None)


_RAW_LOADERS = dict(koi=load_koi, diabetes=load_diabetes,
                    diabetes_pure=load_diabetes_pure, lc=load_lc,
                    compas=load_compas, ai4i=load_ai4i, titanic=load_titanic)


def _drop_dead(spec):
    """A11: a column that is entirely null carries no information, but it still
    occupies a slot in the random-subset pool.  Leaving them in lowers the mean
    of the null distribution and inflates the leaky subset's z-score -- a bias
    in our own favour.  Removed from the clean arm before anything is measured."""
    df = spec["df"]
    dead = [c for c in spec["clean"] if df[c].isna().all()]
    if dead:
        spec["clean"] = [c for c in spec["clean"] if c not in dead]
        spec["note"] = ((spec.get("note", "") + "; ") if spec.get("note") else "") \
            + f"dropped {len(dead)} all-null column(s): {dead}"
    return spec


LOADERS = {k: (lambda f=f: _drop_dead(f())) for k, f in _RAW_LOADERS.items()}


# ---------------------------------------------------------------- machinery

def safe(c):
    """LightGBM rejects JSON-special characters in feature names."""
    return "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(c))


def encode(df, cols):
    """Numeric where possible, else integer category codes.

    Codes impose an arbitrary order on nominal levels, which trees can still
    isolate.  Both arms use the identical encoding, so the ablation contrast is
    unaffected by the choice."""
    X = pd.DataFrame(index=df.index)
    for c in cols:
        s = df[c]
        if pd.api.types.is_numeric_dtype(s):
            X[safe(c)] = pd.to_numeric(s, errors="coerce")
        else:
            num = pd.to_numeric(s.astype(str).str.replace(r"[%$,]", "", regex=True),
                                errors="coerce")
            X[safe(c)] = (num if num.notna().mean() > .9
                          else s.astype("category").cat.codes)
    return X


def _cv(X, y, groups, seed, folds):
    grouped = len(np.unique(groups)) < len(groups)
    return ((StratifiedGroupKFold(folds, shuffle=True, random_state=seed) if grouped
             else StratifiedKFold(folds, shuffle=True, random_state=seed))
            .split(X, y, groups))


def oof(X, y, groups, seed, n_est=300, folds=5):
    """A9: `seed` varies the CV partition.  The learner seed is fixed at 42, so
    the reported spread is partition variance, not initialisation variance."""
    p = np.empty(len(X), dtype=object)
    for tr, te in _cv(X, y, groups, seed, folds):
        m = lgb.LGBMClassifier(n_estimators=n_est, learning_rate=.05, num_leaves=31,
                               random_state=42, verbose=-1, n_jobs=NJOBS)
        m.fit(X.iloc[tr], y[tr])
        p[te] = m.predict(X.iloc[te])
    return p


def pair_rates(y, p, marked, pair):
    """Matched denominator.  Of the true members of the pair, how many were
    judged on the pair axis at all, and what fraction of those were exchanged?

    Raw counts are not comparable across arms: a weaker model diverts pair
    members into the marked class, where their errors are booked elsewhere and
    never reach the pair total."""
    classes = set(np.unique(y))
    assert classes == set(pair) | {marked}, \
        f"A7: matched denominator assumes 3 classes, got {classes}"
    inpair = np.isin(y, list(pair))
    escaped = (inpair & (p == marked)).sum()
    kept = inpair & (p != marked)
    wrong = (kept & (p != y)).sum()
    return escaped, kept.sum(), wrong, wrong / max(kept.sum(), 1)


def pair_common(y, p_clean, p_leak, marked, pair):
    """A13.  Matching the denominator's SIZE does not match its COMPOSITION.

    The clean arm diverts many pair members into the marked class; the +leak arm
    does not.  So the +leak arm is scored on a strictly larger set that includes
    exactly the objects the clean model found most marked-class-like -- plausibly
    the hardest ones.  Any difference in rate then confounds the leak's effect
    with a change of population.

    Here both arms are scored on the intersection: pair members that BOTH arms
    placed on the pair axis.  Same objects, same count, paired.  Returns the
    discordant counts for McNemar as well."""
    inpair = np.isin(y, list(pair))
    common = inpair & (p_clean != marked) & (p_leak != marked)
    ok_c, ok_f = (p_clean == y), (p_leak == y)
    return (common.sum(),
            (common & ~ok_c).sum(),                 # clean wrong
            (common & ~ok_f).sum(),                 # +leak wrong
            (common & ok_c & ~ok_f).sum(),          # b: leak broke it
            (common & ~ok_c & ok_f).sum())          # c: leak fixed it


def _auc(v, y):
    best = .5
    for cl in np.unique(y):
        try:
            a = roc_auc_score((y == cl).astype(int), v)
            best = max(best, a, 1 - a)
        except Exception:
            pass
    return best


def univariate(X, y, cols, raw=None):
    """Best one-vs-rest AUC per column, scored two ways and the better kept: the
    column's VALUES and its MISSINGNESS indicator.  A one-sided field carries
    its signal in whether it is populated at all, so a values-only screen scores
    it at chance.  Handing the screen the stronger of the two keeps the baseline
    we are about to beat from being a strawman."""
    out, how = {}, {}
    for c in cols:
        v = pd.to_numeric(X[safe(c)], errors="coerce")
        miss = raw[c].isna() if (raw is not None and c in raw) else v.isna()
        a_miss = _auc(miss.astype(int).values, y) if miss.nunique() > 1 else .5
        a_val = (_auc(v.fillna(v.median()).values, y)
                 if v.notna().sum() >= 10 and v.nunique() >= 2 else .5)
        out[c] = max(a_val, a_miss)
        how[c] = "missingness" if a_miss > a_val else "values"
    return pd.Series(out).sort_values(ascending=False), how


def subset_score(X, y, groups, cols, labels, folds=3):
    """Per-class F1 vector reachable from this subset of columns alone.

    A12.  v1 scored a subset by its best single-class F1; v2's first correction
    used macro F1.  BOTH are blind to a one-sided leak, in opposite directions:

      best-class  under imbalance this is just the majority-class F1, which is
                  near-constant over subsets (AI4I nulls 0.9862 +- 0.001).
      macro       a one-sided leak is superb at ONE class and uninformative
                  about the rest, so averaging over classes buries it -- the
                  KOI flags score macro 0.5705 against a legitimate-subset mean
                  of 0.6036, i.e. BELOW average.

    The vector is returned raw so the caller can standardise each class against
    that class's own null distribution, which is the only comparison under which
    "unusually good at one class" is well defined."""
    sub = X[list(cols)]
    p = np.empty(len(sub), dtype=object)
    for tr, te in _cv(sub, y, groups, 0, folds):
        m = lgb.LGBMClassifier(n_estimators=100, learning_rate=.1, num_leaves=15,
                               random_state=0, verbose=-1, n_jobs=NJOBS)
        m.fit(sub.iloc[tr], y[tr])
        p[te] = m.predict(sub.iloc[te])
    return f1_score(y, p, average=None, labels=labels, zero_division=0)


def null_subsets(obs, k, n_null, rng):
    """A2: exhaustive when the space is small, otherwise DISTINCT samples."""
    total = comb(len(obs), k)
    if total <= n_null:
        return [list(s) for s in itertools.combinations(obs, k)], total, True
    seen, out = set(), []
    while len(out) < n_null:
        s = tuple(sorted(rng.choice(obs, k, replace=False)))
        if s not in seen:
            seen.add(s)
            out.append(list(s))
    return out, total, False


# ---------------------------------------------------------------- protocol

def run(spec, seeds=range(10), n_null=120):
    name, df, y, g = spec["name"], spec["df"], spec["y"], spec["groups"]
    clean, leaky = spec["clean"], spec["leaky"]
    P = lambda *a: print(*a, flush=True)
    res = {"name": name, "domain": spec["domain"], "n": int(len(df))}
    P("=" * 78)
    P(f"{name}  [{spec['domain']}]   n={len(df)}")
    P(f"  classes: {pd.Series(y).value_counts().to_dict()}")
    P(f"  clean={len(clean)}  leaky={leaky}")
    if spec.get("note"):
        P(f"  {spec['note']}")
    P("=" * 78)

    Xc, Xf = encode(df, clean), encode(df, clean + leaky)
    labels = sorted(np.unique(y).tolist())

    accs = {"clean": [], "+leak": []}
    mf1s = {"clean": [], "+leak": []}
    perc = {"clean": [], "+leak": []}
    prs = {"clean": [], "+leak": []}
    cms, common = {}, []
    for s in seeds:
        preds = {}
        for tag, X in (("clean", Xc), ("+leak", Xf)):
            p = preds[tag] = oof(X, y, g, s)
            accs[tag].append(accuracy_score(y, p))
            mf1s[tag].append(f1_score(y, p, average="macro"))
            perc[tag].append(f1_score(y, p, average=None, labels=labels,
                                      zero_division=0))
            if spec["pair"]:
                prs[tag].append(pair_rates(y, p, spec["marked"], spec["pair"]))
            if s == list(seeds)[0]:
                cms[tag] = confusion_matrix(y, p, labels=labels)
        if spec["pair"]:
            common.append(pair_common(y, preds["clean"], preds["+leak"],
                                      spec["marked"], spec["pair"]))

    ns = len(list(seeds))
    P(f"\n1. AGGREGATE METRICS   mean +- sd over {ns} CV partitions "
      f"(learner seed fixed)")
    for tag in ("clean", "+leak"):
        P(f"   {tag:<7} acc {np.mean(accs[tag]):.4f} +-{np.std(accs[tag],ddof=1):.4f}"
          f"   macroF1 {np.mean(mf1s[tag]):.4f} +-{np.std(mf1s[tag],ddof=1):.4f}")
    dacc = np.mean(accs["+leak"]) - np.mean(accs["clean"])
    dmf1 = np.mean(mf1s["+leak"]) - np.mean(mf1s["clean"])
    P(f"   DELTA   acc {dacc:+.4f}   macroF1 {dmf1:+.4f}"
      f"   (macro moves {abs(dmf1)/max(abs(dacc),1e-9):.1f}x further)")
    P("   per-class F1:")
    for li, lab in enumerate(labels):
        a = np.mean([r[li] for r in perc["clean"]])
        b = np.mean([r[li] for r in perc["+leak"]])
        P(f"     {str(lab):<16} {a:.4f} -> {b:.4f}  ({b-a:+.4f})")
    res.update(acc_clean=float(np.mean(accs["clean"])),
               acc_leak=float(np.mean(accs["+leak"])),
               mf1_clean=float(np.mean(mf1s["clean"])),
               mf1_leak=float(np.mean(mf1s["+leak"])),
               d_acc=float(dacc), d_mf1=float(dmf1),
               cm_clean=cms["clean"].tolist(), cm_leak=cms["+leak"].tolist(),
               labels=[str(l) for l in labels],
               perclass_clean=[float(np.mean([r[i] for r in perc["clean"]]))
                               for i in range(len(labels))],
               perclass_leak=[float(np.mean([r[i] for r in perc["+leak"]]))
                              for i in range(len(labels))],
               support=[int((y == l).sum()) for l in labels])

    if spec["pair"]:
        i, j = spec["pair"]
        P(f"\n2. THE {i} <-> {j} BOUNDARY   (the leak is silent here)")
        P(f"   {'':<7}{'escaped':>10}{'on axis':>10}{'wrong':>9}{'RATE':>10}")
        for tag in ("clean", "+leak"):
            a = np.array(prs[tag], dtype=float)
            P(f"   {tag:<7}{a[:,0].mean():>10.1f}{a[:,1].mean():>10.1f}"
              f"{a[:,2].mean():>9.1f}{a[:,3].mean():>10.4f}")
        rc = np.array([r[3] for r in prs["clean"]])
        rf = np.array([r[3] for r in prs["+leak"]])
        wc = np.array([r[2] for r in prs["clean"]], dtype=float)
        wf = np.array([r[2] for r in prs["+leak"]], dtype=float)
        t, pv = stats.ttest_rel(rf, rc)
        d = 100 * (rf - rc)
        se = d.std(ddof=1) / np.sqrt(len(d))
        lo, hi = d.mean() - 1.96 * se, d.mean() + 1.96 * se
        P(f"   raw exchanged counts: {wc.mean():.0f} -> {wf.mean():.0f} "
          f"({100*(wf.mean()/max(wc.mean(),1)-1):+.1f}%   NOT comparable)")
        P(f"   matched error RATE  : {rc.mean():.4f} -> {rf.mean():.4f}  "
          f"({d.mean():+.2f} pts, 95% CI [{lo:+.2f}, {hi:+.2f}], p={pv:.2e})")
        # A8: three-way verdict
        if pv >= .05:
            v = "NO detectable change on the boundary once the denominator is matched"
        elif d.mean() > 0:
            v = f"DEGRADES the boundary by {d.mean():.2f} pts"
        else:
            v = (f"IMPROVES the boundary by {-d.mean():.2f} pts -- the field is "
                 f"NOT purely label-derived, it carries legitimate signal too")
        P(f"   size-matched verdict: {v}")

        # A13: same objects in both arms, not merely the same count
        cm = np.array(common, dtype=float)
        n_c, wc2, wf2, bb, cc = (cm[:, 0], cm[:, 1], cm[:, 2], cm[:, 3], cm[:, 4])
        r_c, r_f = wc2 / n_c, wf2 / n_c
        d2 = 100 * (r_f - r_c)
        se2 = d2.std(ddof=1) / np.sqrt(len(d2))
        lo2, hi2 = d2.mean() - 1.96 * se2, d2.mean() + 1.96 * se2
        t2, pv2 = stats.ttest_rel(r_f, r_c)
        # A14: McNemar PER SEED.  Pooling discordant pairs across seeds would
        # count the same object up to `ns` times as if those were independent
        # trials, which inflates significance.  Report the spread instead.
        mcs = np.array([stats.binomtest(int(min(b_, c_)), int(b_ + c_), .5).pvalue
                        if b_ + c_ else 1.0 for b_, c_ in zip(bb, cc)])
        P(f"\n   COMPOSITION-MATCHED  (objects BOTH arms put on the axis: "
          f"{n_c.mean():.0f} of {int(np.isin(y,[i,j]).sum())})")
        P(f"     error rate  {r_c.mean():.4f} -> {r_f.mean():.4f}  "
          f"({d2.mean():+.2f} pts, 95% CI [{lo2:+.2f}, {hi2:+.2f}], p={pv2:.2e})")
        P(f"     discordant  leak broke {bb.mean():.1f}/seed, "
          f"leak fixed {cc.mean():.1f}/seed")
        # A15: OBJECT-level uncertainty.  The paired t-test above is computed
        # across CV partitions of the SAME rows, so its standard error shrinks
        # with the number of seeds and reports partition consistency, not
        # generalisation.  Adding seeds would drive it to zero for an effect of
        # any size.  The discordant pairs are the object-level evidence.
        dl = (bb - cc) / n_c                       # paired difference in props
        sel = np.sqrt(bb + cc) / n_c               # its standard error
        P(f"     object-level  delta {100*np.median(dl):+.2f} pts  "
          f"95% CI [{100*np.median(dl-1.96*sel):+.2f}, "
          f"{100*np.median(dl+1.96*sel):+.2f}]  (median over partitions)")
        P(f"     McNemar per partition: median p={np.median(mcs):.3f} "
          f"[{mcs.min():.3f}, {mcs.max():.3f}], "
          f"significant in {(mcs<.05).sum()}/{len(mcs)}")
        mc = float(np.median(mcs))
        nsig = int((mcs < .05).sum())
        # PRIMARY verdict rests on the object-level test, not the across-seed one
        if nsig <= len(mcs) // 5:
            v2 = (f"NO reliable effect on the boundary "
                  f"(McNemar significant in only {nsig}/{len(mcs)} partitions)")
        elif d2.mean() > 0:
            v2 = (f"DEGRADES the boundary by {d2.mean():.2f} pts "
                  f"({nsig}/{len(mcs)} partitions)")
        else:
            v2 = (f"IMPROVES the boundary by {-d2.mean():.2f} pts "
                  f"({nsig}/{len(mcs)} partitions)")
        P(f"   VERDICT: {v2}")
        P(f"   (across-partition t-test p={pv2:.2e} measures consistency between "
          f"partitions,\n    not generalisation -- it is not the object-level test)")
        res.update(pair_rate_clean=float(rc.mean()), pair_rate_leak=float(rf.mean()),
                   pair_delta_pts=float(d.mean()), pair_ci=[float(lo), float(hi)],
                   pair_p=float(pv), pair_verdict=v,
                   common_n=float(n_c.mean()), common_rate_clean=float(r_c.mean()),
                   common_rate_leak=float(r_f.mean()),
                   common_delta_pts=float(d2.mean()),
                   common_ci=[float(lo2), float(hi2)], common_p=float(pv2),
                   mcnemar_broke=float(bb.mean()), mcnemar_fixed=float(cc.mean()),
                   mcnemar_p_median=float(mc),
                   mcnemar_sig_partitions=int((mcs < .05).sum()),
                   common_verdict=v2)

    allcols = clean + leaky
    au, how = univariate(Xf, y, allcols, raw=df)
    ranks = {c: list(au.index).index(c) + 1 for c in leaky}
    best_rank = min(ranks.values())
    P(f"\n3. UNIVARIATE SCREEN   best one-vs-rest AUC over {len(allcols)} columns")
    P("   top5: " + ", ".join(f"{c}={au[c]:.3f}" for c in au.index[:5]))
    for c in leaky:
        P(f"   leaky {c:<26} AUC {au[c]:.3f} via {how[c]:<11} rank {ranks[c]}/{len(allcols)}")
    P(f"   caught by a top-3 univariate rule? {'YES' if best_rank <= 3 else 'NO'}")
    res.update(uni_best_rank=int(best_rank), uni_ncols=len(allcols),
               uni_caught=bool(best_rank <= 3),
               uni_auc={c: float(au[c]) for c in leaky},
               uni_how={c: how[c] for c in leaky})

    # ---- subset scan
    k = len(leaky)
    P(f"\n4. SUBSET SCAN   {k}-feature subsets")
    if k == 1:
        # A3: with a single leaky column the scan IS the univariate screen.
        P("   DEGENERATE: a one-column leak cannot be a joint leak.  The scan "
          "reduces\n   to the univariate screen above and is not scored.")
        res.update(scan="degenerate")
    else:
        idx = np.arange(len(Xf))
        if len(idx) > SCAN_CAP:
            rs = np.random.default_rng(7)
            idx = np.sort(rs.choice(idx, SCAN_CAP, replace=False))
            P(f"   [subsampled to {SCAN_CAP} rows for this section only]")
        Xs, ys, gs = Xf.iloc[idx].reset_index(drop=True), y[idx], g[idx]
        obs = [safe(c) for c in clean if safe(c) in Xs.columns]
        fv = subset_score(Xs, ys, gs, [safe(c) for c in leaky], labels)
        subs, total, exhaustive = null_subsets(obs, k, n_null, np.random.default_rng(0))
        nulls = np.array([subset_score(Xs, ys, gs, s, labels) for s in subs])
        P(f"   null subsets: {len(subs)} distinct of {total} possible"
          f"{' (EXHAUSTIVE)' if exhaustive else ' (sampled, no repeats)'}")

        # A12: standardise each class against ITS OWN null, then take the best.
        # SD is floored so a class whose F1 barely varies across subsets cannot
        # manufacture a huge z out of a fourth-decimal difference.
        SD_FLOOR = 0.01
        zs = [(fv[i] - nulls[:, i].mean()) / max(nulls[:, i].std(ddof=1), SD_FLOOR)
              for i in range(len(labels))]
        best = int(np.argmax(zs))
        P("   per-class F1, leaky subset vs null over legitimate subsets:")
        for i, lab in enumerate(labels):
            P(f"     {str(lab):<16} leak {fv[i]:.4f} | null {nulls[:,i].mean():.4f}"
              f" +-{nulls[:,i].std(ddof=1):.4f} max {nulls[:,i].max():.4f}"
              f" | z {zs[i]:+6.2f}{'   <-- best' if i == best else ''}")
        z_star = zs[best]
        det = fv[best] > nulls[:, best].max()
        P(f"   PRIMARY  max per-class z = {z_star:+.2f} on '{labels[best]}'"
          f"   (pct {100*(nulls[:,best]<fv[best]).mean():.1f}%)")
        # the two statistics that do not work, kept so the failure is on record
        mac, mx = fv.mean(), fv.max()
        nm, nx = nulls.mean(1), nulls.max(1)
        P(f"   blind-1  macro F1  leak {mac:.4f} vs null {nm.mean():.4f}"
          f"  z = {(mac-nm.mean())/nm.std(ddof=1):+.2f}")
        P(f"   blind-2  max-class leak {mx:.4f} vs null {nx.mean():.4f}"
          f"  z = {(mx-nx.mean())/nx.std(ddof=1):+.2f}")
        P(f"   DETECTED? {'YES -- beats every legitimate subset on ' + str(labels[best]) if det else 'NO -- inside the legitimate range'}")
        res.update(scan="scored", scan_z=float(z_star), scan_class=str(labels[best]),
                   scan_f1=float(fv[best]),
                   scan_null_mean=float(nulls[:, best].mean()),
                   scan_null_max=float(nulls[:, best].max()),
                   scan_z_macro=float((mac - nm.mean()) / nm.std(ddof=1)),
                   scan_z_maxclass=float((mx - nx.mean()) / nx.std(ddof=1)),
                   scan_ndistinct=len(subs), scan_total=int(total),
                   scan_exhaustive=bool(exhaustive), scan_detected=bool(det))
        np.savez(HERE + f"null_{name}.npz", nulls=nulls, fv=fv,
                 labels=np.array([str(l) for l in labels]))

    with open(HERE + f"res_{name}.json", "w") as fh:
        json.dump(res, fh, indent=1)
    P("")
    return res


if __name__ == "__main__":
    todo = sys.argv[1:] or list(LOADERS)
    for k in todo:
        run(LOADERS[k]())
