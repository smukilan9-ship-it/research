# Results — semantic detection of label-derived columns

**Status: 2026-08-14.** Every number regenerated on the current 12-dataset
corpus. Anything not measured is marked as such.

> Baselines move with the corpus: B3 = 0.812 (6 datasets) -> 0.719 (10) ->
> **0.658 (12)**. Cross-corpus F1 comparisons are NOT valid and are not made.
> Seed variance is **+/-0.07 F1**; several effects reported earlier in this
> project sit inside that band and should not have been quoted to 3 decimals.

---

## 0. Headline

| | value | basis |
|---|---|---|
| best model, C6 | **F1 0.894** (P 0.875, R 0.913) | **claude-opus-5 max**, 12/12 ds |
| tuned baseline B3 | F1 0.658 (P 0.788, R 0.565) | threshold swept on the answers |
| prompt effect C1->C6 | **+0.073** | same model, same corpus |
| REASON recall, 480B | 33-73% (C1) -> **100% every seed** (C6) | 5 seeds |
| paraphrase cost | C6 REASON gain +13pp -> **+7pp** | gemini-3.5, seed 1000 |
| triage | 17% of columns reviewed, **91% of leaks** | union, C1 |
| explicit-source documentation | **6 of 7,080 datasets (0.085%)** | UCI 660 + OpenML 6,420, swept in full |
| downstream inflation | **+0.130 AUC** (rf), +0.133 (gb) | 12 datasets, ALL vs GT-cleaned |
| LLM-cleaned distance to ceiling | **0.025** vs 0.076 for B3 | \|arm − GT\|, rf |
| held-out explicit set | **no condition effect survives 3 seeds** | Qwen-480B; C1 seed spread **0.312 F1** |
| order-averaging (3 shuffles, majority vote) | C1 F1 0.543 -> **0.732**, recall **1.000** | Qwen-480B; **does not generalise**, see §12 |
| **gpt-5.6-sol xhigh, transfer set** | **F1 0.966 at C1, precision 1.000** | 3 datasets, 3 shuffles, seed spread **0.000** |
| **convergent frontier error** | **3 labs miss the same 4 columns**: `sps`,`aps`,`prg2m`,`prg6m` | opus-5 misses ONLY those, 4 of 46 |
| SURROGATE, transfer set | opus C6 **6/6**; **C2 drives BOTH models to 0/6** | adding the prediction point destroys it |

---

## 1. Corpus

**12 datasets, 306 columns, 46 documented positives (15.0%).**
Subtypes: REASON 15, CONSEQUENCE 24, TIMING 5, CONTESTED 2.
24 of 46 subtype codes come from a source; 22 are analyst-assigned.

| dataset | cols | pos | target | role |
|---|---|---|---|---|
| KOI | 40 | 4 | koi_disposition | original |
| DIABETES | 47 | 1 | readmitted | original |
| LC | 29 | 2 | loan_status | original |
| COMPAS | 15 | 4 | two_year_recid | original |
| AI4I | 10 | 4 | Machine failure | original |
| TITANIC | 9 | 2 | survived | original |
| BANK | 16 | 1 | y | expansion |
| SUPPORT2 | 47 | 15 | death | expansion |
| BONEMARROW | 36 | 5 | survival_status | expansion |
| HEARTFAIL | 12 | 1 | DEATH_EVENT | expansion |
| STEEL | 33 | 6 | Other_Faults | **held out** |
| ECHO | 12 | 1 | alive_at_1 | **held out** |

**Attrition:** 20 datasets processed -> 12 with admissible evidence -> 8 with
none (WPBC, CREDIT, ACTG175, POLISH, POSTOP, CTG, CERVICAL, MI). POLISH is
additionally excluded by I2 (columns are `A1`...`A64`). The 8 are a finding, not
an omission: their own literature never states when a column was recorded.

> **MI has since left this list** (§10). Its evidence is a *heading* —
> "Complications and outcomes of myocardial infarction:" over attributes
> 113-124 — and every sieve up to that point read sentences, so none of them
> could see it. The attrition set was measuring the shape of our instrument as
> much as the silence of the sources; one of the eight was recovered the moment
> a pass existed that reads headings. The other seven still stand.

**SUPPORT2 is 15 of 46 positives.** Any pooled number is disproportionately a
statement about that one dataset, which is why every headline is also reported
leave-one-dataset-out.

---

## 2. Baselines on this corpus

| baseline | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| B0 always AVAILABLE | 0.000 | 0.000 | 0.000 | 0 | 0 | 46 |
| B1 name regex | 0.667 | 0.087 | 0.154 | 4 | 2 | 42 |
| B2 univariate AUC | 0.342 | 0.565 | 0.426 | 26 | 50 | 20 |
| **B3 \|correlation\|** | **0.788** | **0.565** | **0.658** | 26 | 7 | 20 |
| B4 missingness asym | 0.150 | 1.000 | 0.261 | 46 | 260 | 0 |

Thresholds swept on the answers -> **upper bounds**. B4 has gone degenerate at
n=12: the best available threshold is 0.000, flagging all 306 columns. Report it
as a dead baseline rather than dropping it.

---

## 3. Models, 12/12 datasets, seeds pooled

| model | C1 F1 | C6 F1 | delta | C6 P | C6 R |
|---|---|---|---|---|---|
| gemini-3.7-flash | 0.803 | **0.876** | +0.073 | 0.918 | 0.839 |
| gemini-3.5-flash | 0.805 | 0.854 | +0.049 | 0.852 | 0.856 |
| Qwen3-Coder-480B | 0.645 | 0.803 | **+0.158** | 0.722 | 0.904 |

