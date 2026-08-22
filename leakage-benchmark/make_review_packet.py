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


def labels_only(rs):
    """The 76 labels that took a human decision, and nothing else.

    604 columns are labelled in Strata A and B, but 536 of them are scored
    legitimate by default under §4.6: no source statement, no judgement call.
    The decisions are the 68 leaks and the 8 the §4.7 audit withdrew, each of
    which rests on a quotation somebody had to read and accept.

    Withdrawn first, because those are the audit and the strongest evidence the
    licensing rule bites.  Then the leaks by evidence tier, weakest first: E3
    is where §6.2's adversarial analysis expects disagreement, so it is where a
    reader's attention is worth most.
    """
    seen, out = set(), []
    for r in rs:
        if r["_state"] not in ("ACTIVE", "WITHDRAWN"):
            continue
        raw = str(r.get("dataset") or r.get("dataset_id") or "")
        key = (DS_ALIAS.get(raw, raw.upper()), str(r.get("column")))
        if key in seen:
            continue
        seen.add(key)
        out.append((key, r))

    order = {"E3": 0, "E2": 1, "E1": 2, None: 3, "": 3}
    wd = [x for x in out if x[1]["_state"] == "WITHDRAWN"]
    ac = sorted([x for x in out if x[1]["_state"] == "ACTIVE"],
                key=lambda x: (order.get(x[1].get("evidence_tier"), 3), x[0]))

    print("# The 76 labels that took a decision")
    print()
    print("604 columns are labelled across Strata A and B. 536 of them are")
    print("scored legitimate by default (§4.6): no source statement, no")
    print("judgement call, and precision is reported as a lower bound because")
    print("of it. The remaining 76 each rest on a quotation.")
    print()
    print("For each: does this quotation license this label? The protocol is")
    print("*code the evidence, not the intuition* -- a sentence that reports")
    print("only WHEN a value was recorded is TIMING, even where something")
    print("deeper seems to be going on.")
    print()
    print(f"- **{len(wd)} withdrawn** by the §4.7 audit, listed first")
    print(f"- **{len(ac)} leaks**, weakest evidence tier first")
    tiers = collections.Counter(x[1].get("evidence_tier") or "(none)" for x in ac)
    print("- tiers among the leaks: " +
          ", ".join(f"{k} {v}" for k, v in sorted(tiers.items())))
    print()

    def block(title, items, note=""):
        print(f"\n## {title}\n")
        if note:
            print(note + "\n")
        for (ds, col), r in items:
            print(f"### {ds} · `{col}`")
            print()
            print(f"> {(r.get('quote') or '(no quotation on this record)').strip()}")
            print()
            print(f"- label **{r.get('label','-')}**, mechanism "
                  f"**{r.get('subtype') or '-'}**, tier "
                  f"**{r.get('evidence_tier') or '-'}**")
            if r.get("target"):
                print(f"- target: `{r['target']}`")
            if r.get("source_citation") or r.get("source_locator"):
                print(f"- source: {str(r.get('source_citation') or r.get('source_locator'))[:180]}")
            if r.get("notes"):
                print(f"- note: {str(r['notes'])[:260]}")
            print()

    block(f"Withdrawn by the §4.7 audit ({len(wd)})", wd,
          "Each was a leak in the corpus and is not one now, because its own "
          "documentation places the value at or before the prediction point. "
          "Disagreeing with a removal changes a corpus count.")
    e3 = [x for x in ac if x[1].get("evidence_tier") == "E3"]
    rest = [x for x in ac if x[1].get("evidence_tier") != "E3"]
    block(f"Leaks at tier E3 ({len(e3)}) — weakest evidence", e3,
          "§6.2's adversarial analysis treats these as the arguable ones and "
          "shows the lift margin survives half of them being overturned. If a "
          "reader disagrees anywhere, it is most likely here.")
    block(f"Leaks at tiers E1 and E2 ({len(rest)})", rest,
          "Stronger evidence: a quotation naming the column, or a documented "
          "relationship checked against the values.")
    return 0


def main():
    rs = list(rows())
    frame = corpus_frame()
    for r in rs:
        r["_state"] = state_of(r, frame)

    if "--labels" in sys.argv:
        return labels_only(rs)
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
