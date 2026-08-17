"""Prompt instrument for the provenance-detection benchmark.

Five conditions forming a ladder, each adding exactly one thing:

  C0  column names only                      -- ill-posed control
  C1  + target column                        -- PRIMARY (minimum coherent task)
  C2  + prediction point
  C3  + dataset description
  C4  + sample rows                          -- THE ABLATION

C4 is the experiment that matters.  The paper's claim is that provenance is not
recoverable from values, so showing the model actual data should NOT improve it.
If C4 >> C3, the claim is wrong and the paper is reframed.

C0 exists because provenance is relative to a target: without one the question
is ill-posed.  We expect C0 < C1 and report it, because a benchmark that never
asks an ill-posed question can't show that the question needs a target.

DESIGN NOTES

* Whole-table, not per-column.  Provenance is relational -- you judge a column
  against a target, alongside its siblings.  Per-column prompting asks a harder
  and less realistic question, and hides models that flag half the table.
* The task statement deliberately avoids the sieve's marker vocabulary
  ("post", "after", "recovery", "follow-up").  Using them would hand the model
  the regex we are trying to beat.
* Every column must be answered, and ABSTAIN is allowed.  Forcing binary
  verdicts inflates false positives and hides calibration.
* A one-line reason per column is required.  The reasons are the qualitative
  half of the results -- they tell you WHY a model missed `charges`.
* Column order is shuffled per run (see runner), because models anchor on
  position.
"""

SYSTEM = (
    "You are auditing a tabular dataset before it is used to train a "
    "predictive model. Answer only with the JSON object requested. Do not "
    "add commentary outside the JSON."
)

TASK = """\
Below is the column list of a dataset that will be used to train a classifier.

For each column, decide whether its value would already exist, and already have \
its final recorded value, at the moment the model is asked to make its \
prediction in real deployment.

Label each column with exactly one of:
  AVAILABLE    - the value exists and is final at prediction time
  UNAVAILABLE  - the value does not exist yet, or is not yet final, at prediction time
  ABSTAIN      - you cannot tell from what you have been given

Judge every column. Do not judge a column by how strongly it would predict the \
target; a column can be highly predictive and still be AVAILABLE, or weakly \
predictive and UNAVAILABLE.

Return JSON only, in exactly this form:
{"columns": [{"name": "<column>", "verdict": "AVAILABLE|UNAVAILABLE|ABSTAIN", \
"confidence": <0.0-1.0>, "reason": "<one short sentence>"}]}"""


def build(dataset, columns, condition, target=None, prediction_point=None,
          description=None, sample_rows=None):
    """Assemble the user message for one dataset under one condition.

    columns      : list of column names, ALREADY SHUFFLED by the caller
    sample_rows  : list of dicts, or None
    """
    p = [TASK, "", f"Dataset: {dataset}"]

    if condition >= 1 and target:
        p.append(f"Target column (what the model predicts): {target}")
    if condition >= 2 and prediction_point:
        p.append(f"Prediction is made: {prediction_point}")
    if condition >= 3 and description:
        p.append("")
        p.append("Dataset description:")
        p.append(description.strip()[:1500])
    p.append("")
    p.append("Columns:")
    for c in columns:
        p.append(f"  - {c}")

    if condition >= 4 and sample_rows:
        p.append("")
        p.append("Sample rows:")
        keys = list(columns)
        p.append("  " + " | ".join(keys))
        for r in sample_rows[:5]:
            p.append("  " + " | ".join(str(r.get(k, ""))[:18] for k in keys))

    return "\n".join(p)


CONDITIONS = {
    0: "names only (ill-posed control)",
    1: "+ target column (PRIMARY)",
    2: "+ prediction point",
    3: "+ dataset description",
    4: "+ sample rows (THE ABLATION)",
}


# ---------------------------------------------------------------- condition 5

EXPERT_SYSTEM = (
    "You are a domain expert auditing a tabular dataset before it is used to "
    "train a predictive model. Reason about the real-world process that produced "
    "the data before judging any column. Answer only with the JSON object "
    "requested."
)