gemini-3.5 C7 = 0.864, its best cell.

**C0-C5 are flat**; only C6 moves anything. The full ladder including the
domain-expert scaffold changes gemini-3.7 by at most 0.046 F1.

---

## 4. The central result: the failure is definitional

`gemini-3.5-flash`, 5 seeds pooled, 12 datasets:

| cond | REASON | CONSEQUENCE | TIMING | precision |
|---|---|---|---|---|
| C1 | 47/75 63% | 91/120 76% | 25/25 100% | 0.865 |
| **C6** | **66/75 88%** | 83/105 79% | 25/25 100% | 0.852 |

`Qwen3-Coder-480B`, 5 seeds: REASON **33-73% -> 100% at every seed**, ranges
non-overlapping.

### 4-i. Seed robustness

| model | C1 F1 range | C6 F1 range | C6-C1 worst case |
|---|---|---|---|
| gemini-3.5 | 0.756-0.828 | 0.826-0.870 | **-0.001 (fails)** |
| Qwen3-480B | 0.558-0.747 | 0.766-0.898 | **+0.019 (holds)** |

Pooled F1 is noisy because 24 of 46 positives are CONSEQUENCE, which C6 does not
touch. The **subtype** effect is robust where pooled F1 is not: gemini-3.5's
REASON recall rises at every seed (47-67% vs 80-93%, non-overlapping).

### 4-ii. Leave-one-dataset-out — the KOI dependency

| model | smallest C6 gain | dropping | verdict |
|---|---|---|---|
| gemini-3.7 | +0.011 | KOI | REASON gain falls to **zero** without KOI |
| gemini-3.5 | -0.058 | KOI | effect **inverts** without KOI |
| Qwen3-480B | +0.156 | KOI | **survives**, still +6 REASON columns |

For both Gemini models the entire REASON lift is KOI's four `koi_fpflag_*`
columns. The 480B is the only model where C6 demonstrably generalises beyond
them. Since C6's clause was written after inspecting KOI's failures, this is
the tuning objection, measured.

### 4-iii. Memorisation control, full corpus

`gemini-3.5-flash`, seed 1000, all 306 columns paraphrased (map passes C1-C4):

| | REASON | CONSEQUENCE | precision |
|---|---|---|---|
| original C1 | 10/15 67% | 19/24 79% | 0.878 |
| original C6 | 12/15 80% | 19/24 79% | 0.826 |
| paraphrased C1 | 9/15 60% | 16/24 67% | 0.889 |
| paraphrased C6 | 10/15 67% | 17/24 71% | 0.850 |

**About half the C6 REASON gain is memorisation-assisted**: +13pp on original
names, +7pp on aliases. The effect survives renaming but is materially smaller.

---

### 4a. Where C6 does NOT help — a fourth subtype the taxonomy is missing

On SUPPORT2, C6 changes recall not at all (10/15 at both C1 and C6, seed 1000). The five
it misses, with the model's own stated reasons at C6:

```
prg2m  "Model-based 2-month survival prognostic estimate is computed at baseline"
prg6m  "Model-based 6-month survival prognostic estimate is computed at baseline"
sps    "SUPPORT physiology score is calculated from baseline physiological measurements"
aps    "Acute physiology score is computed from baseline clinical parameters"
dnr    "DNR order status as of baseline day 3 is known at study entry"
```

**The model is factually right.** These are computed at baseline and *are*
available at the prediction point. The source papers excluded them as
"surrogate outcomes and administrative features".

`prg2m` is a **prior estimate of the same target**. It is not later than the
prediction point (not TIMING), it is not a consequence of the outcome (not
CONSEQUENCE), and it was not an input used to determine the label (not REASON,
and so not covered by C6's clause). It is a fourth thing:

> **SURROGATE** — a pre-existing prediction of the same outcome, available at
> the prediction point, which leaks because it was built from information the
> deployed model will not have.

Two consequences, both honest:

1. **A coding error of mine.** I coded all 15 SUPPORT2 positives CONSEQUENCE
   because `records_all.jsonl` said so. At least four are SURROGATE. The
   subtype counts in §4 are affected and the SUPPORT2 block should be recoded.
2. **C6 is incomplete, not wrong.** It closes the REASON gap (63% → 88% on 12 datasets) and
   leaves the SURROGATE gap open.

### 4b. C7 — the prediction was registered, then tested

C7 = C6 plus one clause naming surrogate outcomes. The prediction was written
into `prompts.build_surrogate` **before the run**: it should move columns that
are prior estimates of the target, and nothing else.

`gemini-3.5-flash`, SUPPORT2 (the only model with a complete 12/12 C7 before
the Gemini daily quota was exhausted):

| cond | TP/15 | FP | prg2m | prg6m | sps | aps | dnr |
|---|---|---|---|---|---|---|---|
| C1 | 10 | 1 | – | – | – | – | – |
| C6 | 10 | 1 | – | – | – | – | – |
| **C7** | **12** | **0** | **FLAGGED** | **FLAGGED** | – | – | – |

It moved exactly the two columns that are literally "model-based survival
prognostic estimates", and left `sps`/`aps` (severity scores) and `dnr` (a care
decision) alone — correctly, since those are inputs to prognosis rather than
estimates of the target. False positives fell to zero.

Corpus-wide for that model: CONSEQUENCE 78% → 87%, precision 0.789 → 0.882.

Two controlled interventions, two registered predictions, each moving the
subtype it names and leaving the others where they were. That is the strongest
form the central claim can take on this corpus.

