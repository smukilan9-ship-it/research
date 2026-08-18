# Draft revision — §7.3, the brittleness of the derivation criterion

> **NOT APPLIED, and not applicable yet.** Every figure below is computed from
> the response cache but **is not yet in `NUMBERS.txt`**, and this project's
> rule is that a number not in `NUMBERS.txt` is unverified and does not belong
> in the paper. Two things must happen first:
>
> 1. `verify_paper.py` must emit a **matched C6-vs-C9 comparison on Stratum B**.
>    It currently emits matched C6/C9 for Stratum A only (§6); §7 lists Stratum
>    B per condition without matching, which is how the unmatched version of
>    this table misled me for one round.
> 2. The six Vertex models must be in `MODELS`, and `NUMBERS.txt` regenerated.
>
> Then `verify_tables.py` and `prose_pins.py` can hold this section, and the
> numbers below can be checked rather than trusted.

## What changes, and what does not

**The claim survives and is better evidenced.** §7.3 currently ends: *"No
wording of the derivation criterion is uniformly better, and we can name the
failure mode of each."* That is now supported by eight models on the held-out
set rather than by two, and the split is **five improve, three degrade**.

**The characterisation does not survive.** The section currently reads as
though C9's held-out behaviour is a degradation, because it is written from
`claude-opus-5` (precision 0.706 → 0.587, false positives 35 → 59) and
`gpt-5.6-sol`. Those two are now the minority case — and both are the hand-run
models §6.1 already flags as the paper's least reproducible cells.

On the six API-served models, C9 **roughly halves false positives on the
held-out set**, and does it without paying recall:

| model | precision C6 → C9 | false positives | recall C6 → C9 |
|---|---|---|---|
| `gemini-3.7-flash` | 0.903 → **0.966** | 9 → 3 | 1.000 → 1.000 |
| `gemini-3.1-pro-preview` | 0.755 → **0.913** | 27 → 8 | 0.988 → 1.000 |
| `grok-4.20-non-reasoning` | 0.535 → **0.684** | 46 → 25 | 0.631 → 0.643 |
| `grok-4.20-reasoning` | 0.457 → **0.603** | 63 → 29 | 0.791 → 0.657 |
| `gemini-2.5-pro` | 0.352 → **0.467** | 136 → 73 | 0.881 → 0.762 |
| `gemini-3.5-flash` | 0.508 → 0.405 | 64 → **94** | 0.985 → 0.955 |

Two models hold recall at 1.000 while cutting false positives by two thirds.
That is precision bought for nothing, and it is the opposite of the mechanism
the section currently describes.

**Stratum A shows none of this.** Matched, the six are a wash — three up, three
down, every delta inside ±0.05. The effect is specific to the held-out set,
which is where these models flag most freely and therefore where a brake has
something to do.

## The replacement for "C9 has no brake"

Keep the AI4I example: `gpt-5.6-sol` flagging all ten columns because each is
*"an input to the synthetic rules that determine Machine failure"* is true,
useless, and exactly on-criterion — a synthetic table whose target IS a
threshold rule over its sensors will answer yes to a reconstruction test for
every column.

Add the sharper case, which is a **failure at the clause's most explicit
instruction**. C9 says:

> *Criterion (b) is about INFORMATION, not about time. Do not test (b) by
> asking when the value was measured.*

On MI, `gemini-3.5-flash` flags twelve treatment columns at C9 that it passed
at C6, and the reason it gives for every one of them is **temporal**:

| condition | verdict | the model's stated reason |
|---|---|---|
| C6 | AVAILABLE | *"Fibrinolytic therapy on admission is available at prediction time."* |
| C9 | UNAVAILABLE | *"Hospital treatment administered after admission."* |

The clause instructs the model not to reason about timing; the model reasons
about timing and reverses itself. This is the **mirror image of the STEEL
case** that motivated C9 in the first place — there a model excused six columns
under C6 with *"measured concurrently"* and recovered them under C9; here a
model flags twelve columns under C9 with *"administered after admission"* that
it had excused under C6. Same axis, opposite direction, same clause.

## And the part that cannot be scored

Whether those twelve are errors is **not decidable from the score**, and saying
so is more honest than picking a side.

MI's prediction point is *"at admission to intensive care, before any
in-hospital complication is observed."* A treatment **administered after
admission** is, by §2.1's own definition, recorded after the prediction point.
The corpus codes those columns legitimate not because a source clears them but
because **no source names them** — §4.6's legitimate-by-default rule, which the
paper already states makes precision a lower bound and which §9 already says
means *"the apparent false positives include probable undocumented true
positives."*

So the same twelve columns are either C9's failure mode or C9's most useful
behaviour, and this benchmark cannot tell which. That is a property of the
ground truth, not of the model, and it is worth stating here because a reader
who has absorbed §4.6 will arrive at §7.3 with exactly this objection.

## Suggested closing

> Across eight models the direction is model-dependent, and on the held-out set
> C9 more often **raises** precision than lowers it — for two models to 0.913
> and 0.966 at recall 1.000. Where it fails it fails as described: on tables
> whose columns carry no lexical cue, a reconstruction test licenses flagging
> most of the frame. No wording of the derivation criterion is uniformly
> better, and prompt-level interventions for this task therefore require
> per-deployment validation, which no current practice provides.

## Numbers this draft needs `verify_paper.py` to emit

- matched C6-vs-C9 on **Stratum B**: P, R, F1, tp, fp per model
- the same on Stratum A, for the "wash" claim
- per-dataset breakdown for `gemini-3.5-flash` (the regression is **MI**, not
  CRIME: F1 0.542 → 0.420 with false positives 53 → 80, against CRIME's
  0.944 → 0.919)

Until those are emitted, this file is a draft and nothing in it may be quoted.
