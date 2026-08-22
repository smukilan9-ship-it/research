"""Every licensing quotation in one file, for a human to read and approve.

WHY THIS EXISTS

  The ground truth is source-licensed: a column is a leak because a sentence in
  its documentation says so, and that sentence is stored beside the label.  The
  records carry a `coder` field, and 99 of them say SM.  That field is a claim
  about who read the quotation and decided it licensed the label, and the claim
  should be true before the paper is submitted, not after.

  So this collects every record the corpus rests on into one document, ordered
  for reading rather than for machines: dataset, column, the verbatim
  quotation, the label it was taken to license, the mechanism assigned, the
  evidence tier, and the source.  Withdrawn records are included, because the
  §4.7 audit is the strongest evidence the licensing rule is real and a reader
  should be able to check the eight that failed it.

  THREE STATES, AND THEY ARE NOT THE SAME THING

    ACTIVE     the column is a positive in the corpus the paper scores.
    WITHDRAWN  the record still labels it LABEL_DERIVED, but the corpus no
               longer counts it.  These are §4.7's eight, and the withdrawal
               lives in the loader's positive list rather than in the record,
               so nothing in records*.jsonl says it happened.  That is exactly
               why this file computes the state instead of reading it.
    REJECTED   a screen candidate that was read and never admitted.  Different
               schema, different question: it was never a corpus positive, so
               it was never withdrawn from anything.

  An earlier version of this script printed "WITHDRAWN / REJECTED" for both of
  the last two.  They are different claims about different objects and lumping
  them made §4.7's audit uncheckable from here, which was the one thing the
  packet was supposed to make checkable.

  It reads the same .jsonl files the corpus is built from and cross-references
  the loader's own positive list, so it cannot drift from what the paper
  scores.

    python3 make_review_packet.py > REVIEW_PACKET.md
"""
import glob, json, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
FIELDS = ("quote", "label", "subtype", "evidence_tier", "source_type",
          "source_citation", "source_locator", "prediction_point", "notes",
          "coder", "date")


def rows():
    for f in sorted(glob.glob(HERE + "records*.jsonl")):
        base = os.path.basename(f)
        if "before_devpatch" in base:
            continue                      # superseded copy, not the corpus
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            r["_file"] = base
            yield r


def corpus_frame():
    """Two sets: every SCORED (DATASET, column), and the positives among them.

    Both are needed.  A record can name a column the corpus never scores at
    all -- the record files describe upstream tables in full while the corpus
    scores a chosen subset -- and such a column was never withdrawn from
    anything.  Checking only the positives called five LendingClub payment
    columns WITHDRAWN when they are simply not in LC's 29-column frame.
    """
    sys.path.insert(0, HERE)
    import runner as RN
    scored, pos = set(), set()
    for k in list(RN.ALLSETS) + list(RN.EXPLICIT):
        b = RN.spec_bundle(k)
        nm = b["name"].upper()
        for col, is_pos in b["truth"].items():
            scored.add((nm, str(col)))
            if is_pos:
                pos.add((nm, str(col)))
    return scored, pos


# The record files identify datasets by upstream id; the corpus identifies them
# by short name.  Guessing between them silently misclassified 66 ACTIVE records
# as WITHDRAWN, which is a worse output than no state at all, so the mapping is
# written out rather than inferred.
DS_ALIAS = {
    "uci_880_support2": "SUPPORT2",
    "lending_club_2007_2011": "LC",
    "uci211_communities_crime_unnorm": "CRIME",
    "uci579_myocardial_infarction": "MI",
    "uci320_student_performance": "STUDENT",
    "uci_222_bank_marketing": "BANK",
    "uci878_cirrhosis_survival": "CIRRHOSIS",
    "openml41228_klaverjas2018": "KLAVERJAS",
    "hf_t22000t_bike_sharing_tabular": "BIKESHARING",
}
# Stratum C records describe datasets the corpus never scores as A/B positives,
# so "not a corpus positive" says nothing about them either way.
NOT_IN_AB = {"CIRRHOSIS", "KLAVERJAS", "BIKESHARING"}


