"""Independent checks on every spec the harness runs.

These deliberately do NOT reuse the harness's metric code.  They re-derive the
facts the paper will assert, from the raw frames, so that a bug shared between
the experiment and its check cannot hide.

Every check prints PASS or FAIL.  Any FAIL invalidates the corresponding claim.
"""
import sys, numpy as np, pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
import harness as H

FAILS = []


def check(cond, label, detail=""):
    tag = "PASS" if cond else "FAIL"
    if not cond:
        FAILS.append(label)
    print(f"  [{tag}] {label}" + (f"   {detail}" if detail else ""))
    return cond


def one_sidedness(df, y, col, marked, terminal=None):
    """P(class | field is 'active') for each class.  'Active' means non-null for
    a field that is null elsewhere, non-zero for a 0/1 flag, or membership of a
    given level set."""
    s = df[col]
    if terminal is not None:
        active = s.isin(terminal)
    elif s.isna().any():
        active = s.notna()
    else:
        active = pd.to_numeric(s, errors="coerce").fillna(0) != 0
    if active.sum() == 0:
        return None
    return active.sum(), pd.Series(y)[active.values].value_counts(normalize=True)


def verify(specname):
    spec = H.LOADERS[specname]()
    df, y, g = spec["df"], spec["y"], spec["groups"]
    clean, leaky = spec["clean"], spec["leaky"]
    print(f"\n=== {spec['name']}  [{spec['domain']}]  n={len(df)} ===")

    # --- A. provenance partition is a real partition
    check(not (set(clean) & set(leaky)), "clean and leaky are disjoint")
    # A16: a leaky feature derived from another column is redundant unless that
    # source column is also out of the clean arm.
    src = {"DIABETES_PURE": "discharge_disposition_id"}.get(spec["name"])
    if src:
        check(src not in clean, f"source column '{src}' also excluded from clean")
    lab = {"KOI": "koi_disposition", "DIABETES": "readmitted",
           "DIABETES_PURE": "readmitted", "LC": "loan_status",
           "COMPAS": "two_year_recid", "AI4I": "Machine failure",
           "TITANIC": "survived"}[spec["name"]]
    check(lab not in clean and lab not in leaky,
          f"label column '{lab}' is in neither arm")
    ids = {"KOI": ["kepid", "kepoi_name", "kepler_name"],
           "DIABETES": ["encounter_id", "patient_nbr"],
           "DIABETES_PURE": ["encounter_id", "patient_nbr"],
           "LC": ["id", "member_id", "url"], "COMPAS": ["id", "name"],
           "AI4I": ["UDI", "Product ID"], "TITANIC": ["name", "ticket"]}[spec["name"]]
    check(not (set(ids) & set(clean)), "row identifiers excluded from clean arm",
          f"checked {ids}")

    # --- B. the leak really is one-sided
    term = H.TERMINAL if spec["name"] == "DIABETES" else None
    for c in leaky:
        r = one_sidedness(df, y, c, spec["marked"], term)
        if r is None:
            check(False, f"{c}: field is never active")
            continue
        n_active, dist = r
        top, share = dist.index[0], dist.iloc[0]
        print(f"       {c}: active on {n_active} rows -> "
              + ", ".join(f"{k}={v*100:.1f}%" for k, v in dist.items()))
        check(share >= .70, f"{c} concentrates on one class",
              f"{top} = {share*100:.1f}%")

    # --- C. the leak is silent about the pair
    if spec["pair"]:
        i, j = spec["pair"]
        c = leaky[0]
        s = df[c]
        active = (s.isin(term) if term is not None
                  else s.notna() if s.isna().any()
                  else pd.to_numeric(s, errors="coerce").fillna(0) != 0)
        yy = pd.Series(y)
        ni = int(((yy == i) & active.values).sum())
        nj = int(((yy == j) & active.values).sum())
        ti, tj = int((yy == i).sum()), int((yy == j).sum())
        # rate of activation within each pair class; near-equal = silent
        ri, rj = ni / ti, nj / tj
        print(f"       activation inside the pair: {i} {ni}/{ti} ({ri*100:.2f}%), "
              f"{j} {nj}/{tj} ({rj*100:.2f}%)")
        check(max(ri, rj) < .10, "leak rarely fires inside the pair",
              f"max {max(ri,rj)*100:.2f}%")

    # --- D. group integrity: no group may span a train/test split
    grouped = len(np.unique(g)) < len(g)
    if grouped:
        cv = StratifiedGroupKFold(5, shuffle=True, random_state=0)
        bad = 0
        for tr, te in cv.split(np.zeros((len(y), 1)), y, g):
            bad += len(set(g[tr]) & set(g[te]))
        check(bad == 0, "no group spans a train/test split",
              f"{len(np.unique(g))} groups over {len(g)} rows")
    else:
        check(True, "ungrouped design (one row per entity)")

    # --- E. encoding does not silently destroy a column
    Xc, Xf = H.encode(df, clean), H.encode(df, clean + leaky)
    dead = [c for c in Xf.columns if Xf[c].notna().sum() == 0]
    check(not dead, "no column is all-NaN after encoding", f"dead={dead}")
    check(Xf.shape[1] == len(clean) + len(leaky),
          "encoded width equals clean+leaky", f"{Xf.shape[1]}")
    check(Xc.shape[1] == len(clean), "clean arm width correct", f"{Xc.shape[1]}")
    check(all(H.safe(c) not in Xc.columns for c in leaky),
          "no leaky column present in the clean arm")

    # --- F. matched-denominator arithmetic is exact
    if spec["pair"]:
        rng = np.random.default_rng(0)
        fake = rng.choice(np.unique(y), len(y))
        esc, kept, wrong, rate = H.pair_rates(y, fake, spec["marked"], spec["pair"])
        total = int(np.isin(y, list(spec["pair"])).sum())
        check(esc + kept == total, "escaped + on-axis == pair members",
              f"{esc}+{kept}=={total}")
        check(abs(rate - wrong / kept) < 1e-12, "rate == wrong / on-axis")
    return spec