**Caveat:** C7's REASON recall drops back to 44% for `gemini-3.5-flash`, i.e.
the surrogate clause appears to displace some of C6's derivation gain in the
weaker model. `gemini-3.7-flash` C7 is 8/12 datasets (quota) and is **not**
reported. Whether the two clauses compose or compete is unresolved and needs
the 3.7 run completed.

That C6 raised precision on SUPPORT2 (1 false positive → 0) while leaving
recall untouched is consistent with this: the clause sharpened the criterion it
names and was silent about the one it does not.

---

## 5. The screens are blind in opposite directions

| subtype | B3 \|correlation\| | LLM C1 | union |
|---|---|---|---|
| REASON | **89%** | 44% | 89% |
| CONSEQUENCE | 48% | **78%** | 87% |
| TIMING | 50% | **100%** | 100% |

The mechanism is legible. A REASON column *determines* the label, so it
correlates with it almost by construction and a correlation screen cannot miss
it — but it is temporally prior, so a model reasoning about availability calls
it available. A CONSEQUENCE column is often weakly correlated (`TITANIC.body`
is 0.014) yet semantically obvious.

Found **only** by correlation (C1): the four `koi_fpflag_*`, `SUPPORT2.prg6m`,
`SUPPORT2.dnr`.
Found **only** by the model: 11 columns, including `LC.collection_recovery_fee`,
`COMPAS.r_days_from_arrest`, `TITANIC.body`, and 6 SUPPORT2 cost/stay columns.

| screen (C6) | P | R | F1 |
|---|---|---|---|
| B3 alone | 0.852 | 0.605 | 0.708 |
| LLM alone | 0.889 | 0.842 | 0.865 |
| union | 0.810 | 0.895 | 0.850 |
| **both agree** | **1.000** | 0.553 | 0.712 |

**Where the two screens agree, precision is 1.000** — 21 columns, zero false
positives out of 223 negatives.

---

### 5a. Superseded

The cross-model table that stood here used 10-dataset figures and is
replaced by section 3 above.

---

## 6. Triage, not deletion

Autonomous deletion is the wrong framing: B3 buys its F1 by proposing to delete
`sex`. Stated as reviewer effort instead:

- **Tier 1 — both screens agree.** 21 columns, precision 1.000. Zero false
  positives on this corpus.
- **Tier 2 — either screen fires.** 42 of 261 columns (16%) to review, catching
  34 of 38 leaks (89%).
- **Missed by both:** 4 — `DIABETES.discharge_disposition_id`, `SUPPORT2.sps`,
  `SUPPORT2.aps`, `SUPPORT2.prg2m`.

Reading 16% of columns to find 89% of the leaks is the feasibility number.

---

## 7. Memorisation control

Applies to the **original six only** (150 columns); the four new datasets have
no paraphrase map yet.

| | original | paraphrased |
|---|---|---|
| Qwen3-Coder-480B C4 | 0.828 | **0.400** |
| gemini-3.7-flash C4 | 0.828 | **0.828** |

Qwen collapses; Gemini does not. AI4I is the tell: Qwen goes 4/4 → 0/4 when
`TWF` becomes `tw_f` — same letters, one inserted underscore.

**This does not establish that Gemini generalises.** Its own reasons show it
decoding `hd_f` → "heat dissipation failure" and `os_f` → "overstrain" — AI4I's
specific documented taxonomy. The control preserves domain by design, so it
separates string-retrieval from rule-following and does **not** rule out
dataset re-identification. Settling that needs a dataset published after the
training cutoff.

---

## 8. Bugs found and fixed this session

Each one changed, or would have changed, a reported number.

1. **C3 was C2.** `spec_bundle` hardcoded `description = ""`, so the description
   condition carried no description, and C5 never got one either. Now wired,
   and a dataset without a documented description **skips C3 loudly** instead of
   silently duplicating C2.
2. **Paraphrased runs scored against original column names.** Aliased verdicts
   joined to original truth match nothing, so every positive read as a miss and
   models gained phantom zero-recall cells. Now separated, with a hard JOIN
   ERROR if keys ever fail to intersect.
3. **Duplicate C4 cells.** Fixing (1) changed the C4 prompt for the two datasets
   that have descriptions, producing a second cached cell and double-counting
   them under two different prompts. Now de-duplicated by newest.
4. **Partial cells scored as complete.** Athene reported F1 1.000 on 2 of 6
   datasets and looked like the best model in the benchmark. Coverage is now
   printed on every row and mismatches are marked PARTIAL.
5. **Baseline measured on a different corpus.** `vs B3` compared 10-dataset
   models against a bar from a different corpus (0.812 / 0.719 vs the
   correct 0.658).
6. **`blind` had an empty denominator** in the paraphrase arm — reported 0/0,
   which reads as "found none" but meant "never checked".
7. **Gemini errors were undiagnosable.** Google wraps errors in a top-level
   list, so `"error" in d` was false and every failure surfaced as a TypeError
   instead of "Please pass a valid API key".
8. **503 was not treated as retryable**, so 7 cells failed on first contact
   instead of rotating to another key.
9. **Paraphrase map made two positives harder.** The C3 self-check caught
   `discharge_disposition_id` and `recoveries` losing a sieve marker under
   renaming, which would have inflated the memorisation decrement.
10. **Evidence sieve ranked identifier-removal as the strongest finding** —
    real leakage, wrong kind — while filing the one genuinely useful statement
    as weak.
11. **Dictionary sieve matched author surnames** from reference lists as column
    names. Fixed by anchoring on the distributed column list (I5).
12. **Row-boundary bug** let `Rbodymass` and `Disease` inherit licensing
    phrases from neighbouring dictionary rows.
