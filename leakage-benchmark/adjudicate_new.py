"""Turn anchored candidates into admissible records -- or reject them.

THE PRECISION PROBLEM THIS SOLVES
  harvest_anchored.py accepts a hit when timing wording appears anywhere in a
  +/-200 character window around the column name.  In a reproduced data
  dictionary that window spans several ROWS, so `age` and `education` inherit
  the word "follow-up" from a neighbouring row and look like evidence.  128
  candidates came out, most of them legitimate columns standing next to a leaky
  one.

  A dictionary row is `name  description`.  So the description is what FOLLOWS
  the name, before the next row starts.  This module re-reads the window, keeps
  only the text after the column name and before the next plausible column
  name, and requires the timing marker to fall inside THAT span.

WHAT IT STILL WILL NOT DO
  It will not label a column on our own reading (PROTOCOL 4).  It emits a
  verbatim quote of <=25 words and its locator; a record without a quotable
  licensing phrase is inadmissible and is written to the reject file with the
  reason.  The reject file is part of the attrition reporting (3b), not waste.
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
from screen import PAT
from harvest_anchored import TIMEPAT, norm
import newdata as ND

IN = HERE + "anchored_candidates.jsonl"
OUT = HERE + "records_new.jsonl"
REJ = HERE + "records_rejected.jsonl"

# a description that places the value at/after the outcome.  Deliberately
# narrower than the sieve: the sieve over-collects on purpose, this does not.
LICENSE = re.compile(
    r"(time (?:of|to) (?:observation|event|failure|recurrence|recur|death|relapse)|"
    r"time[- ]to[- ]event|"
    r"(?:period|time) of follow[- ]?up|follow[- ]?up (?:period|time|month|day)|"
    r"duration until|until (?:the )?development|"
    r"(?:development|occurrence|onset) of (?:acute|chronic|extensive|the )|"
    r"if (?:the )?(?:patient )?(?:died|dead|survived|alive)|"
    r"at end of (?:the )?survival|during the (?:follow[- ]?up|survival|observation)|"
    r"only known after|known only after|available only after|"
    r"after the (?:call|outcome|event|diagnosis|discharge|transplant)|"
    r"(?:time|days) (?:taken )?(?:for|to) (?:neutrophil|platelet|.{0,12})?recovery|"
    r"recovery,? defined as|censor)", re.I)

# --------------------------------------------------------------- REASON
# LICENSE above is entirely temporal ("time to event", "follow-up", "only known
# after").  That is the right vocabulary for TIMING and CONSEQUENCE columns and
# it is USELESS for REASON columns, which are not temporal at all: the label is
# assigned BECAUSE of them, at the same moment or earlier.  Running the timing
# sieve over the transfer batch (cardiotocography, cervical cancer, steel plate
# faults, myocardial infarction) admitted ZERO positives -- not because the
# evidence is absent but because the sieve was looking for the wrong thing.
# That is the same blindness the models show, reproduced in our own instrument.
#
# PROTOCOL 2 defines REASON as "records why the outcome was assigned", so the
# licensing phrase must show the LABEL IS DEFINED IN TERMS OF the column.
REASON_LICENSE = re.compile(
    r"(one of (?:the )?(?:two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:fault|defect|class|categor|type|pattern|outcome)|"
    r"mutually exclusive|"
    r"none of the (?:above|other|named|six|seven)|"
    r"remaining (?:fault|defect|class|categor|case)|"
    r"assigned (?:by|from|based on|according to|on the basis of)|"
    r"classified (?:as|into|according to|based on|on the basis of)|"
    r"determined (?:by|from|on the basis of)|"
    r"(?:label|labell?ed|coded|scored) (?:as|according to|based on|from)|"
    r"derived from the|"
    r"defined as (?:the )?(?:absence|presence|any|none)|"
    r"used to (?:assign|define|determine|derive) the (?:class|label|target|"
    r"outcome|diagnosis))", re.I)

# The next column name in a table row ends the current description.  Two row
# styles occur and BOTH must be recognised:
#   "Name  Description"        (whitespace separated)
#   "Name - Description"       (dash separated, used by badawy2025)
# Missing the dash style let `Rbodymass` inherit the licensing phrase from the
# following `ANCrecovery` row, and `Disease` inherit one from running prose.
NEXTNAME = re.compile(
    r"\s(?=[A-Za-z][A-Za-z0-9_]{3,}\s*[-–—]\s+[A-Za-z])"      # Name - Desc
    r"|\s(?=[A-Z][A-Za-z0-9_\-]{3,}\s+[A-Z(])")               # Name  Desc

# A licensing phrase found in running prose rather than a dictionary row is only
# admissible when it is unambiguous about availability on its own.  "time-to-
# event data" in a methods sentence describes a modelling setting, not a column.
PROSE_OK = re.compile(r"(only known after|known only after|available only after|"
                      r"not available at|would not be known)", re.I)


def sentence_with(quote, column):
    """The sentence containing the column name.

    A TIMING licence lives in the column's own dictionary row, so it FOLLOWS the
    name and description_after() is right.  A REASON licence is a statement
    about how the LABEL is defined and naturally PRECEDES the list of columns it
    ranges over: "faults are classified into 7 types, including Pastry,
    Zscratch, ... Bumps and Other".  Looking only after the name misses it
    entirely, which is why the transfer batch admitted nothing.

    Scoping to the sentence keeps this tight: the licence and the column name
    must be in the same sentence, not merely in the same 400-character window.
    """
    parts = re.split(r"(?<=[.;])\s+", quote)
    pat = re.compile(r"(?<![A-Za-z0-9])" +
                     re.escape(column).replace("_", r"[ _\-]?") +
                     r"(?![A-Za-z0-9])", re.I)
    for sent in parts:
        if pat.search(sent):
            return sent
    return ""


def description_after(quote, column):
    """The span that plausibly belongs to THIS column: from just after the name
    to the start of the next row."""
    m = re.search(r"(?<![A-Za-z0-9])" +
                  re.escape(column).replace("_", r"[ _\-]?") +
                  r"(?![A-Za-z0-9])", quote, re.I)
    if not m:
        return ""
    tail = quote[m.end(): m.end() + 200]
    cut = NEXTNAME.search(tail)
    return tail[: cut.start()] if cut else tail


def main():
    cands = [json.loads(l) for l in open(IN)]
    recs, rej = [], []
    for c in cands:
        if c["is_target"]:
            rej.append(dict(c, reject="IS_TARGET -- the label itself is not a "
                                      "label-derived feature"))
            continue
        desc = description_after(c["quote"], c["column"])
        # A dictionary row's description starts right after the name, with a
        # capital, a dash, a digit or a bracket.  One that starts with a comma
        # or a lowercase conjunction is running prose that merely happens to
        # contain the column name -- that is how `Disease` acquired "after the
        # transplant procedure" from a sentence about survival rates.
        midsentence = not re.match(r"^[\s\-–—:()]*[A-Z0-9(]", desc)
        # NEXTNAME already treats "Name - Description" as a dictionary row when
        # finding row boundaries, so a description that opens with that
        # separator IS a row.  DICTISH only recognises rows containing words
        # like "numerical" or "days", which made a clean dash row read as prose
        # and rejected `aGvHDIIIIV` ("- Development of acute graft versus host
        # disease stage III or IV") despite a valid licensing phrase.
        dashrow = bool(re.match(r"^\s*[-–—]\s+[A-Za-z]", desc))
        sent = sentence_with(c["quote"], c["column"])
        lic = LICENSE.search(desc)
        rlic = REASON_LICENSE.search(sent) if sent else None
        lic = lic or rlic
        # a prose hit needs an unambiguous availability phrase, not merely a
        # timing-flavoured word borrowed from a methods sentence
        # the mid-sentence / prose guard applies to TEMPORAL licences only;
        # a REASON licence is expected to be prose and is scoped to its sentence
        if lic and not rlic and (midsentence or not (c.get("dictish") or dashrow)) \
                and not PROSE_OK.search(desc):
            rej.append(dict(c, reject="prose context without an unambiguous "
                                      "availability phrase", own_description=desc[:120]))
            continue
        if not lic:
            why = ("no licensing phrase in the column's own description "
                   "(marker was in a neighbouring row)" if LICENSE.search(c["quote"])
                   else "no licensing phrase")
            rej.append(dict(c, reject=why, own_description=desc[:120]))
            continue
        quote = desc.strip()
        quote = " ".join(quote.split()[:25])
        recs.append(dict(
            dataset_id=c["dataset"], dataset_key=c["dataset_key"],
            column=c["column"], target=None, prediction_point="UNSTATED",
            label="LABEL_DERIVED", subtype=None,
            evidence_tier="E3", source_type="PEER_REVIEWED",
            scope=c["scope"], source_citation=c["source"],
            source_locator=f"p{c['page']}",
            quote=(" ".join(sent.split()[:30]) if rlic else quote),
            licensing_phrase=lic.group(0).lower(),
            licence_kind=("REASON" if rlic else "TEMPORAL"),
            coder="auto-sieve+rule", date="2026-08-13",
            notes="admitted by adjudicate_new.py; quote is the column's own "
                  "dictionary description"))
    with open(OUT, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    with open(REJ, "w") as fh:
        for r in rej:
            fh.write(json.dumps(r) + "\n")

    print(f"{len(cands)} candidates -> {len(recs)} admitted, {len(rej)} rejected\n")
    why = collections.Counter(r["reject"].split(" --")[0].split(" (")[0] for r in rej)
    for k, v in why.most_common():
        print(f"  rejected {v:>4}  {k}")
    print()
    byds = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in recs:
        byds[r["dataset_id"]][r["column"]].add(r["source_citation"])
    print(f"{'dataset':<14}{'positives':>10}   column (sources)")
    tot = 0
    for ds in sorted(byds):
        cols = byds[ds]
        tot += len(cols)
        print(f"  {ds:<12}{len(cols):>10}   " +
              ", ".join(f"{c} ({len(s)})" for c, s in sorted(cols.items())))
    print(f"\n  {tot} documented label-derived columns across {len(byds)} datasets")
    print(f"  wrote {OUT} and {REJ}")


if __name__ == "__main__":
    main()
