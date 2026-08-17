# Six in Seven Thousand: A Source-Grounded Benchmark for Feature-Level Target Leakage

*Draft v1 — every number in this draft is traceable to `RESULTS.md`. Claims are
marked **[strong]**, **[supported]** or **[weak]** where the distinction
matters. Author list, related-work citations and figures are placeholders.*

---

## Abstract

A feature leaks when its value encodes the outcome it is used to predict. We
distinguish this **feature-level target leakage** from the other failures the
word "leakage" is used for — duplicated units across a split, train/test
contamination, identifier columns — and show the distinction is not pedantic:
sweeping the complete UCI ML Repository (660 datasets) and all active OpenML
datasets (6,420), we find explicit, column-level documentation of feature-level
target leakage in **6 of 7,080 datasets (0.085%)**, and **none at all on
OpenML**, whose ten leakage-related statements are entirely about splits and
identifiers. There is no corpus to train or evaluate a detector on.

We build one: 15 datasets, 604 columns, 76 positives, each licensed by a
quotable statement from the dataset's own documentation. Three of the datasets
form a held-out stratum in which the source *names* the leaking column, so the
ground truth is a quotation rather than an inference.

Language models read column names and a target and clear a tuned statistical
baseline by a wide margin (F1 **0.894** vs **0.658**); removing the columns they
flag recovers the honest AUC almost exactly, where the baseline misses in both
directions. But the interesting result is where they fail. Across three
frontier models from three laboratories, the intersection of errors is
**exactly four columns**, all of one kind: a *prior estimate of the same
target*, available at prediction time and therefore correctly judged
"available" by a model reasoning about time. The best model misses four columns
out of forty-six and all four are of this kind. Stating the prediction point —
more information, correctly used — drives recall on this subtype to **0/6 in
both frontier models independently**, while a single sentence naming the
criterion recovers it to **6/6**.

Capability has closed every subtype of feature-level target leakage that is
about time, and none of the one that is not, because the models' temporal
reasoning is correct and the category is not temporal.

---

## 1. Introduction

Every practitioner has met the model that scores 0.99 and is worthless. Usually
the cause is a column that could not have existed when the prediction was
supposed to be made, or that records why the label was assigned. The failure is
old, well known, and — as we show — almost never written down.

"Data leakage" names at least five distinct failures. Two rows describing the
same patient landing on both sides of a split is *group leakage*. Released files
whose train and test portions overlap is *contamination*. A row identifier that
happens to correlate with the outcome is an *identifier artefact*. A
preprocessing step fitted on the full dataset is *procedural leakage*. And a
feature whose value encodes the outcome is *feature-level target leakage*.

They are usually discussed together, and they should not be. They have
different causes, different detection methods, and different remedies. Group
leakage is a splitting problem, solvable by grouping. Contamination is a
release-hygiene problem. Feature-level target leakage cannot be fixed by any
splitting scheme, because the column is wrong in every split.

This paper is about the last one only. Three contributions:

**(1) A measurement of how little is documented.** We sweep both public
repositories of tabular ML datasets in full and read every hit. Feature-level
target leakage is explicitly documented in **6 of 7,080 datasets**. The
practical consequence is stark: there is no labelled corpus from which to build
or evaluate an automatic detector, which is a sufficient explanation for why no
such tool exists. **[strong]**

**(2) A benchmark with two evidence strata.** 15 datasets, 604 columns, 76
documented positives. Forty-six are *inferred from documentation* — a source
describes the column and we judge it. Thirty are **named by the source**: the
documentation states that the target was computed from the column, files it
under an outcome heading, or instructs the reader to discard it. The second
stratum is a genuinely held-out test, because its selection criterion — "the
source already says so" — is independent of any model's behaviour. **[strong]**

**(3) A definitional failure that survives capability scaling.** Frontier
models are at or near ceiling on every subtype of feature-level target leakage
defined by *time*. They fail, convergently and identically across three
laboratories, on the one subtype defined by *information*: a column that is a
prior estimate of the same target. We show the failure is not a capability
ceiling by closing it with a sentence, and we show it is not noise by causing
it on demand. **[strong]**

