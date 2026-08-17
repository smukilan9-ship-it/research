"""Benchmark specs for the EXPLICIT-SOURCE datasets.

WHAT MAKES THIS SET DIFFERENT
  In the other twelve datasets a positive is a column whose documentation we
  read as placing it after the prediction point.  Here a positive is a column
  the source itself names -- as an outcome, as a summand of the target, or as
  something the reader is told to predict without.  The ground truth is a
  quotation, and `records_explicit.jsonl` fails loudly if the quotation is not
  in the cached source.

WHY IT IS A CLEAN TRANSFER SET
  None of these three datasets was looked at while C1-C7 were being written,
  and none of them contributed a single word to any prompt.  They were found
  by a scan whose whole selection criterion is "the source already says it",
  which is independent of anything a model does.  So a score here is a
  held-out score without any further argument being needed.

ONE HONEST WEAKNESS, STATED RATHER THAN HIDDEN
  Communities and Crime Unnormalized supplies 17 of the 30 positives, and 9 of
  those rest on a single sentence about data vintage rather than on a
  derivation.  Per-dataset numbers are therefore reported alongside the pooled
  number, because a pooled F1 here is close to a measurement of one dataset.
"""
import json, os, sys, collections
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
REC = HERE + "records_explicit.jsonl"

SPECS = {
    "mi": dict(uci=579, name="MI", target="ZSN",
               dataset_id="uci579_myocardial_infarction",
               pp="at admission to intensive care, before any in-hospital "
                  "complication is observed",
               drop=["ID"]),
    "crime": dict(uci=211, name="CRIME", target="violentPerPop",
                  dataset_id="uci211_communities_crime_unnorm",
                  pp="from the 1990 census and 1990 LEMAS survey, before the "
                     "1995 crime figures are published",
                  drop=["communityname", "fold"]),
    "student": dict(uci=320, name="STUDENT", target="G3",
                    dataset_id="uci320_student_performance",
                    pp="before the third-period final grade is issued",
                    drop=[]),
}


def positives():
    pos = collections.defaultdict(dict)
    if not os.path.exists(REC):
        return pos
    for line in open(REC):
        r = json.loads(line)
        pos[r["dataset_id"]][r["column"]] = r
    return pos


def build(key):
    m = SPECS[key]
    df = pd.read_csv(f"{HERE}uci/{m['uci']}/data.csv")
    df.columns = [str(c).strip() for c in df.columns]
    if m["target"] not in df.columns:
        raise KeyError(f"{m['name']}: target {m['target']!r} not in file")
    cols = [c for c in df.columns if c != m["target"] and c not in m["drop"]]
    pos = positives()[m["dataset_id"]]
    missing = [c for c in pos if c not in cols]
    truth = {c: (c in pos) for c in cols}
    return dict(name=m["name"], columns=cols, truth=truth, target=m["target"],
                prediction_point=m["pp"], description="",
                sample=df[cols].head(5).to_dict("records"),
                sources={c: [pos[c]["source_citation"]] for c in pos if c in cols},
                subtypes={c: pos[c]["subtype"] for c in pos if c in cols},
                missing_positives=missing, n_rows=len(df))


if __name__ == "__main__":
    tc = tp = 0
    for k in SPECS:
        b = build(k)
        n = sum(b["truth"].values())
        tc += len(b["columns"]); tp += n
        st = collections.Counter(b["subtypes"].values())
        print(f"  {b['name']:<9}{b['n_rows']:>7} rows{len(b['columns']):>5} cols"
              f"{n:>4} positive   target={b['target']}")
        print(f"  {'':<9}{dict(st)}")
        print(f"  {'':<9}{', '.join(sorted(b['subtypes']))}")
        if b["missing_positives"]:
            print(f"  {'':<9}!! named by source, ABSENT from file: {b['missing_positives']}")
    print(f"\n  explicit-source transfer set: 3 datasets, {tc} columns, {tp} positives")
