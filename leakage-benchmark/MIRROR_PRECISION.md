# The re-upload filter's precision, measured — and why it is not being retuned

**Status: an audit of all 40 mirror-excluded Kaggle datasets, by hand, against
their titles and attributions. Roughly half the exclusions are wrong. One is a
bug; the rest are threshold choices I am deliberately leaving frozen. Written
before deciding anything, so the decision is on the record next to the evidence
rather than after it.**

## What the filter is for

The Kaggle sweep excludes two classes of dataset from its denominators:
synthetic tables, and **re-uploads of Stratum A/B** — because a hit on a
re-uploaded UCI Bank Marketing is not an independent observation, it is the
corpus finding itself. `kaggle_deep.mirrors` and `mirror2.detect` implement the
second test. [as-of] At 7,931 datasets enriched, they excluded **60 sentences across 40
datasets**; at the **complete** sweep of 8,693 the figures are **61 sentences
across 41 datasets**.

Those 40 are the population this file audits — 40 of the final 41, the one
later arrival being a `CIRRHOSIS (target 'status' …)` exclusion of the same
class (b) already documented below. The 48% figure is therefore computed on
40/41 of the final population and does not move materially.

## How the exclusions break down

| rule | sentences | what it does |
|---|---|---|
| long column overlap (≥4, or 25%) | 54 | column names of ≥4 chars shared with a corpus table |
| target + 2 columns | 18 | the corpus table's target name plus any two columns |
| source name | 10 | a credited name like `titanic`, `compas` appears |

## The audit

**Correctly excluded — 19 datasets.** All fourteen BANK hits at 12/13 or 13/13
are titled some variant of *"Bank Marketing"*; `predictive-maintenance-ai4i-2020-uci`
names AI4I in its slug; DIABETES at 29/46, STUDENT at 28/28 and 13/28, and the
`larsen0966/student-performance-data-set` source-name hit are all genuine
re-uploads. The filter's core job, catching verbatim re-uploads of a corpus
table, it does well.

**Wrongly excluded — 21 datasets.** Grouped by the rule that failed:

**(a) `source name`, as plain substring — a bug, not a threshold.** The test is
`if s in hay`, with no token boundary. So `'compas'` matches **`encompass`**:

| dataset | attributed to | actually matched |
|---|---|---|
| `gowtha69/mods-clinical-3c-50k` | COMPAS | *"encompass"* |
| `thedevastator/online-course-student-engagement-metrics` | COMPAS | *"encompassing"* |

Four SOURCE_NAMES entries are short enough to collide this way: `compas`,
`ai4i2020`, `titanic`, `support2`. Only `compas` is an English substring, and it
is the one that fired.

**(b) `target + 2 columns`, on generic target names — 10 datasets.** The target
names doing the work are `status`, `death` and `loan_status`:

| attributed to | via target | datasets wrongly caught |
|---|---|---|
| CIRRHOSIS | `status` | COVID-19 outcomes ×2, remote-vs-office working, clinical trials, no-show prediction |
| SUPPORT2 | `death` | global suicide data, US death rates, self-driving-car ethics, coronary artery disease, heart-disease risk factors |

A dataset about death rates contains the word `death`. This rule has essentially
no precision when the corpus table's target is an ordinary English noun.

**(c) long overlap at the 4-column floor — 3 datasets.** BANK has 13 long
columns, so its threshold is `max(4, 3) = 4`, and its column names are ordinary
words (`duration`, `month`, `day`, `previous`, `contact`, `campaign`):

| dataset | attributed |
|---|---|
| `patricklford/covid-19` | BANK 4/13 |
| `lorentzyeung/price-paid-data-202304` (UK property prices) | BANK 4/13 |
| **`marekk13/pkp-intercity-delays-dataset`** (Polish railway delays) | BANK 4/13 |

**(d) STUDENT source-name phrase — 4 datasets.** *"student performance"* is a
phrase that appears in the prose of any paper-adjacent education dataset;
`ai-impact-on-students`, `cs1-failure-prediction` and
`higher-education-predictors-of-student-retention` are not re-uploads of UCI
Student Performance. `tejas14/...` (target `g3` plus 3 columns) is genuine.

