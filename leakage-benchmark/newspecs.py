"""Four expansion datasets as benchmark specs, built from evidence records only.

Positives come from records_all.jsonl (harvested earlier) and records_new.jsonl
(this session's PDF harvest).  Nothing here is labelled by us: if a column is
not named by a source, it is legitimate by default, and that default is the
stated limitation in PROTOCOL 7.

WHY THE ORIGINAL SIX ARE UNTOUCHED
  Every result so far -- the condition ladder, the paraphrase control, C6 --
  is computed on those six.  Changing their positive sets would silently
  invalidate all of it.  The four new datasets are added alongside, so old and
  new cells stay comparable and the expansion is visible in the coverage column.

TARGET SELECTION MATTERS AND IS NOT FREE
  SUPPORT2's evidence names `hospdead` as label-derived.  A column cannot be
  both the target and a label-derived feature, so the target must be `death`
  (overall mortality) and `hospdead` becomes a positive.  Picking `hospdead` as
  the target instead would have quietly deleted a documented positive and made
  the dataset look cleaner than it is.  This is the (column, target,
  prediction point) relativity of PROTOCOL 2 biting in practice.

PREDICTION POINTS
  Stated by us, from each dataset's own framing, exactly as for the original
  six.  They are an input to the benchmark, not evidence, and are listed here
  so a reader can disagree with a specific one rather than with all of them.
"""
import json, os, sys, collections
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import newdata as ND

# evidence -> (loader key, benchmark name, target, prediction point)
SPECS = {
    "bank": dict(name="BANK", target="y",
                 pp="before the marketing call is placed"),
    "support2": dict(name="SUPPORT2", target="death",
                     pp="on study day 3, before any subsequent outcome is observed"),
    "bonemarrow": dict(name="BONEMARROW", target="survival_status",
                       pp="at transplantation, before any post-transplant outcome"),
    "heartfail": dict(name="HEARTFAIL", target="DEATH_EVENT",
                      pp="at the index clinical assessment, before the follow-up "
                         "period begins"),
    # ---- transfer test: REASON-subtype, failures never inspected ----------
    "steel": dict(name="STEEL", target="Other_Faults",
                  pp="when the plate is inspected, before a fault type is assigned"),
    "echo": dict(name="ECHO", target="alive_at_1",
                 pp="at the echocardiogram, before the one-year mark"),
}

# which evidence file rows belong to which loader key
EV_DATASET = {
    "uci_880_support2": "support2",
    "uci_222_bank_marketing": "bank",
    "BANK": "bank", "BONEMARROW": "bonemarrow", "HEARTFAIL": "heartfail",
    "STEEL": "steel", "ECHO": "echo",
}


def positives():
    """Documented label-derived columns per loader key, with their sources."""
    pos = collections.defaultdict(lambda: collections.defaultdict(set))
    for fn, keyfield in (("records_all.jsonl", "dataset_id"),
                         ("records_new.jsonl", "dataset_id")):
        path = HERE + fn
        if not os.path.exists(path):
            continue
        for line in open(path):
            r = json.loads(line)
            key = EV_DATASET.get(r[keyfield])
            if not key:
                continue
            src = r.get("source_citation") or r.get("source") or "?"
            pos[key][r["column"]].add(str(src)[:40])
    return pos


def build(key):
    spec = ND.NEW[key]()
    meta = SPECS[key]
    tgt = meta["target"]
    if tgt not in spec["df"].columns:
        raise KeyError(f"{meta['name']}: target {tgt!r} not in file")
    pos = positives()[key]
    df = spec["df"]

    # every column except the target; positives must actually exist (I5)
    cols = [c for c in df.columns if c != tgt]
    missing = [c for c in pos if c not in cols]
    kept = {c: sorted(pos[c]) for c in pos if c in cols}
    leaky = set(kept)
    truth = {c: (c in leaky) for c in cols}

    sample = df[cols].head(5).to_dict("records")
    return dict(name=meta["name"], columns=cols, truth=truth,
                target=tgt, prediction_point=meta["pp"],
                description="", sample=sample,
                sources=kept, missing_positives=missing, n_rows=len(df))


if __name__ == "__main__":
    tot_pos = tot_col = 0
    for k in SPECS:
        try:
            b = build(k)
        except Exception as e:
            print(f"  {k:<12}FAILED {type(e).__name__}: {str(e)[:80]}")
            continue
        npos = sum(b["truth"].values())
        tot_pos += npos
        tot_col += len(b["columns"])
        multi = [c for c, s in b["sources"].items() if len(s) >= 2]
        print(f"  {b['name']:<11}{b['n_rows']:>7} rows{len(b['columns']):>4} cols"
              f"{npos:>4} positive   target={b['target']}")
        print(f"  {'':<11}positives: {', '.join(sorted(b['sources']))}")
        if multi:
            print(f"  {'':<11}corroborated by >=2 sources: {', '.join(multi)}")
        if b["missing_positives"]:
            print(f"  {'':<11}!! named by a source but ABSENT from the file "
                  f"(I5 violation, dropped): {b['missing_positives']}")
    print(f"\n  4 new datasets: {tot_col} columns, {tot_pos} documented positives")
    print(f"  original 6:     150 columns,  17 documented positives")
    print(f"  COMBINED:       {tot_col+150} columns, {tot_pos+17} positives, 10 datasets")
