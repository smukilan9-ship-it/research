"""Write evidence records for the five datasets coded before the record format
existed.

WHY THESE WERE MISSING
  KOI, DIABETES, LC, COMPAS, AI4I and TITANIC were coded in the first week,
  when the truth for a column was a Python list in harness.py and the
  justification was a comment above it.  Everything coded afterwards went
  through adjudicate_new.py and landed in a JSONL record with a source, a
  locator and a verbatim quotation.  Auditing the corpus for the appendix
  showed 15 positives with no record at all, which is not defensible in a
  paper whose whole claim is that its labels are traceable.

  This backfills them in the same schema.  Two rules were followed:

  1. A `quote` field is written ONLY where the text is on disk and was read.
     AI4I and DIABETES quote the UCI API record; KOI quotes the column
     definition block in the archive's own CSV header.  COMPAS and TITANIC
     get quote=null, because their documentation was not retrievable here
     (hbiostat.org and the ProPublica repository both 404 from this
     environment).  A citation with no quotation is weaker evidence and is
     labelled as such rather than papered over.

  2. Every record carries `data_check`: the pattern in the values that the
     coded mechanism implies, and whether it holds.  verify_paper.py
     recomputes all of these from the raw tables.

  AI4I is the interesting one.  Its UCI record contains an explicit
  derivation statement -- "the 'machine failure' label is set to 1" if any
  failure mode is true -- which the frozen sieve missed and which was
  found by hand.  So four of the 46 main-corpus positives are in fact
  NAMED_BY_SOURCE, and the record says so.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "records_founding.jsonl"

AI4I_Q = ("If at least one of the above failure modes is true, the process "
          "fails and the 'machine failure' label is set to 1.")

R = []


def add(**kw):
    kw.setdefault("coder", "SM")
    kw.setdefault("date", "2026-08-15")
    kw.setdefault("scope", "FULL_COLUMN_SET")
    kw.setdefault("label", "LABEL_DERIVED")
    kw.setdefault("notes", "backfilled from harness.py spec; see "
                           "make_founding_records.py")
    R.append(kw)


# ------------------------------------------------------------------ AI4I
for c in ("TWF", "HDF", "PWF", "OSF"):
    add(dataset_id="AI4I", column=c, target="Machine failure",
        prediction_point="during the process cycle, before the outcome of that "
                         "cycle is known",
        subtype="REASON", evidence_tier="E1", source_type="DOCUMENTATION",
        source_citation="UCI ML Repository 601, AI4I 2020 Predictive "
                        "Maintenance Dataset, additional_info.variable_info",
        source_locator="ucimeta/601.json, additional_info.variable_info, "
                       "final paragraph",
        quote=AI4I_Q,
        explicitness="NAMED_BY_SOURCE",
        data_check=f"every row with {c}=1 has Machine failure=1 (CONFIRMED)",
        notes="Found by hand while re-fetching the 29 UCI records that failed "
              "to download; the frozen sieve does not match this "
              "construction. RNF is named by the same sentence and is NOT "
              "coded, because the data contradict it (1 of 19 RNF rows has "
              "the target set).")

# --------------------------------------------------------------- DIABETES
add(dataset_id="DIABETES", column="discharge_disposition_id", target="readmitted",
    prediction_point="at the point of discharge decision, before the patient "
                     "leaves",
    subtype="CONSEQUENCE", evidence_tier="E2", source_type="DOCUMENTATION",
    source_citation="UCI ML Repository 296, Diabetes 130-US hospitals, "
                    "variables[discharge_disposition_id]",
    source_locator="ucimeta/296.json, variables[].description",
    quote="Integer identifier corresponding to 29 distinct values, for "
          "example, discharged to home, expired, and not available",
    explicitness="INFERRED_FROM_DESCRIPTION",
    data_check="terminal-discharge levels {11,13,14,19,20,21} have a <30-day "
               "readmission rate of 0.0177 against 0.1139 elsewhere",
    notes="MIXED column: 'expired' and hospice levels record the outcome, "
          "'discharged to home' vs 'to a skilled nursing facility' is "
          "legitimately predictive. The spec diabetes_pure isolates the "
          "terminal indicator so the mechanism can be measured alone.")

# ------------------------------------------------------------------- KOI
KOI = {"koi_fpflag_nt": "Not Transit-Like False Positive Flag",
       "koi_fpflag_ss": "Stellar Eclipse False Positive Flag",
       "koi_fpflag_co": "Centroid Offset False Positive Flag",
       "koi_fpflag_ec": "Ephemeris Match Indicates Contamination False "
                        "Positive Flag"}
for c, q in KOI.items():
    add(dataset_id="KOI", column=c, target="koi_disposition",
        prediction_point="when the object is first vetted, before any "
                         "disposition is assigned",
        subtype="REASON", evidence_tier="E2", source_type="DOCUMENTATION",
        source_citation="NASA Exoplanet Archive, Kepler Objects of Interest "
                        "cumulative table, column definition block",
        source_locator="cumulative_2026.08.08 CSV header, "
                       f"'# COLUMN {c}:'",
        quote=f"# COLUMN {c}:  {q}",
        explicitness="INFERRED_FROM_DESCRIPTION",
        data_check="4764 rows carry at least one flag; 4744 of them are "
                   "dispositioned FALSE POSITIVE (0.9958), against 0.0198 "
                   "among rows with no flag set",
        notes="The flags are the vetting decisions that produce the "
              "disposition, so they are inputs to the label, not "
              "measurements of the object.")

# -------------------------------------------------------------- TITANIC
add(dataset_id="TITANIC", column="boat", target="survived",
    prediction_point="as the ship is being evacuated, before the outcome for "
                     "this passenger is known",
    subtype="CONSEQUENCE", evidence_tier="E3", source_type="DOCUMENTATION",
    source_citation="titanic3 data dictionary (Harrell, Vanderbilt "
                    "biostatistics data repository)",
    source_locator="titanic3 variable list, 'boat'",
    quote=None,
    explicitness="INFERRED_FROM_DESCRIPTION",
    data_check="boat is non-null for 486 rows, 477 of whom survived; "
               "boat-non-null == survived agrees on 0.9756 of rows",
    notes="A lifeboat number exists for a passenger because that passenger "
          "was rescued. Quotation unavailable: the dictionary was not "
          "retrievable from this environment, so this rests on the column "
          "name and the data check.")

add(dataset_id="TITANIC", column="body", target="survived",
    prediction_point="as the ship is being evacuated, before the outcome for "
                     "this passenger is known",
    subtype="CONSEQUENCE", evidence_tier="E3", source_type="DOCUMENTATION",
    source_citation="titanic3 data dictionary (Harrell, Vanderbilt "
                    "biostatistics data repository)",
    source_locator="titanic3 variable list, 'body'",
    quote=None,
    explicitness="INFERRED_FROM_DESCRIPTION",
    data_check="body is non-null for 121 rows, 0 of whom survived",
    notes="A body identification number exists only for recovered dead. "
          "Quotation unavailable, as for boat.")

# ---------------------------------------------------------------- COMPAS
COMPAS = {
    "r_charge_degree": "the degree of the charge in the recidivism event",
    "r_charge_desc": "the description of the charge in the recidivism event",
    "r_days_from_arrest": "days from arrest in the recidivism event",
    "r_offense_date": "the date of the offence in the recidivism event",
}
for c, gloss in COMPAS.items():
    add(dataset_id="COMPAS", column=c, target="is_recid",
        prediction_point="at the screening date, before the two-year "
                         "follow-up window opens",
        subtype="CONSEQUENCE", evidence_tier="E3", source_type="DOCUMENTATION",
        source_citation="ProPublica compas-analysis, compas-scores-two-years "
                        "field list",
        source_locator=f"field '{c}'",
        quote=None,
        explicitness="INFERRED_FROM_DESCRIPTION",
        data_check="r_offense_date non-null is exactly is_recid==1 "
                   "(agreement 1.0000); all four r_ fields are non-null only "
                   "on rows with is_recid==1",
        notes=f"The r_ prefix marks {gloss}; the field exists because the "
              "event happened. Quotation unavailable: the ProPublica "
              "repository README was not retrievable from this environment, "
              "so this rests on the field naming and the data check, which is "
              "exact.")


if __name__ == "__main__":
    with open(OUT, "w") as fh:
        for r in R:
            fh.write(json.dumps(r) + "\n")
    print(f"{len(R)} founding records -> {OUT}")
    nq = sum(1 for r in R if r.get("quote"))
    print(f"  with a verbatim quotation: {nq}")
    print(f"  without:                   {len(R)-nq}")