13. **Failed cells were cached as answers.** A quota error or an empty
    completion was written to `responses/` like any other response, so the next
    run skipped the cell and the scorer saw a permanent zero-coverage answer the
    model never gave. **91 such cells** existed across all runs. The runner now
    refuses to cache a cell with empty text and the 91 are deleted. F1s are
    unchanged — an empty cell never parsed, so it entered no numerator or
    denominator — but coverage and attrition counts do change, and the
    "gemini-3.7 has effectively one seed" note in §9 was partly this bug rather
    than quota alone.
14. **`\bcomplication\b` cannot match "Complications".** The trailing
    word-boundary fails against the plural *s*, so the heading pass returned
    zero blocks on the one dataset it was written for. Cost: it made a real
    11-positive dataset look like it had no evidence.

Sanity suite (`sanity10.py`, 10 checks incl. target-in-features, positives
absent from file, positive identical to target, constant positives, missing
subtype codes): **0 failures, 0 warnings.**

---

## 9. What is NOT established

- **Seeds: 5 for gemini-3.5 and Qwen-480B; effectively 1 for gemini-3.7**
  (quota). Seed variance is +/-0.07 F1, so the 0.876 headline has no interval.
- **Paraphrase now covers all 12 datasets** (map passes C1-C4 on 306
  columns), but only for gemini-3.5 at one seed. Other models and seeds are
  uncontrolled for memorisation.
- **Re-identification is not excluded** (§7). This is the biggest threat to the
  feasibility claim and needs a post-cutoff dataset.
- **C3 rests on 2 datasets.** Ten of the twelve have no documented description
  at all, and writing one ourselves would encode the answer.
- **22 of 46 subtype codes are analyst-assigned**, not source-stated. Two are
  marked CONTESTED rather than forced, and at least four SUPPORT2 codes are
  wrong (SURROGATE mis-coded as CONSEQUENCE, see 4a).
- **Prompt developed on these datasets, and the transfer test was
  inconclusive.** C6's wording was written after inspecting KOI/AI4I/DIABETES
  failures. The held-out REASON dataset (STEEL) has lexically transparent
  columns that models already catch at C1, so there was no gap for C6 to close.
  For both Gemini models the entire REASON lift is KOI's four columns; only the
  480B generalises beyond them. This is the paper's weakest point.
- **The false positives may be true.** Four columns flagged by both Gemini
  models (`ECHO.survival`, `BONEMARROW.Relapse`, `extcGvHD`, `IIIV`) look like
  real post-outcome leaks with no quotable documentation. Precision is therefore
  a lower bound that partly measures harvest completeness.
- **Pro-tier models untested** — all 9 keys returned 429 for
  `gemini-3.1-pro-preview` and `gemini-pro-latest`; free tier has no Pro quota.
- **The explicit-source transfer set has no model scores yet** (§10). All nine
  Gemini keys are at their daily quota and Featherless allows one concurrent
  call, so the 3-dataset run is still in flight.

---

## 10. Explicit-source ground truth, and how little of it exists

Full detail in `EXPLICIT_SOURCES.md`. The rule: a column is a positive because
**the source names it**, not because we read its description and concluded
something. Source formality is not a criterion — an uploader's paragraph counts
the same as a codebook — but the statement must name the column and reach a
conclusion about it.

### 10a. The sweep

Both public repositories, complete: **660 UCI records and 6,420 active OpenML
descriptions.** Three passes over the *whole* record, not just the data
dictionary: WARN sentences ("should be discarded", "not known before"), DEFINE
sentences ("the target was calculated using the sum of..."), and outcome
*headings*. Every hit was read.

Two things had to be got right, and both were got wrong first:

* Reading only `variables[].description` is **structurally blind** — the
  archive's two most-cited warnings (`duration`, `G1`/`G2`) live in prose. This
  is most of why the earlier closed-world dictionary rule fired on only 13 of
  1,007 columns.
* DEFINE has to know the **target's own name**. Requiring the literal words
  *class*/*label*/*target* as the subject fired **zero** times in 660 datasets;
  authors write "The per capita violent crimes variable was calculated using…".

### 10b. The result

| | UCI | OpenML |
|---|---|---|
| datasets swept | 660 | 6,420 |
| feature-level target leakage, explicitly documented | 6 | **0** |
| group leakage | 0 | 2 |
| train/test contamination | 0 | 1 |
| identifier column | 3 | 2 |
| sieve false positive | 4 | 5 |

**6 in 7,080 datasets — 0.085%.** Two were already in the corpus (BANK, STEEL),
one is unusable (uci 183 ships the statement but not the columns), so **three
are new**.

OpenML's ten distinct leakage sentences are *entirely* about splits and
identifiers — duplicate `patient_nbr`, duplicate `obj_ID`, `serviceID`, a
YouTube video `id`, one train/test overlap. One trigger word turned out to be a
column name: *cheating*, meaning **central heating**, in a Munich rent index.

This is the paper's motivation as a measurement rather than an assertion. The
largest public repository of tabular datasets has no vocabulary for the failure
mode at all, so there is no corpus to train or evaluate a detector on — which
is a direct answer to "why doesn't this software already exist?", and a
justification for the expense of the hand-curated corpus (50 PDFs, 46
positives) as the only route rather than a preference.

### 10c. The transfer set

`explicit_specs.py` — **3 datasets, 298 columns, 30 positives**, none of which
existed when C1–C7 were written and none of which contributed a word to any
prompt. The selection criterion is "the source already says it", which is
independent of anything a model does, so this is held out without further
argument.

