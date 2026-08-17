# LeakLadder — the sentence that finds leaks

**Reverie Hacks 2026 · ML Prompt Engineering**

**[▶ Open the interactive demo](https://claude.ai/code/artifact/ebfd7afc-cb9d-48df-a2b6-4fc75bacbc94)**

A language model reading nothing but column names and a target catches **96%** of
data leaks that arrive too late, and only **62%** of the ones the label was
*computed from*. One added sentence takes that second number to **88%**.

You can click through the evidence: pick a dataset, pick a model, toggle the
prompt, and watch the model change its mind — in its own words.

---

## The problem

A column **leaks** when it could not honestly have been known at the moment the
model is asked to predict. Train on it and your metrics look great right up
until deployment, where the column does not exist yet. No splitting scheme
repairs it, because the column is wrong in every split.

Most leakage tooling looks at *values* — correlations, train/test overlap. That
cannot work here, because whether a column is legitimate is not a property of
its numbers. `body` in the Titanic table is a body-recovery number: it exists
only for passengers who did not survive. The integers look ordinary. The
**meaning** is the leak, and meaning lives in documentation and naming.

That makes it a language problem, which makes it a prompt-engineering problem.

## What we found

We asked ten models, across nine prompt variants, to audit 604 columns in 15
public datasets against 68 documented leaks. The failure is not noise — it is
**definitional**, and it splits cleanly by mechanism:

| the column… | mean recall at C1 | after the sentence |
|---|---|---|
| is recorded **after** the prediction point | 96% | 98% |
| exists **because** the outcome happened | 85% | 88% |
| the label was **computed from** it | **62%** | **88%** |

Models arrive already believing leakage means *timing*. They have almost no
concept of a column that is perfectly timely and still inadmissible because the
answer was derived from it. So we said so, in one clause:

> *"A column is also inadmissible if the target was **computed from it** —
> regardless of when it was recorded."*

That single sentence is the entire intervention. It closes the 23-point gap
between derived columns and the next-worst mechanism to under one point, and moves the other two mechanisms by less than 4.

## Why this is a prompt result and not a model result

The model, the schema, the scoring and the output format are all held fixed.
The **only** difference between C1 and C6 is that sentence. Comparisons are made
on the exact cells answered under both variants — matched on dataset *and*
column-shuffle, never pooled across.

## The part most demos leave out

**The gain is not free, and it is not uniform.**

- Measured in F1, the lift **concentrates in the weaker models**. For the three
  strongest, a cluster bootstrap resampling *datasets* is consistent with **no
  effect at all**.
- We wrote a second version of the same criterion (**C9**) that omits any
  mention of time. It rescues one model by **+0.190 F1** and costs another
  **0.061**. No wording is uniformly better.
- On one dataset the sentence rescues 1 real leak and creates **9 false alarms**.

The demo surfaces the costly cases in the same strip as the flattering ones, and
picks them from the data rather than from a hand-written list — so the shortlist
cannot quietly become only the good news.

**Conclusion we actually support:** prompt interventions for this task need
per-deployment validation, and no current practice provides it.

## Is it just pattern-matching leaky-looking names?

No, and we tested it three ways.

- **Renaming.** Replace every column, target and dataset name with a
  meaning-preserving alias. Both frontier models score *marginally better*
  (−0.019, −0.022 F1 — i.e. essentially unchanged).
- **A keyword rule.** We built the pattern-matcher the objection implies — 34
  name patterns (`days_to_*`, `*_outcome`, `body`, `discharge_*`…) fitted to the
  leaks in our main set. It reaches F1 **0.394** there and **0.000** on the
  held-out set, where a frontier model at the same condition is exact. Leaking
  column names share no vocabulary that transfers between datasets.
- **Verbatim memorisation.** No model reproduced any of 675 data rows or any of
  30 headers.

## Baselines

| approach | F1 |
|---|---|
| always say "safe" | 0.000 |
| keyword rule over column names, vocabulary fitted to the answers | 0.394 |
| correlation screen, threshold swept **on the answers** | 0.630 |
| **model, names + target only (C1)** | **0.905** |
| **model, + the sentence (C6)** | **0.918** |

Every baseline threshold is tuned on the test answers, making each an upper
bound no real deployment could reach. An untuned baseline would be a strawman.

## What it's worth downstream

Train a random forest three ways on each dataset: keep everything, drop the
documented leaks (the honest ceiling), drop what the model flagged.

- Leaving the leaks in inflates F1 by **0.147** on average, 0.306 at worst.
- Cleaning with the model's flags lands **0.024** from the honest ceiling.
- The correlation baseline lands 0.048 away and errs in *both* directions — on
  Titanic it drops `sex` (entirely legitimate, the most useful feature on the
  table) and keeps `body`.

As triage: the model's flags put **48 of 306 columns — 16% — in front of a human
reviewer, and that 16% contains all 40 documented leaks.**

## How the demo works

Nothing is generated at page load and there are no live API calls. Every verdict
and every sentence of reasoning shown is a **real cached completion**, the same
cells the numbers above are computed from.

```
build_demo_data.py   pulls 258 cells (8 models × 15 datasets × C1/C6/C9)
                     out of the response cache into demo_data.json
index.html           the page, with __DATA__ as a placeholder
demo.html            built artifact — index.html with the JSON inlined
```

Rebuild:

```bash
python3 build_demo_data.py
python3 -c "
tpl=open('index.html').read()
d=open('demo_data.json').read().replace('</','<\\\\/')
open('demo.html','w').write(tpl.replace('__DATA__',d))"
```

## The benchmark underneath

604 columns, 15 public datasets, 68 documented leaks — each licensed by a
**written record**, most by a verbatim quotation from the dataset's own
documentation. Coded derivations that imply a testable pattern are checked
against the values, and one source statement was refuted by its own data and
withdrawn.

Full corpus, protocol, all 1,812 model cells and the verification stack:
[`../leakage-benchmark/`](../leakage-benchmark/) — including
`handoff/` if you want the whole story.

## Honest limitations

- Two of the ten models were run by hand through a chat interface rather than an
  API; their cells are reproducible only in the sense that the transcripts are
  published.
- One model (`gemini-3.5-flash`) has seven cells missing, non-randomly. Its rows
  are excluded from every mean-over-models figure and marked wherever they
  appear.
- The mechanism labels are one coder's partition. We tested how much that
  matters by adversarially relabelling them; the direction of the finding
  survives, the exact magnitude should not be read to a decimal.
