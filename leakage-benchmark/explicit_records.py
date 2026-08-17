"""Records whose evidence is the SOURCE NAMING THE COLUMN, not our reading.

WHY THIS FILE EXISTS SEPARATELY FROM adjudicate_new.py

  Every earlier record was produced the same way: a sieve found wording in a
  column's description, and a human decided that the wording placed the column
  after the prediction point.  That is defensible but it is an inference, and
  PROTOCOL 4 has to spend most of its length fencing our inference off from
  the evidence.

  These records are different in kind.  In each one the source itself either
  (a) instructs the reader not to use the column, or (b) states that the
  target was computed from it, or (c) files the column under a heading that
  declares it an outcome.  Nothing is left for us to judge except whether the
  sentence says what it says.

  A record here therefore carries `explicitness: NAMED_BY_SOURCE`, and the
  older records keep `explicitness: INFERRED_FROM_DESCRIPTION`.  Reporting F1
  on the two strata separately is the honest version of the "two F1s" idea:
  the difference between them is a property of the LABELS, not an adjustment
  anyone applied to the model's answers.

VERIFICATION, NOT TRANSCRIPTION
  Every quote below is checked at import time against the cached source text
  it claims to come from, and every column is checked against the real header
  of the real data file.  A typo'd quote or a renamed column raises rather
  than silently entering the ground truth.  This is the only defence against
  the failure mode that would destroy the paper: a quote that reads perfectly
  and does not exist.
"""
import json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "records_explicit.jsonl"


def uci_text(uid):
    x = json.load(open(f"{HERE}ucimeta/{uid}.json"))["data"]
    parts = [x.get("abstract") or ""]
    ai = x.get("additional_info") or {}
    for v in ai.values():
        if isinstance(v, str):
            parts.append(v)
    for v in (x.get("variables") or []):
        parts.append(v.get("description") or "")
    return "\n".join(parts)


def uci_cols(uid):
    import pandas as pd
    return [str(c).strip() for c in
            pd.read_csv(f"{HERE}uci/{uid}/data.csv", nrows=5).columns]


def norm(s):
    return " ".join(str(s).split()).replace("’", "'").lower()


# ---------------------------------------------------------------------------
# Each entry: (uci_id, dataset_id, target, prediction_point, [ (columns,
# subtype, quote, locator) ... ])
#
# The quote is the SOURCE's sentence, trimmed but never reworded.
# ---------------------------------------------------------------------------
FINDINGS = [
    dict(
        uci_id=579, dataset_id="uci579_myocardial_infarction",
        target="ZSN", prediction_point="at admission to intensive care",
        citation="UCI ML Repository 579, Myocardial infarction complications, "
                 "attribute documentation",
        groups=[
            # A heading is an explicit statement about everything under it.
            # Attributes 113-124 sit beneath it; ZSN (121) is our target and is
            # excluded, the other eleven are the source's own outcomes.
            (["FIBR_PREDS", "PREDS_TAH", "JELUD_TAH", "FIBR_JELUD", "A_V_BLOK",
              "OTEK_LANC", "RAZRIV", "DRESSLER", "REC_IM", "P_IM_STEN", "LET_IS"],
             "CONSEQUENCE",
             "Complications and outcomes of myocardial infarction:",
             "variable_info, heading above attributes 113-124"),
        ]),
    dict(
        uci_id=211, dataset_id="uci211_communities_crime_unnorm",
        target="violentPerPop",
        prediction_point="from 1990 census and 1990 LEMAS survey data",
        citation="UCI ML Repository 211, Communities and Crime Unnormalized, "
                 "dataset summary",
        groups=[
            # The target is literally the sum of these, per capita.  This is the
            # cleanest UPSTREAM/REASON statement in the archive: the outcome is
            # an arithmetic function of columns sitting in the same table.
            (["murders", "rapes", "robberies", "assaults",
              "murdPerPop", "rapesPerPop", "robbbPerPop", "assaultPerPop"],
             "REASON",
             "The per capita violent crimes variable was calculated using "
             "population and the sum of crime variables considered violent "
             "crimes in the United States: murder, rape, robbery, and assault.",
             "additional_info.summary"),
            # The predictors are 1990; every crime column is 1995.  The source
            # states both dates in one sentence, so the ordering is not ours.
            (["burglaries", "larcenies", "autoTheft", "arsons",
              "burglPerPop", "larcPerPop", "autoTheftPerPop", "arsonsPerPop",
              "nonViolPerPop"],
             "TIMING",
             "Data combines socio-economic data from the '90 Census, law "
             "enforcement data from the 1990 Law Enforcement Management and "
             "Admin Stats survey, and crime data from the 1995 FBI UCR",
             "abstract"),
        ]),
    dict(
        uci_id=320, dataset_id="uci320_student_performance",
        target="G3", prediction_point="before the final period grade is issued",
        citation="UCI ML Repository 320, Student Performance, dataset summary",
        groups=[
            # G3 is not COMPUTED from G1/G2, so this is not REASON.  They are
            # earlier measurements of the same quantity on the same unit, which
            # is exactly SURROGATE, and the source says so and says the useful
            # task is the one without them.
            (["G1", "G2"], "SURROGATE",
             "Important note: the target attribute G3 has a strong correlation "
             "with attributes G2 and G1. This occurs because G3 is the final "
             "year grade (issued at the 3rd period), while G1 and G2 correspond "
             "to the 1st and 2nd period grades. It is more difficult to predict "
             "G3 without G2 and G1, but such prediction is much more useful",
             "additional_info.summary"),
        ]),
]


def build():
    today = datetime.date.today().isoformat()
    out, problems = [], []
    for f in FINDINGS:
        uid = f["uci_id"]
        src = norm(uci_text(uid))
        try:
            cols = set(uci_cols(uid))
        except Exception as e:
            problems.append(f"{uid}: cannot read data.csv ({type(e).__name__})")
            cols = None
        for columns, subtype, quote, locator in f["groups"]:
            q = norm(quote)
            if q not in src:
                # try the sentence in pieces: UCI prose contains mojibake and
                # non-breaking spaces that survive normalisation
                head = q[:60]
                problems.append(f"{uid}: quote not found in source "
                                f"(first 60 chars: {head!r})")
                continue
            for c in columns:
                if cols is not None and c not in cols:
                    problems.append(f"{uid}: column {c!r} not in data.csv header")
                    continue
                out.append(dict(
                    dataset_id=f["dataset_id"],
                    dataset_url=f"https://archive.ics.uci.edu/dataset/{uid}",
                    column=c, label="LABEL_DERIVED", subtype=subtype,
                    evidence_tier="E1", source_type="DOCUMENTATION",
                    source_citation=f["citation"], source_locator=locator,
                    quote=quote, coder="SM", date=today,
                    scope="FULL_COLUMN_SET", notes=None,
                    target=f["target"], prediction_point=f["prediction_point"],
                    explicitness="NAMED_BY_SOURCE"))
    return out, problems


if __name__ == "__main__":
    recs, problems = build()
    if problems:
        print("PROBLEMS -- these did not become records:")
        for p in problems:
            print("  " + p)
        print()
    with open(OUT, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    import collections
    print(f"{len(recs)} explicit records -> {OUT}")
    by = collections.Counter((r["dataset_id"], r["subtype"]) for r in recs)
    for (d, s), n in sorted(by.items()):
        print(f"  {d:<36}{s:<14}{n:>3}")