We also report what did not work. A registered prediction about which subtype
our intervention would move fails on held-out data (§6.4). An order-averaging
remedy we proposed turns out to be model-specific and is withdrawn (§6.8).
A closed-world dictionary rule under-fires by an order of magnitude and is
reported as a negative result (§4.3).

---

## 2. Scope, and a taxonomy of five mechanisms

### 2.1 Definition

Let a dataset have target $y$ and a stated **prediction point** $t$ — the
moment at which, in the intended deployment, the model is asked to produce a
prediction. A column $x$ exhibits **feature-level target leakage** with respect
to $(y, t)$ if $x$'s recorded value could not be obtained, or would not have
its final recorded value, by an honest process running at $t$; or if $x$'s value
was an input to the process that assigned $y$.

Three things follow immediately and are worth stating because they are
routinely elided:

* **Leakage is relative to a triple $(x, y, t)$, not a property of a column.**
  `discharge_disposition_id` is a leak when predicting 30-day readmission and
  an ordinary covariate when predicting length of stay.
* **Predictiveness is not leakage.** A column may be almost perfectly
  predictive and entirely legitimate. Every correlation-based detector
  confuses these, which is why we report one as a baseline rather than a method.
* **The prediction point must be stated by someone.** It is not recoverable
  from the data. We state it for every dataset and list all of them, so a
  reader can disagree with one rather than with all.

### 2.2 Five mechanisms