EXPERT_TASK = """\
You are reviewing a dataset drawn from a real-world process. Work through three \
steps in order, and return all three.

STEP 1 - THE PROCESS
State what one row represents, and the sequence of real events a row passes \
through from beginning to end. Be concrete about the order of events.

STEP 2 - THE TIMELINE
Locate the target on that sequence: at which event does the target's value \
become known? Then state the latest moment BEFORE that event at which a \
prediction would still be useful. That moment is the prediction point.

STEP 3 - THE COLUMNS
For each column, place it on the same sequence and compare it to the prediction \
point. A column is UNAVAILABLE if the event that produces its value happens at \
or after the moment the target becomes known. It is AVAILABLE if its value is \
already fixed at the prediction point.

Judge every column. Use ABSTAIN only when you genuinely cannot place a column \
on the sequence. Do not judge a column by how strongly it would predict the \
target: a column can be highly predictive and still be AVAILABLE.

Return JSON only, in exactly this form:
{"process": "<one or two sentences: what a row is and the order of events>",
 "target_known_at": "<the event at which the target becomes known>",
 "prediction_point": "<the moment a prediction would be made>",
 "columns": [{"name": "<column>", "event": "<the event that produces this value>", \
"verdict": "AVAILABLE|UNAVAILABLE|ABSTAIN", "confidence": <0.0-1.0>}]}"""


def build_expert(dataset, columns, target=None, description=None, sample_rows=None):
    """Condition 5.  Domain-expert framing: derive the process and the timeline
    first, then place each column on it.

    Deliberately does NOT supply the prediction point -- the model must infer it
    in step 2.  Handing it over would make step 2 a copy and would confound this
    condition with C2."""
    p = [EXPERT_TASK, "", f"Dataset: {dataset}"]
    if target:
        p.append(f"Target column (what the model predicts): {target}")
    if description:
        p += ["", "Dataset description:", description.strip()[:1500]]
    p += ["", "Columns:"]
    p += [f"  - {c}" for c in columns]
    if sample_rows:
        p += ["", "Sample rows:", "  " + " | ".join(columns)]
        for r in sample_rows[:5]:
            p.append("  " + " | ".join(str(r.get(k, ""))[:18] for k in columns))
    return "\n".join(p)


CONDITIONS[5] = "domain-expert reasoning (process -> timeline -> columns)"


# ---------------------------------------------------------------- condition 6

DERIVATION_CLAUSE = """\

There are two distinct reasons a column can be UNAVAILABLE, and both count:

  (a) TIMING - the value does not exist, or is not yet final, at the prediction
      point.
  (b) DERIVATION - the value records WHY the target's outcome was assigned, or
      was itself an input used to determine the target. This holds EVEN IF the
      value was recorded BEFORE the prediction point.

A column can satisfy (b) while being chronologically earlier than the target.
Judging only by (a) will mark such a column AVAILABLE, which is wrong.

Being merely predictive is not sufficient for either: a column can correlate
strongly with the target and still be AVAILABLE."""


def build_derivation(dataset, columns, target=None, prediction_point=None,
                     description=None, sample_rows=None):
    """Condition 6.  Exactly condition 1 plus DERIVATION_CLAUSE.

    C1 is the base so that C6 - C1 isolates one variable: the statement of the
    criterion.  Building on C4 instead would confound the criterion with the
    sample rows.

    The clause names no column, dataset or domain.  It also avoids the sieve's
    marker vocabulary ("post", "after", "recovery", "follow-up"), because those
    words in the prompt would hand over the regex that baseline B1 already
    implements, and any gain would be uninterpretable.

    The final sentence is load-bearing: without it, "records why the outcome was
    assigned" reads as "is predictive of the outcome", and the model flags the
    whole table.  Precision on C6 is the check on whether that happened.
    """
    p = [TASK + DERIVATION_CLAUSE, "", f"Dataset: {dataset}"]
    if target:
        p.append(f"Target column (what the model predicts): {target}")
    p += ["", "Columns:"]
    p += [f"  - {c}" for c in columns]
    return "\n".join(p)


