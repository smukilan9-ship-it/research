"""Subtype coding for every documented positive, and the stratified score.

WHY THIS IS THE PAPER'S CENTRAL TABLE
  C6 showed that stating the derivation criterion flips KOI from 0/4 to 4/4 with
  precision unchanged, which says the models operationalise leakage as TIMING
  while the ground truth uses TIMING OR DERIVATION.  That claim was inferred
  from two datasets.  PROTOCOL 2 already defines the three subtypes, so coding
  every positive turns the inference into a measurement:

    REASON       records WHY the label was assigned      -- predicted: models miss
    CONSEQUENCE  happened BECAUSE of the outcome         -- predicted: models catch
    TIMING       merely later than the prediction point  -- predicted: models catch

  If C1 recall is high on TIMING/CONSEQUENCE and near zero on REASON, and C6
  lifts REASON specifically, the mechanism is established rather than asserted.

PROVENANCE OF THESE CODES, STATED PLAINLY
  Subtype is SECONDARY coding of columns whose LABEL_DERIVED status is already
  evidenced.  It is not evidence and it does not create positives.  Where a
  source states the subtype (SUPPORT2, LC, BANK in records_all.jsonl) that value
  is used verbatim.  The rest are coded by the analyst, marked `analyst`, with
  the reason recorded so a reader can disagree with one code rather than the
  set.  PROTOCOL 4 forbids our judgment as evidence for the LABEL; it does not
  forbid us classifying an already-evidenced label, provided the coder is named.

CONTESTED CODES
  Two are genuinely arguable and are marked CONTESTED rather than forced:
  `survival_time` and `time` (heart failure) each encode the outcome AND are
  measured later, so REASON/CONSEQUENCE/TIMING are not cleanly separable.
  They are reported separately and excluded from the primary stratification.
"""
import json, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)

# (dataset, column) -> (subtype, coder, reason)
CODES = {
    # --- REASON: the column records why the label was assigned -------------
    ("KOI", "koi_fpflag_nt"): ("REASON", "analyst", "a vetting flag; the FALSE POSITIVE disposition is assigned because it is set"),
    ("KOI", "koi_fpflag_ss"): ("REASON", "analyst", "as koi_fpflag_nt"),
    ("KOI", "koi_fpflag_co"): ("REASON", "analyst", "as koi_fpflag_nt"),
    ("KOI", "koi_fpflag_ec"): ("REASON", "analyst", "as koi_fpflag_nt"),
    ("AI4I", "TWF"): ("REASON", "analyst", "Machine failure is the disjunction of the five mode flags"),
    ("AI4I", "HDF"): ("REASON", "analyst", "as TWF"),
    ("AI4I", "PWF"): ("REASON", "analyst", "as TWF"),
    ("AI4I", "OSF"): ("REASON", "analyst", "as TWF"),
    # Coded REASON here and CONSEQUENCE in its own evidence record until the
    # two were compared -- the corpus disagreed with itself on exactly the
    # boundary S21 measures.  Settled by S2.2's precedence rule: step 1 needs
    # the quotation to say the target was COMPUTED FROM the column, and it says
    # only what the column records; step 2 asks whether the value exists
    # BECAUSE the outcome occurred, and the terminal levels do.  Death causes
    # both the disposition and the impossibility of readmission; nobody read
    # this column to decide `readmitted`.
    ("DIABETES", "discharge_disposition_id"): ("CONSEQUENCE", "analyst", "terminal dispositions (expired, hospice) record the outcome; readmission is impossible for those rows, but the label was not computed from this column"),

    # --- CONSEQUENCE: happened because of the outcome ----------------------
    ("TITANIC", "boat"): ("CONSEQUENCE", "analyst", "a lifeboat number exists because the passenger was rescued"),
    ("TITANIC", "body"): ("CONSEQUENCE", "analyst", "a body number is assigned because the passenger died"),
    ("COMPAS", "r_charge_degree"): ("CONSEQUENCE", "analyst", "describes the re-offence that constitutes the outcome"),
    ("COMPAS", "r_offense_date"): ("CONSEQUENCE", "analyst", "as r_charge_degree"),
    ("COMPAS", "r_charge_desc"): ("CONSEQUENCE", "analyst", "as r_charge_degree"),
    ("COMPAS", "r_days_from_arrest"): ("CONSEQUENCE", "analyst", "as r_charge_degree"),
    ("LC", "recoveries"): ("CONSEQUENCE", "source", "records_all.jsonl, E1"),
    ("LC", "collection_recovery_fee"): ("CONSEQUENCE", "source", "records_all.jsonl, E1"),

    # --- TIMING: later than the prediction point, no causal claim ----------
    ("BANK", "duration"): ("TIMING", "source", "records_all.jsonl, E2"),
    ("BONEMARROW", "ANCrecovery"): ("TIMING", "analyst", "neutrophil recovery is measured after transplantation; not caused by survival"),
    ("BONEMARROW", "PLTrecovery"): ("TIMING", "analyst", "as ANCrecovery"),
    ("BONEMARROW", "time_to_aGvHD_III_IV"): ("TIMING", "analyst", "duration to a post-transplant complication"),

    # --- CONTESTED: encodes the outcome and is also later ------------------
    ("BONEMARROW", "survival_time"): ("CONTESTED", "analyst", "time to event or censoring: encodes the outcome and is measured later"),
    ("HEARTFAIL", "time"): ("CONTESTED", "analyst", "follow-up period; DEATH_EVENT is defined as death within it"),
}