| dataset | rows | cols | pos | subtypes | target |
|---|---|---|---|---|---|
| MI (uci 579) | 1,700 | 122 | 11 | CONSEQUENCE 11 | `ZSN` |
| CRIME (uci 211) | 2,215 | 144 | 17 | REASON 8, TIMING 9 | `violentPerPop` |
| STUDENT (uci 320) | 649 | 32 | 2 | SURROGATE 2 | `G3` |

Every quote is checked against the cached source text at build time and every
column against the real CSV header; a misquote or a renamed column raises
rather than entering the ground truth.

Records carry `explicitness: NAMED_BY_SOURCE`; the existing 46 carry
`INFERRED_FROM_DESCRIPTION`. **Reporting F1 on the two strata separately is the
defensible version of the two-F1 idea** — the gap is a property of the labels,
not an adjustment applied to anyone's answers.

**Stated weakness:** CRIME supplies 17 of 30 positives and 9 of those rest on a
single sentence about data vintage (1990 predictors, 1995 crime figures) rather
than on a derivation, so a pooled F1 here is close to a measurement of one
dataset. Per-dataset numbers are reported alongside it.

### 10d. Score on the transfer set — the condition effect does not survive seeds

Qwen3-Coder-480B, 39 cells, **100% coverage on every one**. C1/C2/C6 have 3
seeds; C0/C4/C5/C7 have 1 and are shown only for completeness.

| cond | seeds | F1 | P | R |
|---|---|---|---|---|
| C0 names only | 1 | 0.595 | 0.500 | 0.733 |
| C1 +target | **3** | 0.543 | 0.387 | 0.911 |
| C2 +prediction point | **3** | 0.667 | 0.596 | 0.756 |
| C4 +sample rows | 1 | 0.468 | 0.344 | 0.733 |
| C5 expert scaffold | 1 | 0.548 | 0.531 | 0.567 |
| C6 +derivation | **3** | 0.627 | 0.488 | 0.878 |
| C7 +surrogate | 1 | 0.636 | 0.583 | 0.700 |

**This is a null result and it is reported as one.** Per-seed F1, pooled over
the three datasets within each seed:

| cond | s1000 | s1001 | s1002 | spread |
|---|---|---|---|---|
| C1 | 0.638 | 0.714 | 0.403 | **0.312** |
| C2 | 0.635 | 0.633 | 0.746 | 0.112 |
| C6 | 0.711 | 0.644 | 0.535 | 0.176 |

A single seed said C1 0.638 -> C6 0.711 and made a clean story. Three seeds
say the C1 spread alone is **0.312 F1** — four times the +/-0.07 band measured
on the main corpus, and larger than every condition difference in the table.
Nothing about the ladder can be claimed here.

The instability is concentrated in exactly one place. CONSEQUENCE recall on MI,
by seed:

| cond | s1000 | s1001 | s1002 |
|---|---|---|---|
| C1 | 27% | 100% | 100% |
| C2 | 73% | 0% | 45% |
| C6 | 73% | 91% | 36% |

Same model, same prompt, same eleven columns — **only the presentation order of
the 122 column names differs**, and recall moves between 0% and 100%.

**What is stable across every condition and every seed:** REASON 24/24 and
TIMING 27/27, both at 100%. SURROGATE 6/6 except where the prompt breaks
outright. The lexically transparent positives are found by everything; the
opaque ones are found by nothing reliably.

**Why MI is the hard case:** its eleven positives are Russian-language
abbreviations — `FIBR_PREDS`, `OTEK_LANC`, `RAZRIV`, `DRESSLER` — so no lexical
cue exists and the model must reason about what an ICU record contains at
admission. CRIME sits at 0.85-0.90 and STUDENT at 0.667 in essentially every
cell; MI is the entire variance of this set.

**What this costs the paper, stated plainly.** §4's mechanism (C6 lifts REASON)
was measured on the corpus the clause was written against. On data selected by
a criterion independent of any model, the condition effects are inside the
noise. The claim that survives is narrower than the one this project has been
carrying: *models find lexically transparent leaks under any prompt, and their
handling of opaque ones is order-dependent to the point of being unusable
single-shot.* Order-averaging — several shuffles per dataset, majority vote —
looks less like a refinement and more like a requirement, and it is untested.

C4 and C5 are single-seed and, given a spread of 0.312, their apparent damage
cannot be distinguished from a bad shuffle. The earlier reading of them in this
file was wrong and is withdrawn.

### 10e. Order-averaging, and it works

If the variance is caused by column order, average over it. One verdict per
column by majority vote across the three shuffles, instead of scoring each
shuffle separately. No new evidence, no new prompt, three calls instead of one.

| cond | pooled cells | **majority vote** | vote P | vote R |
|---|---|---|---|---|
| C1 | 0.543 | **0.732** | 0.577 | **1.000** |
| C2 | 0.667 | **0.738** | 0.686 | 0.800 |
| C6 | 0.627 | 0.621 | 0.474 | 0.900 |

**C1 gains 0.19 F1 and reaches perfect recall** on the explicit-source
positives; C2 gains 0.07 and is the best cell in the whole table. Three
shuffles of the plainest prompt beat every single-shot condition, including the
engineered ones.

C6 does not benefit, and the reason is visible in its precision (0.474): its
errors are *correlated* across shuffles. A vote cancels independent noise, and
C6's over-flagging is not noise — it is the clause doing the same wrong thing
every time. That is a sharper diagnosis of the clause's cost than the F1
comparison gave.

