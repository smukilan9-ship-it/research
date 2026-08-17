# Registered prediction — C9, the retimed derivation clause

**Written before any C9 cell was run.** Timestamped by the git-less but
append-only convention used for C7: this file exists in full before the runner
is launched, and the launch command follows it in the transcript.

## What C9 changes

C6 and C9 are byte-identical apart from clause (b). C6 says:

> (b) DERIVATION — the value records WHY the target's outcome was assigned, or
> was itself an input used to determine the target. **This holds EVEN IF the
> value was recorded BEFORE the prediction point.**
> A column can satisfy (b) while being **chronologically earlier** than the target.

C9 says:

> (b) DERIVATION — the target's value is a function of this column's value…
> Criterion (b) is about INFORMATION, not about time. Do not test (b) by asking
> when the value was measured. Test it by asking: could the target be
> reconstructed, wholly or in part, from this column?

Temporal references inside clause (b): **3 → 1**, and the remaining one
explicitly discharges timing rather than invoking it.

## Why

`deepseek-ai/DeepSeek-V4-Pro` flags all six of STEEL's sibling fault columns at
C1 and un-flags all six at C6, with the identical stated reason each time:
**"measured concurrently."** Those six define the target (`Other_Faults` is 1
exactly when all six are 0), so they are the clearest REASON case in the corpus
and exactly what C6 exists to catch. Like-for-like over the 10 datasets that
model answered under both conditions, REASON recall goes **91% → 36%** while
precision *rises* 0.720 → 0.806 — it did not get sloppier, it applied a
narrower rule confidently.

The hypothesis: C6's most emphatic sentence argues that timing is irrelevant to
(b), but argues it *in the vocabulary of timing*. A model following it closely
can conclude (b) is a before/after rule, and that "simultaneous" sits outside
it.

## Predictions

**P1 — the diagnosis is right.** DeepSeek-V4-Pro recovers STEEL's six sibling
columns at C9. REASON recall returns to ≥ 80% on the common-dataset set (from
36% at C6, against 91% at C1).

**P2 — no collateral damage.** For the other models, REASON recall at C9 is
within 7pp of C6 and does not fall below C1. Specifically: Kimi-K3 ≈ 93%,
GLM-5.2 ≈ 93%, nemotron-3-super ≈ 80%, deepseek-v4-flash ≈ 42%.

**P3 — precision holds.** Pooled precision at C9 within 0.05 of C6 for every
model. If C9 buys REASON by flagging more of everything, it is not a fix.

## What each outcome means

| result | reading |
|---|---|
| P1 ✓ and P2 ✓ | the mechanism is confirmed and C9 replaces C6 as the paper's intervention |
| P1 ✓, P2 ✗ | the temporal framing helps some models and hurts others — report both clauses, claim neither is universal |
| P1 ✗ | the "concurrent" diagnosis is wrong; DeepSeek's C6 collapse needs another explanation and the §13d story stands unchanged |
| P3 ✗ | any REASON gain is bought with false positives and is not a fix |

**P1 failing is the most informative outcome and will be reported as
prominently as P1 succeeding.**

## Scope

5 models runnable now: Kimi-K3, GLM-5.2, DeepSeek-V4-Pro (Featherless);
nemotron-3-super-120b, deepseek-v4-flash (NVIDIA). 12 datasets, one shuffle,
C9 only — C1 and C6 are already cached. Gemini is quota-limited; Opus and
gpt-5.6-sol are run separately through the chat UI.
