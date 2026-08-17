"""Sanity checks over the 10-dataset corpus.

Each check exists because the corresponding mistake is easy to make, silent, and
would move a headline number.  A check that has never fired is still worth
keeping; a check that fires is worth more than the run it interrupts.
"""
import json, os, sys, collections
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN, harness as H
from subtypes import subtype, CODES

FAIL, WARN = [], []


def check(cond, msg, hard=True):
    if not cond:
        (FAIL if hard else WARN).append(msg)


def main():
    specs = {}
    for k in RN.ALLSETS:
        b = RN.spec_bundle(k)
        specs[k] = b

    print(f"{'dataset':<12}{'rows':>8}{'cols':>6}{'pos':>5}{'prev':>7}  target")
    for k, b in specs.items():
        if k in RN.EXPANSION or k in RN.TRANSFER:
            import newdata as ND, newspecs as NS
            df = ND.NEW[k]()["df"]
        else:
            df = H.LOADERS[k]()["df"]
        npos = sum(b["truth"].values())
        print(f"{b['name']:<12}{len(df):>8}{len(b['columns']):>6}{npos:>5}"
              f"{npos/len(b['columns']):>7.1%}  {b['target']}")

        # C1 the target must not appear as a feature
        check(b["target"] not in b["columns"],
              f"{b['name']}: target {b['target']!r} is also in the feature list")

        # C2 every positive must exist in the distributed file (I5)
        for c, v in b["truth"].items():
            if v:
                check(c in df.columns,
                      f"{b['name']}: positive {c!r} not present in the data file")

        # C3 truth keys and column list must agree exactly
        check(set(b["truth"]) == set(b["columns"]),
              f"{b['name']}: truth keys != column list "
              f"({len(set(b['truth'])^set(b['columns']))} differ)")

        # C4 no duplicate column names (silently collapses a positive)
        check(len(set(b["columns"])) == len(b["columns"]),
              f"{b['name']}: duplicate column names")

        # C5 sample rows must cover the columns the model is shown
        if b.get("sample"):
            miss = set(b["columns"]) - set(b["sample"][0])
            check(not miss, f"{b['name']}: {len(miss)} columns absent from sample rows",
                  hard=False)

        # C6 every positive needs a subtype code
        for c, v in b["truth"].items():
            if v:
                check(subtype(b["name"], c) is not None,
                      f"{b['name']}: positive {c!r} has no subtype code")

        # C7 a positive that is CONSTANT carries no signal and is likely a
        # loader artifact rather than a real leak
        for c, v in b["truth"].items():
            if v and c in df.columns and df[c].nunique(dropna=True) <= 1:
                WARN.append(f"{b['name']}: positive {c!r} is constant "
                            f"({df[c].nunique(dropna=True)} distinct)")

        # C8 a positive perfectly equal to the target is a duplicate label, not
        # a feature -- it would make the task trivial and inflate every score
        if b["target"] in df.columns:
            t = df[b["target"]].astype(str)
            for c, v in b["truth"].items():
                if v and c in df.columns:
                    same = (df[c].astype(str) == t).mean()
                    if same > 0.99:
                        FAIL.append(f"{b['name']}: positive {c!r} is identical to "
                                    f"the target in {same:.1%} of rows")

    # C9 subtype codes must not reference columns that do not exist
    names = {b["name"]: set(b["columns"]) for b in specs.values()}
    for (ds, col) in CODES:
        if ds in names:
            check(col in names[ds],
                  f"subtype code references {ds}.{col} which is not a column",
                  hard=False)

    # C10 the paraphrase map still covers exactly the original six
    import paraphrase as PP
    mapped = {k for k in PP.MAP if not k.startswith("_")}
    orig = {specs[k]["name"] for k in RN.PILOT}
    check(mapped == orig,
          f"paraphrase map covers {sorted(mapped)}, original six are {sorted(orig)}",
          hard=False)

    print()
    for w in WARN:
        print(f"  WARN  {w}")
    for f in FAIL:
        print(f"  FAIL  {f}")
    print(f"\n{len(FAIL)} failure(s), {len(WARN)} warning(s)")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