def state_of(r, frame):
    """ACTIVE, WITHDRAWN, OUT-OF-FRAME, REJECTED or STRATUM-C."""
    scored, positives = frame
    if "rejected" in r["_file"]:
        return "REJECTED"
    raw = str(r.get("dataset") or r.get("dataset_id") or "")
    ds = DS_ALIAS.get(raw, raw.upper())
    if ds in NOT_IN_AB:
        return "STRATUM-C"
    col = str(r.get("column", ""))
    if (ds, col) in positives:
        return "ACTIVE"
    if (ds, col) not in scored:
        return "OUT-OF-FRAME"
    if str(r.get("label", "")).upper() in ("LABEL_DERIVED", "LEAKY"):
        return "WITHDRAWN"
    return "NOT A POSITIVE"


def main():
    rs = list(rows())
    frame = corpus_frame()
    for r in rs:
        r["_state"] = state_of(r, frame)
    by_ds = collections.defaultdict(list)
    for r in rs:
        by_ds[str(r.get("dataset_id") or r.get("dataset") or "(unknown)")].append(r)

    coders = collections.Counter(r.get("coder", "(unset)") for r in rs)
    import collections as _c
    states = _c.Counter(r["_state"] for r in rs)

    print("# Review packet: every licensing quotation")
    print()
    print("Read each quotation and decide whether it licenses the label beside")
    print("it. This is the `coder` field made checkable: the corpus claims a")
    print("human made these calls, and this file is where that claim is settled.")
    print()
    print(f"- **{len(rs)} records** across {len(by_ds)} datasets")
    for st, n in states.most_common():
        print(f"- **{n} {st}**")
    print("- WITHDRAWN: the record labels the column a leak, the column IS in the")
    print("  scored frame, and the corpus no longer counts it. Those are §4.7's")
    print("  eight. OUT-OF-FRAME: the record describes a column the corpus never")
    print("  scores, so it was never withdrawn from anything. REJECTED: a screen")
    print("  candidate read and never admitted. Three different claims.")
    print("- coder field as it currently stands: " +
          ", ".join(f"`{k}` {v}" for k, v in coders.most_common()))
    print()
    print("Generated by `make_review_packet.py` from the same `records*.jsonl`")
    print("the corpus is scored from, so it cannot drift from the paper.")
    print()

    for ds in sorted(by_ds):
        rr = by_ds[ds]
        print(f"\n## {ds}  ({len(rr)} records)")
        tgt = next((r.get("target") for r in rr if r.get("target")), None)
        if tgt:
            print(f"\n*Target:* `{tgt}`")
        pp = next((r.get("prediction_point") for r in rr if r.get("prediction_point")), None)
        if pp:
            print(f"*Prediction point:* {pp}")
        for r in sorted(rr, key=lambda x: str(x.get("column", ""))):
            col = r.get("column", "(no column)")
            lab = r.get("label", "(no label)")
            sub = r.get("subtype") or "-"
            tier = r.get("evidence_tier") or "-"
            mark = f"{r['_state']}" + (f" — {lab}" if lab and lab != "(no label)" else "")
            print(f"\n### `{col}` — {mark}")
            print(f"\n> {(r.get('quote') or '(no quotation on this record)').strip()}")
            print()
            print(f"- mechanism: **{sub}**   tier: **{tier}**   "
                  f"source: {r.get('source_type') or '-'}")
            cite = r.get("source_citation") or r.get("source_locator")
            if cite:
                print(f"- cited as: {str(cite)[:200]}")
            if r.get("notes"):
                print(f"- note: {str(r['notes'])[:300]}")
            print(f"- record file: `{r['_file']}`   coder field: "
                  f"`{r.get('coder', '(unset)')}`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
