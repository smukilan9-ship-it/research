# The opaque-name control

**Post hoc.** Run 2026-08-19, after the Stratum E results were known, in
response to the sharpest available referee attack on the paper's premise. It
is a control on the REAL corpus (Stratum A) and touches nothing PREREG covers.

## The attack it answers

The paper's premise (§1) is that feature-level leakage detection *"requires
knowing what a column means — which is why statistical methods struggle with
it, and why a language model is a plausible instrument."*

The obvious inversion: **then this is column-name classification, not leakage
detection.** A referee raises it in one sentence, and until now the paper had
only a partial answer — B1-tuned, a name-keyword rule with a fitted vocabulary,
reaches 0.394 against the models' 0.929, so names alone are not sufficient for
a keyword rule. That does not show what the models are using.

The paraphrase arm does not answer it either, and was never meant to. Its
authoring rule is to PRESERVE transparency level: `koi_period` → `tc_orbper`
still means orbital period. It rules out string-keyed recall, not semantics.

## The design

`opaque.py`, applied through `runner.py --opaque`.

    masked      every feature column name -> col_1..col_n, and the sample-row
                keys with them (a partial rename leaves the originals
                recoverable from the sample)
    unmasked    dataset name, target, prediction point, description, and every
                VALUE

One variable moves. The target is deliberately kept: with no target there is
nothing for a column to leak *about*, and masking it would make the task
near-impossible and the result uninterpretable.

The `col_N` assignment is a **fixed-seed shuffle**, not source order —
outcome-adjacent columns tend to sit at the end of a table, so numbering in
column order would leak position.

Cells record `dataset = "<NAME>__OPAQUE"`, a key no bundle set contains, so
every existing scorer skips them without a line changing. Verified by running
the checker suite before and after, not assumed.

B1 goes to zero here by construction — no names to match. The comparison this
arm supports is **model-with-names against model-without-names**, not model
against baseline.

## The result

| arm | column-judgments | verdicts |
|---|---|---|
| gemini-3.1-pro-preview::vertex-think16000-t0.0 | 612 | **ABSTAIN 612 (100%)** |
| grok-4.20-reasoning::vertex-t0.0 | 612 | **ABSTAIN 612 (100%)** |
| gemini-2.5-pro::vertex-think16000-t0.0 | 612 | ABSTAIN 592 (97%), AVAILABLE 14, UNAVAILABLE 6 |

Stated reasons, unprompted:

> *"The column name is anonymized, so its meaning and time of measurement are
> unknown."*
> *"Column name is anonymized, providing no context."*

## DO NOT LEAD WITH F1

F1 goes 0.929 → 0.000, and **that number is a scoring artefact.** The scorer
counts ABSTAIN as not-flagged, so a model that correctly declines scores
identically to one that misses everything. The models did not fail; they
declined, near-unanimously, with the right reason and at confidence 1.0.

Report the **abstention rate**. `prf()` already counts ABSTAIN separately in
its `ab` field, so the machinery exists.

## What it establishes

1. **The premise becomes a result.** "Detection requires knowing what a column
   means" was a motivating claim in §1; it is now measured. Remove the meaning,
   detection goes to zero. The attack converts into evidence.
2. **The models are calibrated.** They do not hallucinate leakage from values
   alone. A referee worried about false positives on unfamiliar schemas has a
   direct answer.
3. **It bounds the method honestly.** The instrument is only as good as the
   column naming. Stating that ourselves is stronger than having it extracted.

## A regime error, made and corrected

The first run passed `--think-budget 16000` to all three models. grok's
real-corpus cells were run with NO think budget, so its two arms were different
decoding regimes — the cross-regime comparison this project forbids everywhere
else. Both grok arms are cached and both abstain 100%, but only
`grok-4.20-reasoning::vertex-t0.0` is matched to the real corpus and only that
one may be reported. The two Gemini arms were correctly matched throughout.

## Limits

Three models, Stratum A, one seed. The abstention is so uniform that more
models are unlikely to change the picture, but the claim should be scoped to
what was run. Whether abstention is equally clean on Stratum E's unseen tables
is untested and would be the natural extension.
