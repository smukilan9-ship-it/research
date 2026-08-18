# Analysis plan — the unseen-tables experiment

**Status: DRAFT. Not committed. RUNS IN PROGRESS — 6 of 16 roster models
complete.** The plan below was fixed before any table existed and has not been
edited since the first model saw one; the only changes after that point are this
status line and the record of run outcomes. No threshold, dependent variable or
decision rule has moved.

The corpus this plan is fixed against: **20 tables, 840 columns,
120 injected positives — 40 REASON, 40 CONSEQUENCE, 40 TIMING.**
Every table independently passes the section 6 band, every injected rule
re-derives from the frame, and all twenty are frozen with a SHA256 in
`synth/tables/MANIFEST.json`. They are `.gitignore`d until the runs finish.

## What this document is, and what it is not

It fixes the question, the measurement, the decision rule and the meaning of
each outcome **before any synthetic table exists**, so that the framing of the
resulting paper is chosen by the data rather than fitted to it.

It is **not** a registration. There is no public registry entry, no third-party
timestamp, and git history is rewritable by whoever owns the repository. Anyone
who does not already extend the authors ordinary methodological good faith
should treat this as a stated commitment of the same kind as "seeds were fixed
in advance" — a claim in a methods section, not a proof. Any text derived from
this file must say so in those words and must not use "pre-registered".

Its real function is the one that does not depend on being believed: it stops
the authors moving a threshold after seeing where the numbers landed.

## 1. The question

Does the paper's central finding survive on tables the models have provably
never seen?

The finding is a **definitional** one. Across sixteen models from nine
laboratories, recall at C1 is 61.1% on REASON, 84.3% on CONSEQUENCE and 97.7%
on TIMING; one sentence naming the derivation criterion (C6) lifts REASON to
85.9% and moves the other two by under five points. The paper reads this as
models operationalising leakage as *timing* and under-applying *derivation*.

## 2. Why the current design cannot answer it

Every dataset in the benchmark is public and almost certainly in pretraining.
Stratum B is held out from **prompt development**, not from training data;
Strata C and D are external to the authors, not to the models. So no existing
stratum separates *the model reasoned about this table* from *the model recalls
this table*.

The paraphrase control (§6.3) rules out **string-keyed** recall: dataset name,
target, every column and the sample-row keys are renamed together, and
`claude-opus-5` goes 0.905 → 0.916 under it. It does not rule out **semantic**
recall, because the aliases are faithful — `koi_period` → `tc_orbper` — so a
model can still infer which study the table came from and retrieve what it
knows.

A surviving account of the whole result is therefore: the model has memorised
facts about these tables, C1 fails to cue the right retrieval, and the C6 clause
cues it. That account fits every number in the paper. This experiment exists to
break the tie.

## 3. Design

Tables are **generated locally by a committed generator with a fixed seed, and
are not published anywhere until after all model runs are complete.** This is
the only novelty guarantee available that does not depend on a vendor's
disclosure: a table that has never left this machine cannot be in a training
corpus.

Leaks are injected by rule and verified row by row, the Stratum D standard the
paper already uses — *a record is admitted only if its rule holds on 100% of
rows*. Injected columns carry plausible domain names. A column named
`leaky_col_1` tests nothing and none will exist.

All three measured mechanisms are injected, using §2.2's definitions:

| mechanism | injected as |
|---|---|
| REASON | a column that was an **input to the rule** that assigned the label |
| CONSEQUENCE | a column that **exists because** the outcome occurred |
| TIMING | a column **recorded after** the stated prediction point |

UPSTREAM is declared-not-measured in the paper and is not injected here.

**Fixed in advance, and not adjustable after seeing results:**

- at least **12 tables** — matching the real corpus's cluster count, so the
  cluster bootstrap has the same number of clusters and no more power than the
  result it is being compared against;
- at least **40 positives per mechanism**, against the real corpus's 22 / 30 /
  14, so a null cannot be blamed on thinner subtype counts;
- every table carries legitimate columns that are genuinely predictive, so that
  precision is a real test and not a formality;
