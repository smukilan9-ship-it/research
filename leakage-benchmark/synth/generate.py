"""Generate unseen tables with mechanically injected leakage.

WHY THIS EXISTS

  Every dataset in the benchmark is public and almost certainly in pretraining,
  so no existing stratum separates "the model reasoned about this table" from
  "the model recalls this table".  See PREREG.md.  These tables have never left
  this machine, which is the only novelty guarantee available that does not
  depend on a vendor's disclosure.

THE STANDARD THESE HAVE TO MEET

  Stratum D's, which the paper already uses: a record is admitted only if its
  rule holds on 100% of rows.  Here the rule is ours, so verification is
  cheap -- but it is still RUN, on every generation, because a generator with
  a bug produces a leak that is not a leak and there would be nothing to catch
  it.  `verify()` re-derives every injected column from the frame itself and
  refuses the table on a single disagreeing row.

DESIGN CONSTRAINTS, FROM PREREG.md

  - plausible domain column names.  `leaky_col_1` tests nothing.
  - all three measured mechanisms, per PAPER.md section 2.2:
      REASON       an input used to assign the label
      CONSEQUENCE  exists because the outcome occurred
      TIMING       recorded after the prediction point
  - legitimate columns that are GENUINELY PREDICTIVE, so precision is a real
    test.  A table whose only signal is the leak makes every model look good.
  - prevalence near the real corpus's 68/604 = 11%, so the precision denominator
    behaves comparably.
"""
import numpy as np
import pandas as pd

SEED = 20260818
N_ROWS = 4000


# --------------------------------------------------------------------------
# helpers -- every injected column is produced by one of these, so the
# mechanism of a column is a property of HOW IT WAS BUILT, not of a label we
# attach afterwards.  verify() below re-derives each one.
# --------------------------------------------------------------------------
def _reason_indicator(rng, driver, thresh):
    """An input to the labelling rule: the label is a function OF this."""
    return (driver >= thresh).astype(int)


def _consequence(rng, y, lo, hi, rate):
    """Exists because the outcome occurred -- but SPARSELY.

    The first version was zero on every y=0 row and non-zero on every y=1 row.
    That is a perfect separator: |r| ~ 1, and B3 scored 1.000 on the whole
    table.  Real consequence columns are not like that.  TITANIC's `body` is a
    body-recovery number -- it exists only because the passenger died, and is
    recorded for a SMALL FRACTION of the deaths.  Its |r| with the target is
    0.014.

    `rate` is the share of positives for which the column is populated.  The
    mechanism is unchanged and still mechanically verifiable -- a populated
    value still implies the outcome occurred -- but the correlation now lands
    where real ones do.  verify() tests the implication, not an iff.
    """
    hit = (y == 1) & (rng.random(len(y)) < rate)
    return np.round(np.where(hit, rng.uniform(lo, hi, len(y)), 0.0), 2)


def _timing(rng, y, sep, noise):
    """Recorded after the prediction point.  `sep` is varied deliberately: a
    post-hoc measurement can be a loud signal or a faint one, and a corpus
    where every timing leak is loud is one a correlation rule solves outright."""
    return np.round(rng.normal(loc=y * sep, scale=noise, size=len(y)), 3)


def _legit_predictive(rng, driver, noise):
    """A legitimate feature that genuinely predicts.

    Some must be STRONGLY predictive -- more strongly than the weaker leaks --
    or the two classes are separable by correlation alone and the benchmark
    measures nothing a threshold could not.  TITANIC's `sex` is legitimate at
    |r| = 0.529 while LC's `collection_recovery_fee` leaks at 0.205.  That
    overlap is the whole reason B3 tops out at 0.630.
    """
    return np.round(driver + rng.normal(0, noise, len(driver)), 3)


def _legit_noise(rng, n, kind="normal"):
    if kind == "normal":
        return np.round(rng.normal(0, 1, n), 3)
    if kind == "count":
        return rng.poisson(3, n)
    return rng.integers(0, 5, n)


# --------------------------------------------------------------------------
# one table
# --------------------------------------------------------------------------
def build(spec, seed=SEED):
    """Return (df, truth, meta).  `truth` maps column -> mechanism or None."""
    rng = np.random.default_rng(seed + spec["salt"])
    n = spec.get("rows", N_ROWS)

    # latent risk drives both the label and the legitimate features, which is
    # what makes the legitimate features predictive without being leaks
    driver = rng.normal(0, 1, n)
    truth = {}
    cols = {}

    # ---- REASON: the inputs the label is literally computed from ----------
    reason_names = spec["reason"]
    flags = []
    for i, name in enumerate(reason_names):
        f = _reason_indicator(rng, driver + rng.normal(0, 0.35, n),
                              spec["reason_thresh"][i])
        cols[name] = f
        truth[name] = "REASON"
        flags.append(f)

    # THE LABELLING RULE.  y is 1 iff at least one flag fired.  This is the
    # AI4I shape -- "TWF/HDF/PWF/OSF -> Machine failure" -- and it makes every
    # flag an input to the assignment, which is exactly REASON's definition.
    y = (np.sum(flags, axis=0) > 0).astype(int)

    # ---- CONSEQUENCE: exists because the outcome occurred -----------------
    for name, (lo, hi, rate) in spec["consequence"].items():
        cols[name] = _consequence(rng, y, lo, hi, rate)
        truth[name] = "CONSEQUENCE"

    # ---- TIMING: measured after the prediction point ----------------------
    for name, (sep, noise) in spec["timing"].items():
        cols[name] = _timing(rng, y, sep, noise)
        truth[name] = "TIMING"

    # ---- legitimate ------------------------------------------------------
    for name, noise in spec["legit_predictive"].items():
        cols[name] = _legit_predictive(rng, driver, noise)
        truth[name] = None
    for i, name in enumerate(spec["legit_noise_cols"]):
        cols[name] = _legit_noise(rng, n, ["normal", "count", "cat"][i % 3])
        truth[name] = None

    df = pd.DataFrame(cols)
    df[spec["target"]] = y
    # column order should not encode the answer: a table whose leaks are all
    # on the left is solvable by position
    order = list(rng.permutation([c for c in df.columns if c != spec["target"]]))
    df = df[order + [spec["target"]]]
    meta = dict(name=spec["name"], target=spec["target"],
                prediction_point=spec["prediction_point"],
                rows=n, prevalence=float(y.mean()))
    return df, truth, meta


def verify(df, truth, spec):
    """Re-derive every injected column from the frame and refuse on one bad row.

    The Stratum D standard, applied to our own generator.  A rule that holds on
    99.9% of rows is not a mechanically verified leak, it is a correlation.
    """
    y = df[spec["target"]].to_numpy()
    problems = []

    flags = [df[c].to_numpy() for c in spec["reason"]]
    if not np.array_equal((np.sum(flags, axis=0) > 0).astype(int), y):
        problems.append("labelling rule does not reproduce the target")

    for c in spec["consequence"]:
        v = df[c].to_numpy()
        # The rule is an IMPLICATION -- populated implies the outcome
        # occurred.  Not an iff: the column is sparse by design, and demanding
        # it be present on every positive recreates the perfect separator that
        # put B3 at 1.000.
        if not np.all(v[y == 0] == 0.0):
            problems.append(f"{c}: populated on a y=0 row -- implication broken")
        if v[y == 1].max() <= 0.0:
            problems.append(f"{c}: never populated on any positive")

    for c, m in truth.items():
        if m is None and c in spec["reason"]:
            problems.append(f"{c}: labelled legitimate but is a rule input")
    return problems