# ---- transfer test (held out from all prompt development) ----------------
# STEEL is structurally identical to AI4I: `Other_Faults` is defined as none of
# the six named fault modes, so each flag is a REASON for the label.
for _c in ("Pastry", "Z_Scratch", "K_Scratch", "Stains", "Dirtiness", "Bumps"):
    CODES[("STEEL", _c)] = ("REASON", "source",
                            "chou2021: faults classified into 7 types, the 7th "
                            "being Other")
CODES[("BONEMARROW", "aGvHDIIIIV")] = ("TIMING", "analyst",
    "acute GvHD develops after transplantation; not caused by survival status")
CODES[("ECHO", "still_alive")] = ("CONSEQUENCE", "analyst",
                                  "records survival status at the end of the "
                                  "observation period; the target is survival "
                                  "to one year")

# SUPPORT2's fifteen are all CONSEQUENCE per records_all.jsonl (source-coded)
SUPPORT2_CONSEQUENCE = ["d.time", "slos", "prg2m", "prg6m", "surv2m", "surv6m",
                        "sps", "aps", "totcst", "totmcst", "charges", "avtisst",
                        "dnr", "dnrday", "hospdead"]
for c in SUPPORT2_CONSEQUENCE:
    CODES[("SUPPORT2", c)] = ("CONSEQUENCE", "source", "records_all.jsonl, E3")


def subtype(ds, col):
    return CODES.get((ds, col), (None, None, None))[0]


def audit():
    """Every documented positive must have a code, or the table has a hole."""
    import runner as RN
    missing, counts = [], collections.Counter()
    for k in RN.ALLSETS:
        try:
            b = RN.spec_bundle(k)
        except Exception:
            continue
        for c, v in b["truth"].items():
            if not v:
                continue
            st = subtype(b["name"], c)
            if st is None:
                missing.append((b["name"], c))
            else:
                counts[st] += 1
    return counts, missing


if __name__ == "__main__":
    counts, missing = audit()
    tot = sum(counts.values())
    print(f"{tot} documented positives coded\n")
    for k in ("REASON", "CONSEQUENCE", "TIMING", "CONTESTED"):
        print(f"  {k:<14}{counts[k]:>4}")
    src = sum(1 for v in CODES.values() if v[1] == "source")
    print(f"\n  {src} coded by a source, {len(CODES)-src} by the analyst")
    if missing:
        print(f"\n  !! {len(missing)} positives WITHOUT a subtype code:")
        for ds, c in missing:
            print(f"     {ds:<12}{c}")
    else:
        print("  no uncoded positives")