- the roster is the sixteen models already in `MODELS`, at C1 and C6, on the
  same conditions and the same scoring code, in **three run modes** which are
  declared here because they are not equivalent:

  - **14 models via API.** Vertex, featherless and nvidia, through `runner.py`,
    identical code path to the rest of the corpus.
  - **`claude-opus-5-max` by one sub-agent per cell**, the method section 5.3
    already uses for it. The user prompt is byte-identical to what `runner.py`
    would send and is hash-matched to prove it; the *system* prompt is the
    harness's, not `prompts.SYSTEM`. That difference exists in the published
    corpus too and is not introduced here, but it is a difference and this
    experiment does not get to pretend otherwise.
  - **A sub-agent has a risk the API models do not: it can read the answer.**
    It runs inside this repository with filesystem access, and the ground truth
    sits in `synth/tables.py`, `synth/specs.py` and each table's `meta.json`.
    An API model is handed a prompt and can do nothing else; a sub-agent could
    simply look. Three mitigations, in increasing order of what they are worth:
    the prompt instructs it to judge from column semantics alone; several
    agents volunteered that they had deliberately not opened those files; and
    -- the only one that is evidence rather than assurance -- the last ACCESS
    time on every ground-truth file predates the first sub-agent dispatch
    (16:18-17:01 against a first dispatch at ~17:50). Nothing read them.

    A zero-error cell is NOT evidence of contamination and was briefly
    mistaken for it here. Six cells scored perfectly, all on tables whose
    leaks are transparently post-outcome -- TOWER_OUTAGE's four are
    `sla_credit_usd`, `truck_rolls_dispatched`, `restoration_minutes`,
    `postevent_alarm_count`. Easy tables produce perfect scores honestly.

  - **`gpt-5.6-sol-xhigh` cannot be run by a sub-agent.** A sub-agent in this
    harness is Claude. Producing its 40 cells requires that model's own chat
    interface, run by hand. If those cells are not obtained, the model is
    reported as absent from this experiment -- **not** substituted, and not
    filled by any other model wearing its label.

## 4. The dependent variable

**Not overall F1.** A drop in F1 on synthetic tables is uninterpretable: it is
equally well explained by the generator producing out-of-distribution tables.

The primary measure is the **within-table, within-model subtype asymmetry**,
which is insensitive to how hard the tables are overall:

- **D1, the C1 deficit** = CONSEQUENCE recall − REASON recall, at C1, mean over
  models on complete rosters. Real corpus: **+23.2 points**.
- **D2, the clause repair** = REASON recall at C6 − REASON recall at C1. Real
  corpus: **+24.8 points**.

Both pooled the way §24 pools them, with the 95% interval from the same cluster
bootstrap over tables, 2,000 draws.

## 5. Decision rule, fixed now

**REPLICATES** — D1 ≥ 10 points **and** D2 ≥ 10 points **and** D1's 95% CI
excludes zero.

**FAILS TO REPLICATE** — D1 < 10 points **or** D1's 95% CI includes zero.

**INDETERMINATE** — anything else, including D1 replicating while D2 does not.

The bar is 10 rather than 23 deliberately: the test is whether the *phenomenon*
appears on unseen tables, not whether its magnitude reproduces. A generator we
wrote has no reason to reproduce the effect size of a natural corpus, and
demanding that it does would manufacture a null.

## 6. Positive control — without this the null branch is unpublishable

If the models do badly and nothing else is measured, a referee correctly
answers "your tables are out of distribution" and the result dies.

So the **B3 correlation baseline runs on the synthetic tables too**. On Stratum
A it scores F1 0.630 (P 0.697, R 0.575).

- **Judged per table, not on the mean.** The first generator produced B3 =
  0.667 on all three tables because it was one template three times; a mean
  would have hidden that they were clones. Every table must independently land
  in **[0.45, 0.80]**.
- All tables in band → the tables have statistical structure comparable to the
  real corpus. A model collapse is then about the models.
- Any table outside the band → that table is regenerated or dropped **before
  any model sees it**, and the change is recorded here. If more than a quarter
  of tables need this, the generator is unfit and the run is void.

## 7. What each outcome means for the paper

| outcome | reading | what the paper becomes |
|---|---|---|
| **REPLICATES** | the definitional deficit is not an artefact of familiar tables; retrieval-cueing is ruled out | current framing, materially strengthened; this becomes the memorisation control the design currently lacks |
| **FAILS, F1 near B3** | detection on the real corpus was substantially recall of public tables | the paper is *"do LLMs detect leakage, or recall it?"* — a negative result about a method the field is already adopting |
| **FAILS, F1 stays high** | models detect leakage on unseen tables but the subtype structure was a property of familiar ones | detection claim survives, the definitional claim is scoped to seen data and the mechanism is reopened |
| **INDETERMINATE** | reported as indeterminate | no reframing; the experiment is reported and the question stays open |

All four are written up. None is a failed experiment.

## 8. Conditions that void the run

- B3 outside the band in §6.
- `tabmemcheck` indicates recall of any generated table.
- Any injected rule that does not hold on 100% of rows.
- Fewer than 12 models completing the full roster.

## 9. Flexibility we are giving up

We will not, after seeing results: change the mechanism definitions; drop tables
or models; add models; change the primary dependent variable; move the 10-point
bar; or reanalyse at a condition other than C1 and C6. Anything discovered that
merits a different analysis is reported explicitly as **post hoc**.
