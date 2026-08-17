# The corpus — strata, mechanisms, coding rules

## The four mechanisms

Cut for **codability against a written source**, not for coverage.

| mechanism | the column… | example |
|---|---|---|
| **REASON** | was an input used to assign the label | `TWF`/`HDF`/`PWF`/`OSF` → `Machine failure` |
| **CONSEQUENCE** | exists *because* the outcome occurred | `body` (recovery number) → `survived` |
| **TIMING** | is recorded after the prediction point | 1995 crime counts → a 1995 rate predicted from a 1990 census |
| **UPSTREAM** | computed by a process that consumed outcome information | declared; not separately measured |

**Four, not five.** A fifth, SURROGATE (*a prior estimate of the same target*),
was proposed and **withdrawn** when the §4.4 audit found it could not survive its
own evidence.

### The arrow test — the single most useful sentence for coding

> **REASON is about how the LABEL was made. CONSEQUENCE is about how the COLUMN
> was made.**

### Precedence, for overlapping mechanisms

1. **REASON** if the quotation says the target was computed from the column;
2. else **CONSEQUENCE** if the column exists because the outcome occurred;
3. else **TIMING**;
4. else **CONTESTED**.

## The four strata, never pooled

| stratum | what admits a record | size |
|---|---|---|
| **A** — main | coded from the dataset's own documentation | 12 datasets, 306 columns, 40 positives |
| **B** — transfer, held out | the **source names the leaking column itself** | 3 datasets, 298 columns, 28 positives |
| **C** — external validation | found by applying the frozen instruments to four other documentation cultures | 2 admissible records + hand-nominated diagnostics |
| **D** — mechanically verified | a rule reconstructs the target from the column on **every row** | 8 records, agreement 1.000 |

They are never averaged together, because "a source names this column" and "we
read a source's description" is a property of the labels, not noise to average
away.

### Stratum A

`AI4I BANK BONEMARROW COMPAS DIABETES ECHO HEARTFAIL KOI LC STEEL SUPPORT2
TITANIC` — 306 columns, 40 positives.

### Stratum B

`CRIME` (144 cols, 17 pos), `MI` (122, 11), `STUDENT` (32, **0**) — 298 columns,
28 positives. STUDENT contributes zero positives and is kept: a transfer set
with no negatives-only dataset would be a different test.

**Concentration is a real limitation, stated in §6.5:** SUPPORT2 supplies 9 of
40 Stratum-A positives; CRIME supplies 17 of 28 in Stratum B, nine of them
resting on one sentence. This is why uncertainty resamples **datasets**, not
columns.

Subtype totals across both: `REASON 22, CONSEQUENCE 30, TIMING 14, CONTESTED 2`.

### Stratum D and its admission criterion

An exact rule is **not sufficient**. UCI marks each column `Target`, `Feature`,
`ID` or `Other`, and two of the eight exact-rule hits have a leak column the
archive itself marks `Target`. Predicting one designated outcome from another is
not this paper's failure mode.

- **MI is excluded** — twelve targets in one table; admitting one pair would
  license 132, and choosing one would be arbitrary.
- **STEEL is kept and disclosed** — the seven fault columns are one seven-class
  problem in a single CSV, a modeller really does pick `Other_Faults` as the
  label, and the role metadata is a warning nobody reads. The paper's subject is
  warnings nobody reads.
- **ChessFraud's `is_cheating_player_game` is left uncoded** on the same
  principle: *a column that is itself an outcome is not a feature.*

Scoring the role field as a detector reproduces §4.4's negative result: "refuse
any column the archive marks `Target`" catches 2 of 8 and misses every record
where the leak is a genuine feature.

## Coding rules that decide edge cases

- **Legitimate by default.** A column with no admissible record is coded
  legitimate. Precision is therefore a **lower bound** — a model flagging
  something real but undocumented is scored as a false positive.
- **A record must quote a source *about the column*.** This is the rule the §4.4
  audit applied retroactively, withdrawing 15 SUPPORT2 labels that rested on one
  third-party sentence naming no column.
- **Coded derivations implying a testable pattern are checked against the
  values.** One source statement was refuted by its own data and withdrawn.
- **A rule that does not hold on 100% of rows is refused, not rounded.**

## The scarcity result

Sweeping 689 UCI records and 6,420 active OpenML descriptions (7,109 total) with
a lexical sieve **frozen before the sweep**:

- **6 in 7,109** — frozen sieve as it ran
- **7 in 7,109** — once a defect in the OpenML gate is repaired
- **8 in 7,109** — once one further construction is admitted post hoc

The three stack in **one direction only**: every step is a *miss* being
recovered, never a hit withdrawn. All three are lower bounds. AI4I 601 — a
dataset *inside this benchmark* — states its derivation as a conditional
(*"the 'machine failure' label is set to 1"*) and all three sieve families miss
it. The sieve is left frozen; editing it to catch its own miss and reporting
that as a find would be fitting the instrument to its answer.

Replicated across four documentation cultures: 8,693 Kaggle datasets, 605
competitions, 14,420 Hugging Face cards, 6,418 OpenML records. The Kaggle arm
yields **zero** admissible records.
