# Explicit-source ground truth

Everything here follows one rule: **a column is a positive because the source
says so, not because we read its description and concluded something.** Source
formality is not a criterion. A Kaggle note, an uploader's paragraph and a
peer-reviewed codebook are all admissible; what is required is that the
statement names the column and reaches a conclusion about it.

This replaces the closed-world dictionary rule (`closed_rule.py`), which
classified columns from their descriptions and therefore put our reading back
in the middle of the evidence chain. That rule is retained only as a recorded
negative result.

---

## 1. What was swept

| | UCI | OpenML |
|---|---|---|
| datasets swept (complete repository) | 689 | 6,420 |
| datasets with any leakage-adjacent sentence | 13 | 89 |
| sentences surviving the sieve | 81 | 89 |

Three passes, all over the **whole record**, not just the data dictionary:

* `explicit_scan.py` — sentence level. Two families: **WARN** (the source tells
  you not to use the column, or says it is unknown at prediction time) and
  **DEFINE** (the source says the target was computed from it).
* `section_scan.py` — heading level. A heading such as *"Complications and
  outcomes of myocardial infarction:"* is an explicit statement about every
  column filed beneath it.
* `openml_scan.py` — the same sentence sieve over 6,420 uploader descriptions,
  with column anchoring done by a second request only for datasets that hit.

Two design decisions were forced by failures and are worth keeping:

* **Reading only `variables[].description` is structurally blind.** The
  archive's two most-cited leakage warnings — Bank Marketing's `duration` and
  Student Performance's `G1`/`G2` — live in prose fields. The dictionary-only
  rule found neither, which is most of why it under-fired (13 flags in 1,007
  columns).
* **DEFINE must know the target's name.** Requiring the literal words
  *class* / *label* / *target* as the sentence subject fired **zero** times in
  689 datasets. Authors write derivations with the target's own name: *"The per
  capita violent crimes variable was calculated using population and the sum of
  crime variables … murder, rape, robbery, and assault."*

## 2. What actually exists

Every hit was read individually and classified by **what kind of leakage it
describes**, because most of them are not this paper's kind.

| | UCI | OpenML |
|---|---|---|
| feature-level target leakage | 6 | **0** |
| group leakage (same unit in train and test) | 0 | 2 |
| contamination (train/test overlap) | 0 | 1 |
| identifier column | 3 | 2 |
| false positive on the sieve | 4 | 5 |

**6 datasets in 7,080 — 0.085%.**

The six, and the statement that licenses each:

| id | dataset | evidence |
|---|---|---|
| 222 | Bank Marketing | *"the duration is not known before a call is performed … should be discarded if the intention is to have a realistic predictive model"* |
| 320 | Student Performance | *"G3 is the final year grade (issued at the 3rd period), while G1 and G2 correspond to the 1st and 2nd period grades … more difficult to predict G3 without G2 and G1, but such prediction is much more useful"* |
| 211 | Communities and Crime Unnormalized | target is stated to be the **sum** of eight columns in the same table |
| 579 | Myocardial infarction complications | eleven columns filed under an *outcomes* heading |
| 198 | Steel Plates Faults | seven mutually exclusive fault flags |
| 183 | Communities and Crime | same statement as 211, but the component columns are not in this version — unusable |

222 and 198 were already in the corpus. 183 is unusable. **Three are new.**

## 3. The OpenML result is the sharper one

6,420 datasets produced **ten** distinct leakage-related sentences, and not one
of them is about a feature that encodes the outcome:

| dataset | kind | what it says |
|---|---|---|
| Diabetes130US | group | drop duplicate `patient_nbr` to avoid target leakage |
| SDSS17 | group | drop duplicate `obj_ID` to avoid target leakage |
| sarcos | contamination | train/test overlap in the released files |
| tamilnadu-electricity | identifier | `serviceID` should be removed |
| video_transcoding | identifier | YouTube video `id` should be dropped |

The remaining five are sieve false positives, including one where the trigger
word *"cheating"* turned out to be a **column name** — *central heating* — in a
Munich rent index.

So the largest public repository of tabular ML datasets uses the word
"leakage" exclusively for **splits and identifiers**. The failure mode this
paper is about has no vocabulary there at all.