**This changes what the paper should recommend.** Ordering variance is a larger
lever than prompt content on held-out data, it is trivially cheap, and it is
not something the literature on LLM tabular reasoning currently reports for
this task. Two caveats: three seeds is the minimum that admits a majority, and
this is one model on three datasets, so the effect size is not established —
only its sign and rough magnitude.

---

## 11. What the leakage costs downstream

`downstream.py`. Four arms differing **only** in which columns are present — no
tuning, no per-arm choices. Group-aware 5-fold splits where a unit repeats
(`patient_nbr`, `member_id`, `id`). Two learners, because leakage is a property
of the data and should show up under both.

| arm | columns |
|---|---|
| ALL | everything — what a practitioner gets by default |
| GT | documented positives removed — the honest ceiling |
| MODEL | what gemini-3.7-flash flagged at C6 removed |
| B3 | what the correlation baseline flagged removed (threshold swept on the answers, so a best case for it) |

**Inflation = AUC(ALL) − AUC(GT), over the 12 datasets:**

| learner | mean | median | max |
|---|---|---|---|
| random forest | **0.130** | 0.109 | 0.357 (BONEMARROW) |
| gradient boosting | **0.133** | 0.123 | 0.374 |

Leaving the documented leaks in buys about **0.13 AUC of nothing**, and the
effect is the same size under both learners.

**Does an automatic arm land on the honest ceiling?** The ratio
(ALL−arm)/(ALL−GT) reads ~1.00 for both arms and is useless — an arm that
overshoots by deleting a legitimate column also scores 1.00. Distance from GT
does not have that blind spot:

| learner | mean \|LLM−GT\| | mean \|B3−GT\| | LLM closer | B3 closer | tie |
|---|---|---|---|---|---|
| rf | **0.025** | 0.076 | 7 | 1 | 4 |
| gb | **0.028** | 0.073 | 7 | 1 | 4 |

Per dataset (rf), sorted by inflation:

| dataset | ALL | GT | MODEL | B3 | inflation |
|---|---|---|---|---|---|
| BONEMARROW | 0.977 | 0.620 | 0.536 | 0.682 | 0.357 |
| COMPAS | 0.979 | 0.702 | **0.702** | 0.749 | 0.277 |
| LC | 0.928 | 0.736 | **0.736** | 0.909 | 0.191 |
| TITANIC | 0.993 | 0.844 | **0.844** | 0.750 | 0.149 |
| BANK | 0.932 | 0.784 | **0.784** | 0.784 | 0.148 |
| HEARTFAIL | 0.901 | 0.789 | **0.789** | 0.789 | 0.113 |
| STEEL | 1.000 | 0.894 | **0.894** | 0.938 | 0.105 |
| SUPPORT2 | 0.975 | 0.878 | 0.886 | 0.828 | 0.097 |
| KOI | 0.998 | 0.932 | **0.932** | 0.932 | 0.066 |
| ECHO | 0.965 | 0.935 | 0.743 | 0.504 | 0.030 |
| DIABETES | 0.699 | 0.682 | 0.699 | 0.699 | 0.018 |
| AI4I | 0.985 | 0.970 | **0.970** | 0.970 | 0.015 |

The baseline misses in **both directions**, which is the point: it under-drops
on LC (0.909 vs a ceiling of 0.736 — it keeps `recoveries`) and over-drops on
TITANIC (0.750 vs 0.844 — it deletes `sex`) and SUPPORT2. A correlation
threshold cannot separate "correlated because it caused the label" from
"correlated because it predicts the label", which is the whole distinction.

**Where the LLM overshoots:** ECHO (0.743 vs 0.935) and BONEMARROW (0.536 vs
0.620), the two datasets where it flags columns we have no documentation for.
§9 already notes those flags are probably *correct* and undocumented, so this
row is as likely to be a limit of the ground truth as an error by the model —
and that ambiguity is exactly why the explicit-source stratum in §10 matters.

**Not claimed:** that dropping the flagged columns is the right remedy. The
honest ceiling is what a careful analyst would have got; recovering it
automatically is useful, but the arms differ in columns only and no arm was
tuned, so these are not performance claims about any deployed pipeline.

---

## 12. gpt-5.6-sol at extra-high effort — the frontier run

Run through the chat UI with sub-agents, one condition per session, prompts
verified byte-identical to the API runs (24 regenerated, 18 hash-matched
against cells already on disk). **51 cells, 100% coverage on every one, zero
invented column names, clean JSON throughout** — better instrument discipline
than any API model in this project managed.

### 12a. Main corpus, 12 datasets

| model | C1 | C6 | delta | C6 P | C6 R |
|---|---|---|---|---|---|
| gemini-3.7-flash | 0.803 | **0.876** | +0.073 | 0.918 | 0.839 |
| **gpt-5.6-sol xhigh** | **0.805** | 0.857 | +0.052 | 0.867 | 0.848 |
| gemini-3.5-flash | 0.805 | 0.854 | +0.049 | 0.852 | 0.856 |
| Qwen3-Coder-480B | 0.645 | 0.803 | +0.158 | 0.722 | 0.904 |
| B3 baseline | — | 0.658 | — | 0.788 | 0.565 |

Subtype recall — **the registered prediction, on a third independent model
family**:

| cond | REASON | CONSEQUENCE | TIMING | CONTESTED | precision |
|---|---|---|---|---|---|
| C1 | 10/15 **67%** | 18/24 75% | 5/5 100% | 2/2 100% | 0.854 |
| C6 | 14/15 **93%** | 18/24 75% | 5/5 100% | 2/2 100% | 0.867 |

REASON 67% -> 93%; CONSEQUENCE+TIMING 79% -> 79%, dead flat; precision *up*.
The mechanism now replicates across Google, Alibaba and OpenAI models. That is
the strongest form the §4 claim has ever been in.

