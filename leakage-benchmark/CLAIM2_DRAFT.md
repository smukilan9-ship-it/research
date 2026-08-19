# Rewriting contribution (2)

**Not applied to `PAPER.md`.** Two gates first, both of which the project
already enforces elsewhere and neither of which is satisfied yet:

1. **The roster is incomplete** — 10 of 16 at the time of writing. Every
   Stratum E figure below is a maximum over completed models, and PREREG §3
   fixes the roster precisely so that a number announced on part of it is not
   treated as the number. If any remaining model exceeds 0.852 at C6 or 0.754
   at C1, these change.
2. **None of these figures is in `NUMBERS.txt`.** The project's rule is that a
   number not in `NUMBERS.txt` is unverified and does not belong in the paper.
   `synth/score.py` runs deliberately *beside* the frozen result rather than
   inside it, so applying this text requires a verifier that emits the Stratum
   E figures into a checkable artefact first.

## CORRECTED — the first draft of this file overstated the problem

It compared the models' synthetic F1 against **0.717**, the mean of PREREG
section 6's *per-table oracle* baseline, and concluded the margin over
correlation had nearly closed. The paper's B3 is a **single global threshold
over all columns pooled**, and computed that way on the synthetic tables it is
**0.665**. Every "margin" figure below is against 0.665. `verify_synth.py`
now prints both baselines with a note saying which is comparable.

## What is actually wrong with the current text

> **(2) Evidence that models detect what correlation cannot.** Best F1 0.929
> against a tuned upper-bound baseline at 0.630, and exact performance at the
> primary condition on the held-out set; downstream, model-based cleaning
> recovers the honest ceiling to within 0.024 F1 while the baseline misses in
> both directions. [N §5, §6, §7, §8]

**The claim is true and survives the memorisation control.** Nine of ten
models exceed the pooled baseline on tables that have never been published, at
both conditions — proportionally more than the 12 of 16 the public corpus
manages at C1. Nothing here needs withdrawing.

What is missing is that the claim is currently *unqualified as to magnitude*,
and the magnitude does fall:

| | baseline | exceed at C1 | exceed at C6 | best margin | best F1 |
|---|---|---|---|---|---|
| public corpus | B3 0.630 | 12 of 16 | 14 of 16 | +0.288 | 0.929 |
| unseen tables | B3 0.665 | 9 of 10 | 9 of 10 | +0.187 (C6) | 0.852 |

So the edit is an **addition, not a retraction**: the control result belongs in
the contribution because it is favourable, and reporting the narrowing
alongside it is what makes the claim honest rather than merely defensible.

## Proposed replacement

> **(2) Evidence that models detect what correlation cannot, on public and on
> unseen data alike.** Best F1 0.929 against a tuned upper-bound baseline at
> 0.630, with 12 of 16 models exceeding that baseline at the primary condition
> and 14 of 16 with the derivation clause; exact performance at the primary
> condition on the held-out set; downstream, model-based cleaning recovers the
> honest ceiling to within 0.024 F1 while the baseline misses in both
> directions. The advantage is not an artefact of familiarity: on twenty tables
> generated locally and never published (§X), 9 of 10 models exceed the same
> baseline computed the same way, at both conditions. It is, however, smaller
> there — best F1 falls from 0.929 to 0.852 and the best margin from +0.288 to
> +0.187 — and §X reports what that costs the claim. [N §5, §6, §7, §8;
> NE §1, §2, §3]

## What §X must then say, since the bullet now defers to it

The absolute drop is real and has a mechanism. Three lines of evidence, none of
which involves the baseline and so none of which is touched by the correction
at the top of this file:

1. **Per-model absolute drop** at C1, −0.13 to −0.15 for the strongest models,
   while the two weakest *gain*.
2. **The nemotron scale ladder** — real minus synthetic of −0.002, −0.035,
   −0.120 across 30B / 120B / 550B of one architecture. Whatever scale buys is
   concentrated on data the model has seen.
3. **The clause diagnostic** — `deepseek-v4-flash` and `grok-4.20-non-reasoning`
   respond to the C6 clause enormously on the real corpus (+45.2, +28.6) and
   almost not at all on unseen tables (+2.5 each). Not a capability limit; a
   limit on where the capability applies.

The honest summary for §X: **detection above correlation is not memorisation,
but the size of the advantage partly is.**

## Gates before this can be applied

1. **Roster completeness.** `verify_synth.py` exits non-zero and stamps
   NUMBERS_E.txt PRELIMINARY until 16 of 16. At 10 of 16 the counts read 9 of
   10; they will change.
2. **`prose_pins.py`.** The pin on §5/§6's exceedance sentence sources from
   `src_exceed()` → `{b3: 0.63, n: 16, c1: 12, c6: 14}` and the rewrite reuses
   those counts unchanged, so it keeps passing. What is owed is a second source
   reading NUMBERS_E.txt section 3 and a pin for the Stratum E counts — a
   hardcoded count that stops matching is the exact failure `src_exceed()` was
   written to avoid.

## Consequential edits owed

- **Abstract.** Scope any unqualified detection claim the same way.
- **Contribution (3).** The derivation clause carries a materially larger share
  of the margin on unseen tables (+0.089 → +0.187) than on public data
  (12 of 16 → 14 of 16). It is part of (2)'s evidence, not only a
  characterisation of failure. Cross-reference it.
- **§8.** The three mechanistic lines above are new and belong in the
  discussion.