| mechanism | the column ... | example |
|---|---|---|
| **REASON** | was an input used to assign the label | `koi_fpflag_ss` → `koi_disposition` |
| **CONSEQUENCE** | exists *because* the outcome occurred | `body` (body recovery number) → `survived` |
| **TIMING** | is recorded after the prediction point | 1995 crime counts → 1995 violent crime rate, predicted from 1990 census |
| **SURROGATE** | is a prior estimate of the same target | `prg2m` (physician's 2-month survival estimate) → `death` |
| **UPSTREAM** | was computed by a process that consumed outcome information | `surv2m` (model-fitted survival probability) → `death` |

SURROGATE was not in our original taxonomy. It was added after a model
correctly refused to flag five SUPPORT2 columns, on grounds we could not fault:
the columns *are* computed at baseline and *are* available at the prediction
point. They are still unusable, because they are estimates of the very quantity
being predicted. §6.5 shows this subtype is now the entire remaining error of
the best models tested.

### 2.3 Explicitly out of scope

Group leakage, train/test contamination, procedural leakage (preprocessing
fitted on the full dataset), and identifier artefacts. Each is real; none is
what this paper measures. §3 shows that in the largest public repository, these
are the *only* things the word "leakage" is used for.

---

## 3. How much explicit documentation exists

### 3.1 Method

We swept both machine-readable repositories of tabular ML datasets in full:
**660 UCI records** and **6,420 active OpenML dataset descriptions**. Three
passes ran over the *entire* record rather than the data dictionary:

* **WARN sentences** — the source instructs the reader not to use a named
  column, or says its value is not known at prediction time.
* **DEFINE sentences** — the source states the target was computed, assigned or
  derived from a named column.
* **Outcome headings** — a heading such as *"Complications and outcomes of
  myocardial infarction:"* is an explicit statement about every column filed
  beneath it.

Every hit was read individually and classified by *which* leakage it describes.

Two design points were forced by failures and are worth reporting, because they
are the difference between finding this material and not:

**Reading only per-variable descriptions is structurally blind.** The archive's
two most-cited leakage warnings — Bank Marketing's `duration` and Student
Performance's `G1`/`G2` — live in free prose fields, not in the dictionary. Our
first pass read only `variables[].description` and found neither.

**A derivation sieve must know the target's name.** Requiring the literal words
*class* / *label* / *target* as the sentence subject fired **zero times in 660
datasets**. Authors write derivations using the target's own name: *"The per
capita violent crimes variable was calculated using population and the sum of
crime variables … murder, rape, robbery, and assault."*

### 3.2 Result

| | UCI | OpenML |
|---|---|---|
| datasets swept | 660 | 6,420 |
| datasets with any leakage-adjacent sentence | 13 | 89 |
| **feature-level target leakage** | **6** | **0** |
| group leakage | 0 | 2 |
| train/test contamination | 0 | 1 |
| identifier column | 3 | 2 |
| sieve false positive | 4 | 5 |

**6 in 7,080 datasets — 0.085%.**

The OpenML result is the sharper one. Its ten distinct leakage-related
sentences are: drop duplicate `patient_nbr`; drop duplicate `obj_ID`; a
train/test overlap in the released files; `serviceID` should be removed; a
YouTube video `id` should be dropped — and five sieve false positives, one of
which matched the trigger word *cheating* because it is a **column name**
(*central heating*) in a Munich rent index.

The largest public repository of tabular ML datasets uses the word "leakage"
exclusively for splits and identifiers. The failure mode this paper is about has
no vocabulary there at all.

### 3.3 What this implies

This is the paper's motivation stated as a measurement rather than an
assertion. It explains, without speculation, why no off-the-shelf detector
exists: there is no labelled corpus to build or evaluate one from. It also
justifies the expense of hand curation — fifty source documents for
forty-six positives — as the only route available, rather than a
methodological preference.

We also report a negative result. Before this sweep we attempted a
**closed-world dictionary rule**: for the 44 UCI datasets whose every column
carries an official description, classify each column from its description, so
that silence about a column becomes informative. Applied to 1,007 columns it
flagged **13 (1.3%)** against a hand-curated base rate of 15%, and recovered
6 of 9 known positives — all three misses being documentation failures rather
than rule failures (`discharge_disposition_id`: *"Integer identifier
corresponding to 29 distinct values"*). A complete data dictionary is not the
same thing as documented provenance. **[strong, negative]**

---

## 4. Benchmark construction

### 4.1 Evidence protocol

A column becomes a positive only with a **verbatim quotation of ≤25 words**
from a citable source, plus a locator. Explicitly inadmissible as evidence:
our own judgement, correlation with the target, feature importance, and a
language model's opinion. A record without a quotable licensing phrase is
written to a reject file, and the rejects are reported as attrition rather than
discarded.

Source formality is **not** an admission criterion. An uploader's paragraph
counts the same as a peer-reviewed codebook. What is required is that the
statement names the column and reaches a conclusion about it.

### 4.2 Two strata

**Stratum A — `INFERRED_FROM_DESCRIPTION` (12 datasets, 306 columns, 46
positives).** A source describes the column; we judge that the description
places it after the prediction point or shows it fed the label.

| dataset | cols | pos | target |
|---|---|---|---|
| KOI | 40 | 4 | `koi_disposition` |
| DIABETES | 47 | 1 | `readmitted` |
| LC | 29 | 2 | `loan_status` |
| COMPAS | 15 | 4 | `two_year_recid` |
| AI4I | 10 | 4 | `Machine failure` |
| TITANIC | 9 | 2 | `survived` |
| BANK | 16 | 1 | `y` |
| SUPPORT2 | 47 | 15 | `death` |
| BONEMARROW | 36 | 5 | `survival_status` |
| HEARTFAIL | 12 | 1 | `DEATH_EVENT` |
| STEEL | 33 | 6 | `Other_Faults` |
| ECHO | 12 | 1 | `alive_at_1` |

Subtypes: REASON 15, CONSEQUENCE 24, TIMING 5, CONTESTED 2. Twenty-four of the
forty-six subtype codes are stated by a source; twenty-two are analyst-assigned.

**Stratum B — `NAMED_BY_SOURCE` (3 datasets, 298 columns, 30 positives).** The
source itself names the column: it states the target was summed from it, files
it under an outcome heading, or tells the reader to predict without it.

| dataset | rows | cols | pos | subtypes | target |
|---|---|---|---|---|---|
| MI (UCI 579) | 1,700 | 122 | 11 | CONSEQUENCE 11 | `ZSN` |
| CRIME (UCI 211) | 2,215 | 144 | 17 | REASON 8, TIMING 9 | `violentPerPop` |
| STUDENT (UCI 320) | 649 | 32 | 2 | SURROGATE 2 | `G3` |

Every quotation is verified at build time against the cached source text, and
every column against the real CSV header; a misquote or a renamed column raises
rather than silently entering the ground truth.

Reporting the two strata separately is the honest form of a two-tier F1: the
difference between them is a property of the *labels*, not an adjustment
applied to any model's answers.

### 4.3 Attrition, and one instructive recovery

Twenty datasets were processed; twelve yielded admissible evidence. The eight
that did not are a finding — their own literature never states when a column
was recorded — with one important exception.

Myocardial Infarction Complications was in the zero-evidence set. Its evidence
is a *heading*, `Complications and outcomes of myocardial infarction:`, standing
over attributes 113–124, and every sieve we had read sentences. Adding a
heading-aware pass recovered eleven positives from a dataset we had recorded as
undocumented. The attrition set was partly measuring the shape of our
instrument rather than the silence of the sources. We report this because it
bounds how much any such attrition number can be trusted, including ours.

### 4.4 Legitimate-by-default

A column with no source statement is treated as legitimate. This makes reported
**precision a lower bound**: a model flagging a genuine but undocumented leak is
scored as wrong. §6.7 shows this is not hypothetical — two of the corpus's
apparent false positives behave downstream exactly like real leaks. Stratum B
is partially immune, since a full-column-set source makes silence informative.

---

## 5. Experimental setup

### 5.1 The condition ladder

Each condition adds exactly one thing to the previous one:

| | added |
|---|---|
| C0 | column names only (ill-posed control — provenance is undefined without a target) |
| **C1** | **+ the target column (primary condition: minimum coherent task)** |
| C2 | + the prediction point |
| C3 | + the dataset's own documented description |
| C4 | + five sample rows (**the ablation**) |
| C5 | domain-expert scaffold |
| **C6** | **+ the derivation criterion** |
| C7 | + the surrogate criterion |

C4 is the ablation that matters: if provenance were recoverable from values,
showing the model actual data should help. C3 uses only descriptions written by
the dataset's authors — a description we wrote could encode the answer.

The intervention at C6 is one clause, stated in full:

> There are two distinct reasons a column can be UNAVAILABLE, and both count:
> (a) TIMING — the value does not exist, or is not yet final, at the prediction
> point. (b) DERIVATION — the value records WHY the target's outcome was
> assigned, or was itself an input used to determine the target. This holds
> EVEN IF the value was recorded BEFORE the prediction point.

### 5.2 Protocol

Whole-table prompting (provenance is relational — a column is judged against a
target, alongside its siblings). Every column must be answered; `ABSTAIN` is
permitted and reported, because forcing binary verdicts inflates false positives
and hides calibration. A one-line reason per column is required.

**Column order is shuffled per run.** This is not cosmetic: §6.8 shows ordering
alone moves F1 by up to 0.312 for one model.

Cells below a 90% coverage floor are excluded and counted, never scored as
partial. Failed API calls are never cached — a quota error written to cache
becomes a permanent zero-coverage "answer" the model never gave, which
silently produced 91 such cells before we caught it.

### 5.3 Models

`claude-opus-5` (max effort), `gpt-5.6-sol` (extra-high effort),
`gemini-3.7-flash`, `gemini-3.5-flash`, `Qwen3-Coder-480B-A35B-Instruct`. The
two frontier models were run through their chat interfaces with one sub-agent
per cell; their prompts were verified byte-identical to the API runs by
regenerating 24 prompts and hash-matching 18 against cells already on disk.
Both returned **100% coverage on every cell with zero invented column names**.

### 5.4 Baselines

All thresholds swept **on the answers**, making every baseline an upper bound.

| baseline | P | R | F1 |
|---|---|---|---|
| B0 always AVAILABLE | 0.000 | 0.000 | 0.000 |
| B1 name regex | 0.667 | 0.087 | 0.154 |
| B2 univariate AUC | 0.342 | 0.565 | 0.426 |
| **B3 \|correlation\| (tuned)** | **0.788** | **0.565** | **0.658** |
| B4 missingness asymmetry | 0.150 | 1.000 | 0.261 |

B4 is degenerate at n=12 — its best available threshold flags all 306 columns.
We report it as a dead baseline rather than dropping it.

---

## 6. Results

### 6.1 Models clear the statistical ceiling

Stratum A, 12/12 datasets:

| model | C1 | **C6** | Δ | C6 P | C6 R |
|---|---|---|---|---|---|
| **claude-opus-5 max** | 0.844 | **0.894** | +0.050 | 0.875 | 0.913 |
| gemini-3.7-flash | 0.803 | 0.876 | +0.073 | 0.918 | 0.839 |
| gpt-5.6-sol xhigh | 0.805 | 0.857 | +0.052 | 0.867 | 0.848 |
| gemini-3.5-flash | 0.805 | 0.854 | +0.049 | 0.852 | 0.856 |
| Qwen3-Coder-480B | 0.645 | 0.803 | +0.158 | 0.722 | 0.904 |
| B3 (tuned upper bound) | — | 0.658 | — | 0.788 | 0.565 |

Reading column names beats a correlation threshold whose cutoff was fitted on
the answers, by **+0.236 F1** at best. **[strong]**

C0–C5 are otherwise flat: the full ladder including the domain-expert scaffold
moves gemini-3.7 by at most 0.046 F1. In particular **C4 does not help**, which
is the ablation the framing predicted — provenance is not in the values.

### 6.2 The failure is definitional

`gemini-3.5-flash`, 5 seeds pooled:

| cond | REASON | CONSEQUENCE | TIMING | precision |
|---|---|---|---|---|
| C1 | 47/75 63% | 91/120 76% | 25/25 100% | 0.865 |
| **C6** | **66/75 88%** | 83/105 79% | 25/25 100% | 0.852 |

The same pattern in every model family tested:

| model | REASON C1 → C6 | CONSEQUENCE+TIMING C1 → C6 |
|---|---|---|
| claude-opus-5 max | 93% → **100%** | 76% → 86% |
| gpt-5.6-sol xhigh | 67% → **93%** | 79% → 79% |
| gemini-3.7-flash | 51% → **89%** | 84% → 81% |
| gemini-3.5-flash | 63% → **88%** | 80% → 83% |
| Qwen3-480B (5 seeds) | 33–73% → **100% at every seed** | — |

TIMING is at 100% before the intervention in every model. REASON is not, and
moves sharply when the criterion is stated, while precision does not fall (it
rises for three of the five). The models were operationalising "leakage" as
*timing*; naming the second criterion is what closes the gap. **[strong]**

### 6.3 The tuning objection, measured

C6's clause was written after inspecting failures on KOI, AI4I and DIABETES. We
measure the resulting dependency rather than arguing about it.

**Leave-one-dataset-out.** Dropping KOI: gemini-3.7's REASON gain falls to
**zero**; gemini-3.5's effect **inverts** (−0.058); Qwen-480B **survives**
(+0.156, still +6 REASON columns). For both Gemini models the entire REASON
lift is KOI's four `koi_fpflag_*` columns. **[reported against ourselves]**

**Memorisation control.** All 306 columns renamed to string-distinct aliases
under a bijective map that passes four mechanical checks (total, distinct,
marker-status preserved in both directions, no truth conflicts):

| | REASON | CONSEQUENCE | precision |
|---|---|---|---|
| original C1 | 10/15 67% | 19/24 79% | 0.878 |
| original C6 | 12/15 80% | 19/24 79% | 0.826 |
| paraphrased C1 | 9/15 60% | 16/24 67% | 0.889 |
| paraphrased C6 | 10/15 67% | 17/24 71% | 0.850 |

About half the C6 REASON gain is memorisation-assisted (+13pp on real names,
+7pp on aliases). The effect survives renaming and is materially smaller.
**[supported; one model, one seed]**

`gpt-5.6-sol` offers a different and stronger form of the same reassurance. At
C1 it **abstained on all 40 KOI columns** — *"the deployment prediction point is
unspecified"* — and flagged all four `koi_fpflag_*` correctly at C6. Refusal is
not what a memorised answer key produces.

### 6.4 Held-out, source-named evaluation — including a registered prediction that fails

Stratum B, 3 shuffles per cell:

| model | C1 | C2 | C6 | C6 majority-vote |
|---|---|---|---|---|
| gpt-5.6-sol xhigh | **0.966** (P **1.000**) | 0.804 | 0.926 | **0.984** |
| claude-opus-5 max | 0.762 (P 0.624) | 0.697 | 0.861 (**R 1.000**) | 0.857 |
| Qwen3-480B | 0.543 | 0.667 | 0.627 | 0.621 |

`gpt-5.6-sol` at C1 achieves **84 true positives and zero false positives**
across 27 cells and 894 column judgments. It flagged the source-documented
positives and nothing else — which doubles as an independent audit of our
ground truth. **[strong]**

The two frontier models are opposites and, unexpectedly, **nested**: opus's
flagged set strictly *contains* gpt's at both conditions, so union = opus and
agreement = gpt exactly. Requiring agreement recovers gpt's precision (0.968) at
**no recall cost** (1.000).

**A registered prediction fails here.** §6.2 predicted C6 lifts REASON and
leaves other subtypes flat. On Stratum B, REASON is **24/24 = 100% in every
condition and every model, including C0** — `murders`, `rapes`, `robberies` are
lexically transparent, so there is no gap to close. All movement is elsewhere.
We report this as a failed prediction rather than reframing it. What survives is
narrower: the derivation criterion moves whichever subtype the model was
missing, and here that was not REASON. **[reported against ourselves]**

### 6.5 The convergent failure

Every C6 error on Stratum A — all 46 positives, one shuffle:

| model | missed | which |
|---|---|---|
| **claude-opus-5 max** | **4** | `SUPPORT2.sps`, `aps`, `prg2m`, `prg6m` |
| gemini-3.7-flash | 6 | those four + `SUPPORT2.dnr` + `DIABETES.discharge_disposition_id` |
| gpt-5.6-sol xhigh | 7 | those four + `SUPPORT2.surv2m`, `surv6m` + `DIABETES.discharge_disposition_id` |

**The best model misses four columns out of forty-six, and all four are
SURROGATE.** Not one column in the corpus is missed by it for any other reason.

The intersection across Google, OpenAI and Anthropic — three architectures,
three training pipelines, three laboratories — is **exactly `sps`, `aps`,
`prg2m`, `prg6m`**: the columns that prompted us to add the subtype in the first
place. **[strong]**

Stratum B corroborates on different data, in a different domain. Recall by
subtype:

| cond | model | CONSEQUENCE | REASON | **SURROGATE** | TIMING |
|---|---|---|---|---|---|
| C1 | opus | 100% | 100% | **4/6 67%** | 100% |
| C1 | gpt | 100% | 100% | **0/6 0%** | 100% |
| C6 | opus | 100% | 100% | **6/6 100%** | 100% |
| C6 | gpt | 100% | 100% | 4/6 67% | 100% |

`gpt-5.6-sol` scores **F1 0.000 on STUDENT at C1** for exactly one reason: it
calls `G1` and `G2` AVAILABLE. They *are* available — prior-period grades exist
before the final grade. It is not wrong about time. It does not hold the
category.

**Honest caveat.** Qwen-480B scores 6/6 on SURROGATE at C1, but with precision
0.387: it flags these columns because it flags nearly everything. Its result is
not evidence of the category and we do not present it as such. The finding is
about *precise* models. **[stated limitation]**

### 6.6 The failure can be caused on demand

| cond | opus SURROGATE | gpt SURROGATE |
|---|---|---|
| C1 | 4/6 67% | 0/6 0% |
| **C2 (+ prediction point)** | **0/6 0%** | **0/6 0%** |
| C6 (+ derivation criterion) | **6/6 100%** | 4/6 67% |

Adding the prediction point drives SURROGATE recall to **exactly zero in both
frontier models, independently**, while leaving CONSEQUENCE, REASON and TIMING
at 100%. The mechanism is visible in the models' own stated reasons: told when
the prediction is made, they check whether the value exists by then, correctly
conclude it does, and mark it available. **Correct reasoning about time is what
destroys the detection.** More information makes the system worse, reproducibly,
across two laboratories. **[strong]**

This is the paper's cleanest evidence that the failure is definitional rather
than perceptual: we can turn it off with one sentence and back on with another.

### 6.7 What the leakage costs

Four arms differing **only** in which columns are present — no tuning, no
per-arm choices, group-aware 5-fold splits where a unit repeats. Two learners,
because leakage is a property of the data and should appear under both.

**Inflation = AUC(all columns) − AUC(ground-truth-cleaned)**, over 12 datasets:

| learner | mean | median | max |
|---|---|---|---|
| random forest | **0.130** | 0.109 | 0.357 |
| gradient boosting | **0.133** | 0.123 | 0.374 |

Leaving the documented leaks in buys about **0.13 AUC of nothing**, with the
same magnitude under both learners.

Does an automatic arm land on the honest ceiling? The ratio
(all − arm)/(all − GT) reads ≈1.00 for both arms and is useless, because an arm
that overshoots by deleting a legitimate column also scores 1.00. Distance from
the ceiling does not have that blind spot:

| learner | mean \|LLM − GT\| | mean \|B3 − GT\| | LLM closer | B3 closer | tie |
|---|---|---|---|---|---|
| rf | **0.025** | 0.076 | 7 | 1 | 4 |
| gb | **0.028** | 0.073 | 7 | 1 | 4 |

The baseline misses in **both directions**: it under-drops on Lending Club
(0.909 against a ceiling of 0.736 — it keeps `recoveries`) and over-drops on
Titanic (0.750 against 0.844 — it deletes `sex`). A correlation threshold cannot
separate "correlated because it caused the label" from "correlated because it
predicts the label", which is the entire distinction. **[strong]**

Where the model overshoots — ECHO and BONEMARROW — are the two datasets where it
flags columns we have no documentation for. §4.4 predicts exactly this, and
whether those are errors or undocumented true positives is not decidable from
our ground truth.

### 6.8 Negative results and instability

**Order sensitivity is a model property, not a task property.** Per-seed F1
spread on Stratum B at C1: `gpt-5.6-sol` **0.000**, `claude-opus-5` 0.182,
Qwen-480B **0.312** — the last being four times the ±0.07 seed band measured on
Stratum A, and larger than any difference between conditions for that model. On
Qwen, CONSEQUENCE recall on MI runs 27% / 100% / 100% across three shuffles of
the same 122 column names with nothing else changed.

We proposed majority-voting over shuffles as a remedy, and on Qwen it works
(C1 F1 0.543 → 0.732, recall 1.000). It does **not** generalise: `gpt-5.6-sol`
returns an identical answer under three shuffles, so there is nothing to
average. We withdraw the general claim and report it as a remedy for models
that need one. **[withdrawn]**

**C4 and C5 can actively hurt.** On Qwen, C4 (sample rows) contains everything
C2 has and still loses C2's entire CONSEQUENCE gain while precision collapses to
0.344; C5 drives two datasets to F1 0.000. These are single-seed cells against a
0.312 spread, so the magnitude is not established and we say so. **[weak]**

**A closed-world dictionary rule fails.** See §3.3.

---

## 7. Discussion

**The gap is definitional, and gaps are closable with a sentence.** This is good
news for practitioners and awkward for a scaling narrative. Three frontier
models, three laboratories, converge on the same four columns not because the
task is hard but because their operational definition of "leakage" is temporal
and one of the mechanisms is not. §6.6 shows the definition is the active
ingredient by manipulating it in both directions.

**Why no such software exists.** §3 answers this without speculation. You cannot
train or evaluate a detector on ground truth that was never written down, and
0.085% is not a corpus. It also explains why the tools that do exist target
group leakage and contamination — those *are* documented, mechanically
checkable, and have a vocabulary.

**What a detector should be.** Not an autonomous deleter. The corpus's own
apparent false positives (§6.7) include probable undocumented true positives,
and a tool that silently drops columns would be deleting real signal on the
strength of a category no one has agreed on. The defensible shape is triage:
in our corpus, reviewing 17% of columns surfaces 91% of documented leaks. Pair
that with the two-model agreement rule of §6.4 (precision 0.968 at recall 1.000)
and a human reads a short list.

**The SURROGATE result generalises beyond leakage.** A model asked "is this
value available at time *t*?" answers correctly and unhelpfully whenever the
user's real question is "is using this value legitimate?". Availability and
admissibility are different predicates, and the second has no temporal
definition. We expect the same failure wherever a specification is stated in
terms of the easier predicate.

---

## 8. Limitations

* **The SURROGATE finding rests on six columns across two datasets.** Four
  SUPPORT2 columns and `G1`/`G2`. The convergence across three laboratories is
  striking, and the corroboration is across domains, but the population is
  small. This is the paper's most exposed claim.
* **SUPPORT2 supplies 15 of 46 Stratum A positives**, and CRIME 17 of 30 in
  Stratum B, 9 of those resting on a single sentence about data vintage. Every
  headline is also reported leave-one-dataset-out.
* **The frontier models were run at one shuffle on Stratum A.** Opus's Stratum B
  spread is 0.182, so 0.894 has no interval.
* **The memorisation control covers one model at one seed.** Frontier models are
  uncontrolled for it; §6.3's abstention argument is suggestive, not a control.
* **Precision is a lower bound** (§4.4).
* **22 of 46 subtype codes are analyst-assigned**, and inter-annotator agreement
  on the subtype task is κ = 0.316 — poor, and reported as such. Two codes are
  marked CONTESTED rather than forced.
* **C3 rests on 2 datasets.** Ten of twelve have no author-written description,
  and writing one ourselves would encode the answer.
* **The prediction points are ours.** They are inputs to the benchmark, not
  evidence, and are listed individually so a reader can reject one.
* **Re-identification is not fully excluded.** A post-cutoff corpus would settle
  it and we do not have one.

---

## 9. Conclusion

Feature-level target leakage is documented in six of seven thousand public
datasets. We built the corpus that does not exist, in two evidence strata, one
of which is ground truth by quotation. On it, language models reading column
names beat a correlation baseline tuned on the answers by 0.236 F1, and removing
what they flag recovers the honest AUC three times more accurately than the
baseline does, which misses in both directions.

Their remaining errors are not distributed. Across three frontier models from
three laboratories the intersection is four columns, all of one kind: a prior
estimate of the target, available at prediction time, correctly judged available
by a model reasoning about time. We close the gap with one sentence and reopen
it with another. Capability has solved the part of this problem that is about
time and none of the part that is about a definition.

---

## Appendix outline

* **A.** Full evidence protocol, admissibility tiers, and the reject file.
* **B.** All 76 records: dataset, column, subtype, quotation, locator, coder.
* **C.** All prediction points, one per dataset, with the framing each is drawn
  from.
* **D.** Complete prompts for C0–C7, verbatim.
* **E.** Paraphrase map (306 columns) and its four mechanical checks.
* **F.** Per-model, per-condition, per-dataset, per-seed result tables.
* **G.** The repository sweep: sieve patterns, all 170 hits, and the reading of
  each.
* **H.** Bugs found during this work that changed a reported number (14 of
  them), including two that would have corrupted results silently: caching
  failed API calls as answers (91 cells), and a word-boundary regex that could
  not match a plural and so hid an 11-positive dataset.
* **I.** Downstream protocol: arms, splits, encoders, and per-dataset AUCs.
