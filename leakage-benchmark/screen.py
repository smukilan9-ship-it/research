"""PROTOCOL §5 step 2 -- narrow a data dictionary to candidates for human review.

This is a SIEVE, not a classifier.  It flags dictionary entries whose wording
places the column at or after the outcome.  A human then reads each hit and
decides whether it licenses a LABEL_DERIVED record, and copies the quote.

Deliberately regex, not a model: the models under evaluation must not have
contributed to the ground truth they are scored against (PROTOCOL §4).

Recall matters far more than precision here -- a false positive costs ten
seconds of reading, a false negative silently corrupts the corpus.  So the
marker list is broad and the output is meant to be over-inclusive.
"""
import csv, re, sys, json

# wording that places a field at or after the outcome
MARKERS = [
    r"\bpost[- ]?charge", r"\bpost[- ]", r"\bafter\b", r"\bfollowing\b",
    r"\bsubsequent", r"\bfollow[- ]?up\b", r"\bcause of death\b",
    r"\bat discharge\b", r"\bdischarge\b", r"\boutcome\b", r"\brecover",
    r"\bcollection", r"\bsettle", r"\bfinal\b", r"\bresulted\b",
    r"\bclosed\b", r"\bterminated\b", r"\bwrite[- ]?off", r"\bcharged[- ]?off",
    r"\bdefault(ed)?\b", r"\bdeceased\b", r"\bexpired\b", r"\bsurviv",
    r"\blast payment\b", r"\bto date\b", r"\bso far\b", r"\bever\b",
]
# wording that signals the dataset's own authors warning you off
WARN = [r"should (not )?be (discarded|used|excluded)", r"only .{0,20}benchmark",
        r"not known before", r"realistic predictive model", r"leakage"]

PAT = re.compile("|".join(MARKERS), re.I)
WPAT = re.compile("|".join(WARN), re.I)


def screen(path, name_col=0, desc_col=1):
    rows, hits = 0, []
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        for i, r in enumerate(csv.reader(fh)):
            if i == 0 or len(r) <= max(name_col, desc_col):
                continue
            col, desc = r[name_col].strip(), r[desc_col].strip()
            if not col:
                continue
            rows += 1
            m = [x.group(0) for x in PAT.finditer(desc)]
            w = WPAT.search(desc)
            if m or w:
                hits.append(dict(column=col, description=desc,
                                 markers=sorted({x.lower() for x in m if x}),
                                 tier_hint="E2" if w else "E1"))
    return rows, hits


if __name__ == "__main__":
    path = sys.argv[1]
    rows, hits = screen(path)
    print(f"dictionary: {path}")
    print(f"  {rows} columns defined -> {len(hits)} flagged for human review "
          f"({100*len(hits)/max(rows,1):.0f}%)\n")
    for h in hits:
        d = h["description"]
        print(f"  {h['column']:<28} [{h['tier_hint']}]")
        print(f"      {d[:110]}{'...' if len(d) > 110 else ''}")
    print(f"\n  -> a human now reads {len(hits)} entries instead of {rows}.")
    print("     Each becomes a LABEL_DERIVED record only if the wording actually")
    print("     places the field at or after the outcome.  The sieve does not decide.")
    json.dump(hits, open(path + ".candidates.json", "w"), indent=1)
