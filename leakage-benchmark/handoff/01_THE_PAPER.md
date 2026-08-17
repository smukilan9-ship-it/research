# The paper — what it claims and what each claim rests on

**Title.** Detecting Feature-Level Target Leakage with Language Models: A
Source-Grounded Benchmark

**Venue.** TMLR. Chosen because TMLR's bar is *claims supported by evidence* and
*of interest to some audience* — not novelty or significance — which suits a
paper whose contribution is an evaluand plus a careful negative result.

**Calibrated acceptance estimate: 84%.** The residual risk is concentrated in
three places, none fixable by editing: the hand-run frontier cells (§05), the
single-coder subtype partition, and seven missing `gemini-3.5-flash` cells. The
realistic bad outcome is not rejection but a revise-and-resubmit asking for a
second coder or an API-reproducible frontier run; roughly 1 in 4, most of which
convert.

## The object

A column **leaks** when it could not honestly have been known at the moment the
model is asked to predict. Leakage is a property of the **triple (column,
target, prediction point)**, never of a column alone — the paper demonstrates
the same column being admissible under one prediction point and not another,
twice.

This is *not* the leakage most tooling targets. Train/test overlap is
procedural: the code is wrong and reading the code finds it. Here the pipeline
is correct — split cleanly, scaled after the split, used once — and what is
wrong is what the column *means*, which lives in documentation rather than in
the program.

## The three contributions, and their load-bearing evidence

**1. A benchmark.** 604 columns, 15 datasets, 68 documented positives. Each
positive is licensed by a written record, most by a verbatim quotation from the
dataset's own documentation. Four strata admitted under different rules and
never pooled. Details in `03_CORPUS.md`.

**2. Models detect what correlation cannot.** Best F1 **0.918** at C6, **0.905**
at C1, against **0.630** for a correlation baseline whose threshold was swept on
the answers and **0.394** for a keyword rule over column names whose vocabulary
was fitted the same way. Downstream, model-based cleaning lands **0.024 F1**
from the ceiling a documented cleaning achieves; the correlation baseline lands
0.048 away and errs in *both* directions.

**3. Why they fail, and how little it takes to fix.** Mean recall at C1 is
**96% TIMING, 85% CONSEQUENCE, 62% REASON**. One sentence naming the derivation
criterion lifts REASON to **88%**. Models operationalise leakage as *timing*;
what they lack is that a column can be inadmissible because the label was
*derived from it*, whenever it was recorded.

## Claims that carry real weight, and their weak points

| claim | rests on | the honest weakness |
|---|---|---|
| best F1 0.918 / 0.905 | `gpt-5.6-sol`, `claude-opus-5` | **both hand-run through a chat interface.** No reader can re-run them. This is the paper's largest hole — see `05_OPEN_WORK.md` |
| Stratum B exactness (84 tp, 0 fp, 0 fn) | `gpt-5.6-sol` at C1 | same, plus: it is 298 columns judged three times with an identical answer, not 894 independent judgments. Stated in §8 |
| the definitional finding | subtype partition | **one coder.** Answered by perturbation analysis (§21) and Stratum D's agreement-1.000 records, not by a κ |
| scarcity (8 in 7,109) | frozen lexical sieve | a sieve is a lexical instrument; all three figures are **lower bounds**, and AI4I 601 is a documented miss inside our own benchmark |
| the C6 lift | matched C1/C6 cells | measured in F1 it **concentrates in weak detectors**; for the three strongest models a cluster bootstrap is consistent with no effect. Now stated in both abstracts |

## Results that are negative and kept

The paper is stronger for these; do not quietly drop them.

- **§4.4, the closed-world dictionary rule.** If a dataset documents every
  column, silence should be informative. 406 of 689 datasets qualify; the rule
  flags 23 columns (0.090%) against an 11.3% base rate and recovers 8 of 56
  positives. *A complete data dictionary is not documented provenance.*
- **Klaverjas2018.** Documented as leakage by its own authors, missed by 3 of 4
  models, and removing the columns *improves* F1 by 0.003. Documented,
  undetected, and inert — three properties a single quality score would collapse.
  It is why detection and downstream cost are reported on separate axes.
- **Cirrhosis.** The sieve returns zero sentences on the whole record. Four of
  ten models flag `N_Days` at C1; no model is reliable across conditions.
- **B1-tuned scores 0.000 on Stratum B.** A keyword rule fitted on Stratum A
  transfers to nothing. Leaking column names share no vocabulary across datasets.
- **The self-audit.** Eight of the original 76 labels withdrawn, and an entire
  proposed mechanism (SURROGATE) withdrawn with them, because the sources did
  not say what we had them saying.

## Where the manuscript's structure lives

`PAPER_SHORT.md` sections 1–10 match `PAPER.md`'s numbering so cross-references
survive the cut. §4.3 scarcity, §4.4 the negative result and audit, §6.1
detection, §6.2 the definitional finding, §6.3 memorisation, §6.4 Stratum C/D,
§6.5 uncertainty, §7 downstream and interventions, §8 limitations, §9 discussion.
