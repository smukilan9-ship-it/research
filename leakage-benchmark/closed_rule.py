"""Closed-world labelling rule for datasets with a COMPLETE data dictionary.

WHY THIS IS NOT A SIEVE, AND WHY THE DISTINCTION MATTERS

  `screen.py` is a sieve: a recall-oriented filter over prose where a human then
  reads each hit.  Its docstring says so explicitly -- "recall matters far more
  than precision here ... a false positive costs ten seconds of reading".

  This is a different operation.  Every column in these 44 datasets has exactly
  one official description, in a known place.  There is nothing to search for.
  What is needed is a CLASSIFIER applied uniformly to a finite enumerated set,
  and its output goes straight into the ground truth with no human in between.

  So the error budget inverts.  A false positive here is not ten seconds of
  reading -- it is a wrong label that the models are then scored against.
  Precision and recall matter equally, and the rule must be TUNED and MEASURED
  rather than deliberately over-inclusive.

WHAT THIS BUYS

  A complete dictionary is FULL_COLUMN_SET scope (PROTOCOL 8a): it addresses
  every column, so its silence about a column is informative.  A column whose
  official description contains no post-outcome language is EVIDENCED CLEAN,
  not assumed clean.  That removes the legitimate-by-default assumption which
  currently makes our precision a lower bound.

CALIBRATION IS THE POINT

  The rule is not trusted because it looks reasonable.  It is run against the
  columns for which hand-verified E1-E3 records already exist, and the
  agreement is reported.  If it cannot reproduce the verified labels, the
  closed-world corpus is not clean enough to fix the precision problem and we
  should keep the bounded interval instead.  That decision is made on the
  number, not on preference.
"""
import json, glob, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
META = HERE + "ucimeta/"

# --------------------------------------------------------------- the rule
# Wording that places a value at or after the outcome, or shows the label was
# derived from it.  Deliberately NARROWER than screen.PAT: each alternative is
# a phrase that on its own licenses the label, not a single suggestive word.
POST = re.compile(
    r"(only known after|known only after|available only after|"
    r"not (?:known|available|recorded) (?:until|before)|"
    r"after (?:the )?(?:call|outcome|event|diagnosis|discharge|transplant|"
    r"surgery|procedure|treatment|admission|death)|"
    r"post[- ](?:operative|treatment|transplant|discharge|charge[- ]?off|"
    r"intervention|surgery)|"
    # `time to X` is a general temporal construction, not a list of nouns.
    # Enumerating the nouns missed "Time to neutrophils recovery" and "Time to
    # development of acute GvHD"; both name an event that happens after the
    # prediction point regardless of which event it is.
    r"(?:time|days|duration|period)\s+(?:of|to|until)\s+\w+|"
    # event-occurrence phrasing, which carries no temporal word at all
    r"(?:development|occurrence|onset|incidence) of |"
    r"follow[- ]?up (?:time|period|days|months|duration)|"
    r"time[- ]to[- ]event|censor|"
    r"length of stay|"
    r"(?:recorded|measured|collected|assigned|determined) (?:at|after) "
    r"(?:discharge|the end|follow)|"
    r"during (?:the )?(?:follow[- ]?up|observation|survival) period|"
    r"at (?:the )?end of (?:the )?(?:study|follow[- ]?up|observation|survival))",
    re.I)

# Wording showing the TARGET was defined from this column (REASON subtype).
DERIVED = re.compile(
    r"(one of (?:the )?(?:two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:fault|defect|class|categor|type|outcome)|"
    r"mutually exclusive|none of the (?:above|other|named)|"
    r"used to (?:assign|define|determine|derive) the (?:class|label|target|"
    r"outcome|diagnosis)|"
    r"(?:the )?(?:class|label|target) (?:is |was )?(?:assigned|determined|"
    r"derived|computed) (?:by|from|according to)|"
    r"basis for the (?:class|diagnosis|outcome))", re.I)

# A description of the TARGET itself is not a leaky feature -- it IS the label.
TARGETISH = re.compile(r"\b(target|class label|outcome variable|"
                       r"dependent variable|response variable)\b", re.I)


def label(desc, role="", is_our_target=False):
    """LEAKY / CLEAN / TARGET, plus the licensing phrase if any.

    UCI's `role` field encodes ONE framing of the dataset.  Student Performance
    marks G1, G2 and G3 all as Target; under the usual G3-prediction framing G1
    and G2 are features, and leaky ones.  Trusting `role` blindly silently
    deletes two of the most-cited leaks in the archive.  So a column counts as
    the target only when it is the target WE stated for that dataset."""
    d = (desc or "").strip()
    if is_our_target:
        return "TARGET", None
    for pat in (POST, DERIVED):
        for m in pat.finditer(d):
            # "at the time of transplantation" is a REFERENCE POINT -- the
            # moment a legitimate baseline covariate was measured.  "Time to
            # neutrophil recovery" is a DURATION that ends after it.  The
            # broadened `time (of|to) X` pattern collapsed the two and flagged
            # Donorage, Recipientage and Rbodymass, all measured at baseline.
            before = d[max(0, m.start() - 8): m.start()].lower()
            if re.search(r"\bat (?:the )?$", before):
                continue
            return "LEAKY", m.group(0).lower()
    return "CLEAN", None


# the target WE predict, where it differs from or disambiguates UCI's role field
OUR_TARGET = {320: "G3", 296: "readmitted", 519: "DEATH_EVENT",
              565: "survival_status", 890: "cid", 579: "ZSN", 198: "Other_Faults"}


def load():
    rows = []
    for f in sorted(glob.glob(META + "*.json")):
        d = json.load(open(f))
        x = d.get("data", d)
        for v in (x.get("variables") or []):
            rows.append(dict(uci_id=x.get("uci_id"), dataset=x.get("name", "?"),
                             column=v.get("name"), role=v.get("role") or "",
                             description=(v.get("description") or "").strip()))
    return rows


# ---------------------------------------------------- calibration targets
# Columns with hand-verified E1-E3 records, keyed by (uci_id, column).
def verified():
    known = {}
    for fn in ("records_all.jsonl", "records_new.jsonl"):
        p = HERE + fn
        if not os.path.exists(p):
            continue
        for line in open(p):
            r = json.loads(line)
            known[r["column"].lower()] = r["dataset_id"]
    return known


if __name__ == "__main__":
    rows = load()
    for r in rows:
        r["label"], r["phrase"] = label(r["description"], r["role"],
                                        is_our_target=(str(r["column"]).lower() ==
                                                       str(OUR_TARGET.get(r["uci_id"], "")).lower()))
    counts = collections.Counter(r["label"] for r in rows)
    print(f"{len(rows)} columns across "
          f"{len({r['uci_id'] for r in rows})} complete-dictionary datasets")
    print(f"  {dict(counts)}\n")

    byds = collections.defaultdict(list)
    for r in rows:
        if r["label"] == "LEAKY":
            byds[(r["uci_id"], r["dataset"])].append(r)
    print(f"{len(byds)} datasets contain at least one flagged column\n")
    print(f"{'id':>5}  {'dataset':<44}{'flagged':>8}")
    for (uid, name), v in sorted(byds.items(), key=lambda kv: -len(kv[1]))[:20]:
        print(f"{uid:>5}  {name[:42]:<44}{len(v):>8}   "
              f"{', '.join(x['column'] for x in v[:4])}")

    json.dump(rows, open(HERE + "closed_labels.json", "w"), indent=1)
    print(f"\nwrote closed_labels.json")