### 12b. It abstains rather than guessing, and that is the KOI story told properly

Abstentions on documented columns:

| dataset | C1 | C6 |
|---|---|---|
| KOI | **40 / 40** | **0** |
| DIABETES | 39 / 47 | 37 |
| LC | 4 / 29 | 0 |
| all others | 0 | 0 |
| **total** | **83** | **38** |

At C1 it declined the entire KOI table — *"the deployment prediction point is
unspecified, so it cannot be established"* — and at C6 it flagged all four
`koi_fpflag_*` columns correctly. §4-ii showed that both Gemini models' whole
REASON lift is those four KOI columns, which reads as tuning. This is the same
lift arrived at differently: the model **refuses the underspecified question**
rather than guessing at it, and answers once the criterion is stated. Refusal
is not something a memorised answer key produces.

### 12c. Transfer set — the null does not hold for this model

| model | C1 | C2 | C6 | C6 majority-vote |
|---|---|---|---|---|
| **gpt-5.6-sol xhigh** | **0.966** (P 1.000, R 0.933) | 0.804 | 0.926 | **0.984** (P 0.968, R 1.000) |
| Qwen3-Coder-480B | 0.543 | 0.667 | 0.627 | 0.621 |

Per dataset:

| cond | CRIME | MI | STUDENT |
|---|---|---|---|
| C1 | **1.000** | **1.000** | 0.000 |
| C2 | **1.000** | 0.653 | 0.000 |
| C6 | **1.000** | 0.880 | 0.615 |

**Precision 1.000 at C1: 84 true positives, zero false positives** across 27
cells and 894 column judgments. It flagged the documented positives and
nothing else. That is also an independent check on the ground truth — a
frontier model, given no documentation, reproduced the source-stated labels
exactly.

MI is the dataset that broke the 480B (F1 0.291, Russian-language
abbreviations, no lexical cue). gpt-5.6 gets **1.000 on it at C1**, on all
three shuffles.

### 12d. Seed spread is 0.000, so §10d's null was model-specific

| cond | s1000 | s1001 | s1002 | spread | (480B spread) |
|---|---|---|---|---|---|
| C1 | 0.966 | 0.966 | 0.966 | **0.000** | 0.312 |
| C2 | 0.836 | 0.836 | 0.747 | 0.089 | 0.112 |
| C6 | 0.949 | 0.984 | 0.857 | 0.126 | 0.176 |

**Two conclusions from earlier today are now wrong and are withdrawn:**

1. *"Ordering variance is a larger lever than prompt content."* It is not, in
   general. It is a property of Qwen-480B on this set. gpt-5.6 returns an
   identical answer under three shuffles. Order-averaging is a remedy for weak
   models, not a requirement of the task.
2. *"No condition effect survives on held-out data."* It does not survive for
   the 480B. For gpt-5.6 the ladder is legible: C1 already near ceiling, C2
   **hurts** (precision 0.706 — the stated prediction point makes it flag MI's
   admission-time covariates), C6 recovers and adds the only thing missing.

### 12e. The finding: at the frontier, the error profile is *entirely* definitional

Subtype recall on the transfer set:

| cond | CONSEQUENCE | REASON | SURROGATE | TIMING |
|---|---|---|---|---|
| C1 | 33/33 **100%** | 24/24 **100%** | **0/6 0%** | 27/27 **100%** |
| C2 | 33/33 **100%** | 24/24 **100%** | **0/6 0%** | 27/27 **100%** |
| C6 | 33/33 **100%** | 24/24 **100%** | 4/6 67% | 27/27 **100%** |

STUDENT scores **0.000** at C1 and C2 for one reason only: it calls `G1` and
`G2` AVAILABLE. They are — prior-period grades exist before the final grade.
It is not making a mistake about time; it does not hold the category.

The main corpus says the same thing independently. Every C6 miss, all seven of
them across 46 positives:

```
SUPPORT2   sps, aps, surv2m, surv6m, prg2m, prg6m     <- all six SURROGATE
DIABETES   discharge_disposition_id                    <- abstained
```

Nothing else. No column missed because the model failed to notice it was
recorded after the outcome. A frontier model at maximum reasoning effort,
given only column names and a target, makes **exactly two kinds of error: it
misses prior estimates of the target, and it declines underspecified
questions.**

§4a introduced SURROGATE as "a fourth subtype the taxonomy was missing",
inferred from five SUPPORT2 columns on one model. It is now the *only*
remaining failure mode of the best model tested, confirmed on a held-out
corpus it has never seen, and reachable — 0/6 -> 4/6 — by stating the
criterion. That is the paper's thesis in its strongest available form: the
failure is definitional, not perceptual, and it survives capability scaling.

---

## 13. claude-opus-5 at max effort — and the convergent failure

Same protocol as §12: chat UI, sub-agents, one condition per session, prompts
byte-identical. **51 cells, 100% coverage on every one, zero invented columns.**

### 13a. New best on the main corpus

| model | C1 | C6 | delta | C6 P | C6 R | abstentions |
|---|---|---|---|---|---|---|
| **claude-opus-5 max** | **0.844** | **0.894** | +0.050 | 0.875 | **0.913** | 2 |
| gemini-3.7-flash | 0.803 | 0.876 | +0.073 | 0.918 | 0.839 | 0 |
| gpt-5.6-sol xhigh | 0.805 | 0.857 | +0.052 | 0.867 | 0.848 | 83 |
| gemini-3.5-flash | 0.805 | 0.854 | +0.049 | 0.852 | 0.856 | 0 |
| Qwen3-Coder-480B | 0.645 | 0.803 | +0.158 | 0.722 | 0.904 | 24 |
| B3 baseline | — | 0.658 | — | 0.788 | 0.565 | — |