**Precision of the exclusion filter: 19/40 ≈ 48%.**

## The one that matters

`marekk13/pkp-intercity-delays-dataset` is the best candidate the sieve
produced, and it never reached the anchor step because it was thrown out as a
re-upload of UCI Bank Marketing. Its card carries, on named columns:

> *"note potential target leakage if used as an input feature for real-time
> target prediction"* · *"Represents real-time traffic hazard intensity along
> the segment without target leakage"* · *"Initial origin stops
> (`stop_order = 1`) are excluded from target modeling because delay delta is
> defined between consecutive stops"*

A warning **conditional on the prediction point** is exactly the triple-relative
definition §2.1 uses. Re-checked against the **complete** sweep rather than the
subset that first suggested it: exactly **two** of 8,693 Kaggle cards use the
phrase *"target leakage"* at all, and the other one uses it as a selling point
(*"minimizing the risk of target leakage"*). So PKP is the only card in the
population that states a prediction-point-conditional warning against a named
column, and it is excluded. It is not yet a finding — nothing is, until the columns are anchored
to a real CSV header and the derivation checked in the values.

## What I am NOT doing, and why

**I am not retuning the thresholds.** I have now seen which datasets each
threshold admits, and PKP is one I want. Lowering the `target + 2` rule or
raising the BANK floor *after* looking would be choosing a filter by its output,
which is the same self-serving move the ChessFraud coding note refuses on a
0.643-ΔF1 record. The registered denominators in `REGISTERED_STRATUM_C.md` were
computed under this filter and they stay computed under it.

**I am fixing the substring bug only, and it changes nothing here.** `'compas'`
matching `encompass` is not a threshold choice; the rule means "the credited
source name appears", and a match inside another word is not that rule firing,
it is the rule failing. Fixing it releases the two COMPAS datasets — neither of
which has a leakage sentence worth anything (one is *"number of events"*
boilerplate). So the fix is made on principle and buys nothing, which is the
right order of events.

**What goes in the paper instead of a retune:** the 48% figure, the exclusion
list, and PKP named as excluded. §6.4's yield denominators already carry
"re-upload of Stratum A/B — 60" as a line item; a reader is entitled to know
that line is about half wrong, in the direction of *under*-counting the real
population. Legitimate-by-default already makes precision a lower bound (§4.6);
this makes the *denominator* a lower bound too, and both point the same way.

## The bug fix, applied and verified

`SOURCE_NAMES` now matches on token boundaries for single-token names and keeps
plain containment for multi-word phrases like `student performance`. Re-running
the sieve over 8,006 enriched datasets [as-of] moved **exactly three** datasets and
nothing else — 235 candidate datasets before and after, none lost, none gained:

| dataset | was | now |
|---|---|---|
| `patricklford/what-about-the-wind` | COMPAS (source name) | **not excluded** |
| `thedevastator/online-course-student-engagement-metrics` | COMPAS (source name) | **not excluded** |
| `gowtha69/mods-clinical-3c-50k` | COMPAS (source name) | CIRRHOSIS (`status` + 4 columns) |

Headline counts move from *60 re-uploads / 112 real* to **58 / 113**. The third
dataset falls straight through into class (b) above — caught by the generic-
target rule instead — which is left standing, as promised.

Regression checks: `compas` still matches the COMPAS tool named in prose,
`titanic` still matches, and `student performance` still matches as a phrase.

## Follow-up owed
2. Report `mirrors`/`detect` precision as 19/40 in §6.4.2, with this list in the
   appendix.
3. **PKP is a registered-protocol question, not a judgement call.** The clean
   way to admit it is to state in advance that any dataset excluded *only* by
   the `target + 2` or 4-column-floor rules is re-examined by hand, and to apply
   that to all 13 such datasets — not to the one I liked. If that is done, it is
   done to the whole class or not at all, and the other twelve are listed above
   so the class is fixed before the examination starts.