CONDITIONS[6] = "+ derivation criterion stated (C1 + one clause)"


# ---------------------------------------------------------------- condition 9
# C9 exists because of a DIAGNOSED failure, not a hunch.
#
# DeepSeek-V4-Pro flags all six of STEEL's sibling fault columns at C1 and
# un-flags all six at C6, giving the same reason each time: "measured
# concurrently."  Those six columns DEFINE the target -- Other_Faults is 1
# exactly when all six are 0 -- so they are the clearest REASON case in the
# corpus and precisely what C6 was written to catch.
#
# The likely culprit is C6's most emphatic sentence: "This holds EVEN IF the
# value was recorded BEFORE the prediction point."  It is there to say timing
# is irrelevant to (b), but it says so *in the vocabulary of timing*, and a
# model that follows it closely can conclude that (b) is a rule about
# before/after -- and that "concurrent" therefore falls outside it.
#
# C9 states the same criterion with NO temporal reference in (b) at all, adds
# an explicit instruction not to reason about time when testing it, and gives
# a positive test (reconstruction) in place of a negative carve-out.
DERIVATION_CLAUSE_V2 = """\

There are two distinct reasons a column can be UNAVAILABLE, and both count:

  (a) TIMING - the value does not exist, or is not yet final, at the prediction
      point.
  (b) DERIVATION - the target's value is a function of this column's value: the
      column was an input to the process that assigned the target, or the
      target was computed, defined or decided from it.

Criterion (b) is about INFORMATION, not about time. Do not test (b) by asking
when the value was measured. Test it by asking: could the target be
reconstructed, wholly or in part, from this column? If yes, the column is
UNAVAILABLE whatever its timing - earlier, later, or simultaneous.

Being merely predictive is not sufficient for either: a column can correlate
strongly with the target and still be AVAILABLE."""


def build_derivation_v2(dataset, columns, target=None):
    """Condition 9.  Exactly condition 1 plus DERIVATION_CLAUSE_V2.

    Byte-identical to C6 except for the clause, so the two are directly
    comparable and any difference is attributable to the wording alone."""
    p = [TASK + DERIVATION_CLAUSE_V2, "", f"Dataset: {dataset}"]
    if target:
        p.append(f"Target column (what the model predicts): {target}")
    p.append("")
    p.append("Columns:")
    for c in columns:
        p.append(f"  - {c}")
    return "\n".join(p)


CONDITIONS[9] = "+ derivation criterion, stated without reference to time"


# ---------------------------------------------------------------- condition 7

SURROGATE_CLAUSE = """\

  (c) SURROGATE - the value is itself a pre-existing estimate, score or
      prediction OF the same outcome, or of something that stands in for it.
      This holds even when the estimate was produced at or before the
      prediction point, because it was built from information the deployed
      model will not have.

A column can satisfy (c) while being computed at baseline and therefore
perfectly available in time. Judging only by (a) or (b) will mark such a column
AVAILABLE, which is wrong."""


def build_surrogate(dataset, columns, target=None):
    """Condition 7.  C6 plus the surrogate-outcome clause.

    Prediction registered before running: this should move columns that are
    prior estimates of the target (SUPPORT2's prg2m, prg6m, sps, aps) and
    should NOT move REASON, CONSEQUENCE or TIMING columns, which C6 already
    covers.  If it lifts everything, it is a threshold change rather than a
    criterion, and the subtype story does not survive.
    """
    p = [TASK + DERIVATION_CLAUSE + SURROGATE_CLAUSE, "", f"Dataset: {dataset}"]
    if target:
        p.append(f"Target column (what the model predicts): {target}")
    p += ["", "Columns:"]
    p += [f"  - {c}" for c in columns]
    return "\n".join(p)


CONDITIONS[7] = "+ surrogate-outcome criterion (C6 + one clause)"