| cond | REASON | CONSEQUENCE | TIMING | CONTESTED | precision |
|---|---|---|---|---|---|
| C1 | 14/15 **93%** | 17/24 71% | 5/5 100% | 2/2 100% | 0.864 |
| C6 | 15/15 **100%** | 20/24 **83%** | 5/5 100% | 2/2 100% | 0.875 |

Highest C1 REASON of any model (93%), and the only model where C6 also lifts
**CONSEQUENCE** (+12pp) rather than leaving it flat. Precision rises too.

### 13b. Transfer set — the two frontier models are opposites

| model | C1 | C2 | C6 | C6 majority-vote |
|---|---|---|---|---|
| gpt-5.6-sol xhigh | **0.966** (P **1.000**) | 0.804 | 0.926 | **0.984** |
| claude-opus-5 max | 0.762 (P 0.624, R 0.978) | 0.697 | 0.861 (P 0.756, **R 1.000**) | 0.857 |

Per dataset at C6: opus is **recall 1.000 on all three** (CRIME 1.000, MI 0.717,
STUDENT 0.800); gpt is precision-first (MI 0.880, STUDENT 0.615). Opus finds
every documented positive and pays 29 false positives; gpt flags fewer and is
almost never wrong.

**They are nested, not complementary.** Opus's flagged set strictly *contains*
gpt's at both C1 and C6, so union = opus and agreement = gpt exactly. Requiring
agreement recovers gpt's precision (0.968) at **no recall cost** (1.000) — a
usable two-model rule, but it is not combining two different views.

### 13c. SURROGATE is solved — and C2 unsolves it, in both labs

Recall by subtype on the transfer set:

| cond | model | CONSEQUENCE | REASON | **SURROGATE** | TIMING |
|---|---|---|---|---|---|
| C1 | opus | 33/33 100% | 24/24 100% | **4/6 67%** | 27/27 100% |
| C1 | gpt | 33/33 100% | 24/24 100% | **0/6 0%** | 27/27 100% |
| **C2** | opus | 33/33 100% | 24/24 100% | **0/6 0%** | 27/27 100% |
| **C2** | gpt | 33/33 100% | 24/24 100% | **0/6 0%** | 27/27 100% |
| C6 | opus | 33/33 100% | 24/24 100% | **6/6 100%** | 27/27 100% |
| C6 | gpt | 33/33 100% | 24/24 100% | **4/6 67%** | 27/27 100% |

Two things here, and the second is the more interesting.

**opus-5 at C6 is the first model in this project to reach 6/6 on SURROGATE.**
It flags `G1`/`G2` on STUDENT and every surrogate column on the transfer set.

**C2 drives SURROGATE to exactly 0/6 in both frontier models, independently.**
Stating the prediction point makes the model reason correctly — a prior-period
grade *does* exist before the final grade — and that correct reasoning is what
destroys the detection. Adding information makes it worse, reproducibly, across
two labs. That is a mechanism, not noise, and it is the sharpest evidence in
the project that the failure is definitional rather than perceptual.

### 13d. The convergent error — three labs, the same four columns

Every C6 miss on the main corpus, all 46 positives, seed 1000:

| model | missed | which |
|---|---|---|
| **claude-opus-5 max** | **4** | `SUPPORT2.sps`, `aps`, `prg2m`, `prg6m` |
| gemini-3.7-flash | 6 | those four + `SUPPORT2.dnr` + `DIABETES.discharge_disposition_id` |
| gpt-5.6-sol xhigh | 7 | those four + `SUPPORT2.surv2m`, `surv6m` + `DIABETES.discharge_disposition_id` |

**opus-5 misses four columns out of forty-six, and all four are SURROGATE.**
Not one column in the corpus is missed by it for any other reason.

The intersection across Google, OpenAI and Anthropic — three architectures,
three training pipelines, three labs — is **exactly `sps`, `aps`, `prg2m`,
`prg6m`**, the columns §4a flagged when the subtype was first noticed on a
single model. Frontier capability has closed REASON, CONSEQUENCE and TIMING to
ceiling and left this untouched.

### 13e. Order stability is a model property, not a task property

Per-seed F1 on the transfer set:

| model | C1 spread | C6 spread |
|---|---|---|
| gpt-5.6-sol xhigh | **0.000** | 0.126 |
| claude-opus-5 max | 0.182 | 0.214 |
| Qwen3-Coder-480B | 0.312 | 0.176 |

gpt returns an identical answer under three shuffles; opus does not; the 480B is
worse than either. §10e's order-averaging recommendation stands only as a
remedy for models that need it, and cannot be stated as a property of the task.

### 13f. What this does to the paper

The benchmark now has a **live, unsolved item that three frontier models fail
identically**, and a condition (C2) that reliably *causes* the failure. That is
a better artefact than a benchmark everything saturates:

* C6 on the main corpus is close to saturated — opus 0.894 with four misses.
* The transfer set is saturated for gpt at C1 (F1 0.966, precision 1.000).
* SURROGATE is not saturated by anything, and is reachable by prompt (0/6 ->
  6/6), which makes it a *definitional* gap rather than a capability ceiling.

The paper's claim should now be stated at that level: **model capability has
closed every subtype of feature-level target leakage that is about time, and
none of the one that is about a prior estimate of the target — because the
models' reasoning about time is correct and the category is not a temporal
one.**
