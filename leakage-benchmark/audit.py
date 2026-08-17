"""Post-hoc audit of the ground truth: does each quote license its own label?

WHY THIS EXISTS

  The corpus was built quote-first, and I believed that made it safe.  It did
  not.  Asked whether a "prior estimate of the target" is really leakage, I
  went back to the licensing quotes and read them against the labels they were
  supposed to license.  Two failures, one of which is large:

  STUDENT G1/G2.  The licensing quote is:

      "It is more difficult to predict G3 without G2 and G1, but such
       prediction is much more useful."

  That says predicting without them is HARDER AND MORE USEFUL.  It does not
  say the values are unavailable, does not say G3 was computed from them, and
  does not say they are leakage.  G3 is the third-period grade; G1 and G2 are
  the first and second period grades and genuinely precede it.  The label was
  my inference, and it was sitting in Stratum B -- the stratum whose entire
  purpose is that the SOURCE does the labelling.

  SUPPORT2, all fifteen.  Every one was licensed by a single sentence:

      "we rigorously excluded surrogate outcomes and administrative features
       containing future information"

  from a third-party paper using the dataset.  It names no column.  One
  unnamed methodological sentence was doing the work of fifteen records, and
  the dataset's OWN documentation -- which is better evidence and was sitting
  in ucimeta/880.json the whole time -- says several of them are computed on
  study day 3, which is the prediction point.

THE RULE, APPLIED UNIFORMLY

  A column leaves the ground truth when its own documentation places its value
  AT OR BEFORE the prediction point.  Not "when a model missed it", not "when
  it looks arguable" -- when the source says the value is already fixed when
  the prediction is made.

  Applying this rule RAISES every model's score, because the excluded columns
  are disproportionately ones models declined to flag.  That is a reason to
  state the rule before showing the effect, and to report both numbers, which
  is what §4.7 does.  It is not a reason to keep labels the evidence does not
  support.

WHAT IS NOT EXCLUDED, AND WHY

  avtisst survives: "Average TISS score, DAYS 3-25" -- the window runs 22 days
  past the prediction point, so the final value cannot be known at day 3.
  dnr and dnrday survive: "dnr after sadm" is a possible value and dnrday is
  "<0 if before study", so both can take their final value after day 3.
  adlp and adls are documented "measured at day 3" and were ALREADY negatives,
  which is the check that this rule was not invented to fit a conclusion.
"""

# (dataset, column) -> (documentation sentence that excludes it, reading)
EXCLUDED = {
    ("SUPPORT2", "sps"): (
        "SUPPORT physiology score on day 3 (predicted by a model).",
        "Documented as computed ON DAY 3, which is the prediction point. It is "
        "a model output fitted on outcome data, so it is arguably UPSTREAM -- "
        "a mechanism this paper declares and does not measure. Excluded."),
    ("SUPPORT2", "aps"): (
        "APACHE III day 3 physiology score (no coma, imp bun,uout for ph1)",
        "Documented as a DAY 3 score. APACHE III is a published severity index, "
        "not fitted on this dataset's outcomes; it is an ordinary clinical "
        "covariate available at the prediction point. Excluded."),
    ("SUPPORT2", "surv2m"): (
        "SUPPORT model 2-month survival estimate at day 3  (predicted by a model)",
        "Documented as estimated AT DAY 3. A prior model's estimate of the "
        "target, available at the prediction point. Excluded."),
    ("SUPPORT2", "surv6m"): (
        "SUPPORT model 6-month survival estimate at day 3  (predicted by a model)",
        "As surv2m. Excluded."),
    ("SUPPORT2", "prg2m"): (
        "Physician's 2-month survival estimate for patient.",
        "A physician's prior estimate of the target, recorded at enrolment. "
        "Using it makes the model predict the physician rather than the "
        "outcome, which is a real problem -- but it is not a statement about "
        "availability, and no source in the corpus says it is leakage. "
        "Excluded on the same grounds as STUDENT G1/G2."),
    ("SUPPORT2", "prg6m"): (
        "Physician's 6-month survival estimate for patient.",
        "As prg2m. Excluded."),
    ("STUDENT", "G1"): (
        "G3 is the final year grade (issued at the 3rd period), while G1 and "
        "G2 correspond to the 1st and 2nd period grades.",
        "The source's own sentence places G1 BEFORE G3. It says prediction "
        "without it is 'more difficult ... but much more useful' -- a claim "
        "about difficulty and utility, not about admissibility. Excluded."),
    ("STUDENT", "G2"): (
        "G3 is the final year grade (issued at the 3rd period), while G1 and "
        "G2 correspond to the 1st and 2nd period grades.",
        "As G1. Excluded."),
}

# Columns kept, but RE-LICENSED from the dataset's own documentation instead of
# the third-party sentence that named no column.  This is an upgrade in
# evidence, not a change of label.
RELICENSED = {
    ("SUPPORT2", "hospdead"): "Death in hospital",
    ("SUPPORT2", "slos"): "Days from Study Entry to Discharge",
    ("SUPPORT2", "d.time"): "Days of follow-up",
    ("SUPPORT2", "charges"): "Hospital charges",
    ("SUPPORT2", "totcst"): "Total ratio of costs to charges (RCC) cost",
    ("SUPPORT2", "totmcst"): "Total micro cost",
    ("SUPPORT2", "avtisst"): (
        "Average TISS score, days 3-25, where Therapeutic Intervention "
        "Scoring System (TISS) is a method for calculating costs in the "
        "intensive care unit (ICU) and intermediate care unit (IMCU)."),
    ("SUPPORT2", "dnr"): (
        "Whether the patient has a do not rescuscitate (DNR) order or not. "
        "Possible values are dnr after sadm, dnr before sadm, missing, no dnr."),
    ("SUPPORT2", "dnrday"): "Day of DNR order (<0 if before study)",
}


def apply(bundle):
    """Zero the audited columns in a bundle's truth dict, in place.

    Called from runner.spec_bundle so that EVERY consumer -- scoring,
    downstream, baselines, the appendix -- sees the same ground truth. A
    correction applied in one scorer and not another is how the two strata
    ended up with different subtype sources (H13)."""
    n = bundle.get("name")
    for c in list(bundle.get("truth", {})):
        if (n, c) in EXCLUDED:
            bundle["truth"][c] = 0
    return bundle


def report():
    print(f"{len(EXCLUDED)} columns excluded by the audit:")
    for (d, c), (q, why) in EXCLUDED.items():
        print(f"\n  {d}.{c}")
        print(f"    doc:  \"{q}\"")
        print(f"    read: {why}")
    print(f"\n{len(RELICENSED)} columns re-licensed from the dataset's own "
          f"documentation:")
    for (d, c), q in RELICENSED.items():
        print(f"  {d}.{c:<10} \"{q[:80]}\"")


if __name__ == "__main__":
    report()