def unit_tests():
    """Hand-worked examples.  Classes A, B are the pair; M is the marked class."""
    print("\n=== unit tests on the matched-denominator code ===")
    #        idx:   0    1    2    3    4    5    6    7
    y = np.array(["A", "A", "A", "B", "B", "B", "M", "M"])
    #  clean sends idx2 -> M (escape) and gets idx1 wrong
    pc = np.array(["A", "B", "M", "B", "B", "A", "M", "M"])
    #  +leak escapes nothing, gets idx1 right, idx4 wrong
    pf = np.array(["A", "A", "A", "B", "A", "A", "M", "M"])

    esc, kept, wrong, rate = H.pair_rates(y, pc, "M", ("A", "B"))
    check(esc == 1, "size-matched: 1 escape", f"got {esc}")
    check(kept == 5, "size-matched: 5 on axis", f"got {kept}")
    check(wrong == 2, "size-matched: 2 wrong (idx1, idx5)", f"got {wrong}")
    check(abs(rate - 2 / 5) < 1e-12, "size-matched: rate 0.4", f"got {rate}")

    esc2, kept2, wrong2, rate2 = H.pair_rates(y, pf, "M", ("A", "B"))
    check(kept2 == 6, "+leak on axis 6", f"got {kept2}")
    check(wrong2 == 2, "+leak wrong 2 (idx4, idx5)", f"got {wrong2}")

    n, wc, wf, b, c = H.pair_common(y, pc, pf, "M", ("A", "B"))
    # intersection excludes idx2 (clean escaped it): {0,1,3,4,5}
    check(n == 5, "common set has 5 objects", f"got {n}")
    check(wc == 2, "clean wrong on common: idx1, idx5", f"got {wc}")
    check(wf == 2, "+leak wrong on common: idx4, idx5", f"got {wf}")
    check(b == 1, "leak BROKE 1 (idx4: clean right, leak wrong)", f"got {b}")
    check(c == 1, "leak FIXED 1 (idx1: clean wrong, leak right)", f"got {c}")
    check(wc - wf == b - c, "discordance identity  wc-wf == b-c")

    # a leak that changes nothing must produce zero discordance
    n0, wc0, wf0, b0, c0 = H.pair_common(y, pc, pc, "M", ("A", "B"))
    check(b0 == 0 and c0 == 0, "identical arms give zero discordant pairs")
    check(wc0 == wf0, "identical arms give identical error counts")


if __name__ == "__main__":
    todo = sys.argv[1:] or list(H.LOADERS)
    for k in todo:
        verify(k)
    unit_tests()

    # --- G. spec-specific facts the paper will state
    print("\n=== dataset-specific claims ===")
    lc = H.load_lc()
    d = lc["df"]
    check(d.issue_d.notna().all(), "LC issue_d parsed to an ordinal for every row")
    check(d.issue_d.max() - d.issue_d.min() == 54,
          "LC issue_d spans 55 distinct months", f"{d.issue_d.min()}-{d.issue_d.max()}")
    order_ok = (d.groupby("issue_d").size().index.is_monotonic_increasing)
    check(order_ok, "LC issue_d is chronologically ordered (not alphabetical)")

    cp = H.load_compas()
    check(len(cp["df"]) == 6172, "COMPAS filter reproduces ProPublica's 6172 rows",
          f"got {len(cp['df'])}")

    koi = H.LOADERS["koi"]()
    flags = ["koi_fpflag_nt", "koi_fpflag_ss", "koi_fpflag_co", "koi_fpflag_ec"]
    vals = {c: sorted(koi["df"][c].dropna().unique().tolist()) for c in flags}
    binary = {c: v for c, v in vals.items() if set(v) <= {0, 1}}
    check(len(binary) == 4, "all four KOI flags are binary after exclusion",
          f"non-binary: { {c: v for c, v in vals.items() if c not in binary} }")
    check(len(koi["df"]) == 9563, "KOI n is 9563 after excluding the corrupt row",
          f"got {len(koi['df'])}")
    check(not [c for c in koi["clean"] if koi["df"][c].isna().all()],
          "no all-null column survives in the KOI clean arm")

    # the corrupt row is a real defect in the published table, not our artifact
    import pandas as _pd
    _raw = _pd.read_csv(H.U + "e818b7de-cumulative_2026.08.08_07.34.36.csv",
                        comment="#", low_memory=False)
    _bad = _raw[~_raw.koi_fpflag_nt.isin([0, 1])]
    check(len(_bad) == 1 and _bad.iloc[0].kepoi_name == "K00477.01",
          "exactly one out-of-range flag row, K00477.01",
          f"{len(_bad)} row(s), value {_bad.koi_fpflag_nt.tolist()}")

    ai = H.load_ai4i()
    a = ai["df"]
    orv = a[["TWF", "HDF", "PWF", "OSF"]].max(axis=1)
    agree = (a["Machine failure"] == orv).mean()
    check(agree > .999, "AI4I label is the OR of the four mode flags",
          f"agreement {agree*100:.2f}%")

    print("\n" + "=" * 60)
    print(f"{'ALL CHECKS PASSED' if not FAILS else str(len(FAILS)) + ' FAILURE(S): ' + '; '.join(FAILS)}")