This is the paper's motivation stated as a measurement rather than an
assertion: there is no labelled corpus of feature-level target leakage to
build a detector from, and the two repositories that would have to supply one
are silent. It also answers "why doesn't this software already exist?" — you
cannot train or evaluate a detector on ground truth that has not been written
down.

## 4. The explicit-source transfer set

`explicit_specs.py` — three datasets, 298 columns, **30 positives**, none of
which existed when C1–C7 were written and none of which contributed a word to
any prompt. Selection was by "the source already says it", a criterion
independent of anything a model does, so this is a held-out score without
needing further argument.

| dataset | rows | cols | positives | subtypes | target |
|---|---|---|---|---|---|
| MI (uci 579) | 1,700 | 122 | 11 | CONSEQUENCE 11 | `ZSN` |
| CRIME (uci 211) | 2,215 | 144 | 17 | REASON 8, TIMING 9 | `violentPerPop` |
| STUDENT (uci 320) | 649 | 32 | 2 | SURROGATE 2 | `G3` |

Every quote in `records_explicit.jsonl` is checked at build time against the
cached source text, and every column against the real CSV header. A misquoted
sentence or a renamed column raises instead of entering the ground truth.

Records carry `explicitness: NAMED_BY_SOURCE`; the existing 46 carry
`INFERRED_FROM_DESCRIPTION`. **Reporting F1 separately on the two strata is the
honest version of the two-F1 idea** — the gap between them is a property of the
labels, not an adjustment anyone applied to the model's answers.

### Stated weakness

CRIME supplies 17 of the 30 positives, and 9 of those rest on a single sentence
about data vintage (1990 predictors, 1995 crime figures) rather than on a
derivation. A pooled F1 over three datasets is close to a measurement of one
dataset, so per-dataset numbers are reported alongside it.

## 5. What the transfer set said

Qwen3-Coder-480B, 39 cells, 100% coverage on every one; 3 seeds on C1/C2/C6.

**The condition effect does not survive seeds.** Per-seed F1 pooled over the
three datasets: C1 = 0.638 / 0.714 / 0.403 — a spread of **0.312**, four times
the ±0.07 measured on the main corpus and larger than any gap between
conditions. CONSEQUENCE recall on MI runs 27% / 100% / 100% across three
shuffles of the same 122 column names, with nothing else changed.

What *is* stable in every condition and every seed: REASON 24/24 and TIMING
27/27, both 100%. The real split is **lexically transparent vs opaque**, not
which prompt was used. `murders` and `rapes` are found by everything;
`FIBR_PREDS` and `OTEK_LANC` are found by nothing reliably.

### Order-averaging, and it works

Majority vote across the three shuffles — one verdict per column, three calls
instead of one, no new prompt and no new evidence:

| cond | pooled cells | majority vote | vote P | vote R |
|---|---|---|---|---|
| C1 | 0.543 | **0.732** | 0.577 | **1.000** |
| C2 | 0.667 | **0.738** | 0.686 | 0.800 |
| C6 | 0.627 | 0.621 | 0.474 | 0.900 |

Three shuffles of the plainest prompt beat every single-shot condition,
including the engineered ones, and reach perfect recall on the explicit-source
positives.

C6 gains nothing, and its precision says why: 0.474. A vote cancels independent
noise, and C6's over-flagging is not noise — it is the derivation clause making
the same error on every shuffle. That is a sharper diagnosis of the clause's
cost than any F1 comparison gave.

## 6. Two bugs found while running this

* **`\bcomplication\b` cannot match "Complications."** The word-boundary
  assertion fails against the plural *s*, so the heading pass returned zero
  blocks on the single dataset it exists for.
* **Failed cells were being cached.** A quota error or an empty completion was
  written to `responses/` like any other answer, so the next run skipped the
  cell and the scorer saw a permanent zero-coverage response the model never
  gave. 91 such cells existed across all runs. The runner no longer caches a
  cell with empty text, and the 91 have been removed. Main-corpus F1s are
  unchanged (an empty cell never parsed, so it never entered a numerator or
  denominator); coverage and attrition counts change.
