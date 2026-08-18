# Analysis plan — the unseen-tables experiment

**Status: committed to git 2026-08-19 as part of `30792c8`. RUNS IN PROGRESS
— 7 of 16 roster models complete.** The plan below was fixed before any table
existed and has not been edited since the first model saw one; the only changes
after that point are this status line, the record of run outcomes, and
**Amendment 1**, which is dated, marked post-hoc, and appended rather than
folded into the text it modifies. No threshold, dependent variable or decision
rule has moved.

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

---

# Amendment 1 — 2026-08-19, after partial results were seen

**This is a post-hoc change and is presented as one.** Seven of sixteen roster
models had complete cells when it was made, and their D1/D2 figures were known.
It is recorded here, and committed to git before the affected cells were
scored, so that the sequence is checkable rather than asserted.

## What changed

Section 3 declares three run modes and says of the fourth roster model:

> **`gpt-5.6-sol-xhigh` cannot be run by a sub-agent.** A sub-agent in this
> harness is Claude. Producing its 40 cells requires that model's own chat
> interface, run by hand. If those cells are not obtained, the model is
> reported as absent from this experiment — **not** substituted, and not filled
> by any other model wearing its label.

That was wrong about the facts, not about the principle. The Codex CLI ships
inside `/Applications/ChatGPT.app/Contents/Resources/codex` and is
authenticated on this machine. It **is** that model's own harness, and it runs
non-interactively. So the cells are obtainable, and a **fourth run mode** is
added to obtain them:

- **`gpt-5.6-sol-xhigh` via `codex exec`, one ephemeral session per cell.**
  Driver: `synth/codex_cell.py`.

## What did not change

No model is added and none is dropped — `gpt-5.6-sol-xhigh` was already on the
roster fixed in section 3, and this changes only how its declared cells are
obtained. The dependent variable, the 10-point bar, the conditions, the
scoring code and the decision rule in section 5 are untouched. Section 7's
table is applied to the completed roster exactly as written.

## Why this is not a loophole, and where it still costs us

The honest objection is that a run mode added after seeing results is a
researcher degree of freedom, and reporting sixteen models instead of fifteen
moves D1 and D2. Three things bound that, none of which is "trust us":

1. **The direction was not knowable in advance.** The decision was made and
   committed before any of the forty cells existed, let alone was scored.
2. **The cells cannot be cherry-picked.** Each has a deterministic id derived
   from the prompt, so a missing one is a visible gap, not a silent omission.
   All forty or none is the only reachable state that looks clean.
3. **Reporting the model is strictly more informative than reporting it
   absent**, and section 8 voids the run below twelve complete models — a rule
   that only makes sense if obtaining cells is preferred to not obtaining them.

What it costs: this amendment exists, and any write-up must carry it.

## This arm is more tightly bounded than the sub-agent arm, not less

Section 3's stated weakness in the sub-agent path is that a sub-agent *can*
read the answer key, and the only evidence it did not is file access times —
evidence about what happened, not a limit on what could. The Codex arm is
bounded structurally instead. Every cell runs with:

    --disable shell_tool --disable unified_exec    no command execution at all
    -s read-only                                   no writes if it had one
    -C <empty dir outside the repository>          nothing where it is rooted
    --ignore-user-config                           no MCP servers, no plugins

Verified rather than assumed: asked directly to `ls` the `synth/` directory,
the model replies that shell execution is not available in the session. It
cannot open `synth/tables.py` because it has no tool that opens anything.
Each cached cell additionally records `tool_items`, counted from the session's
JSONL event stream, and the driver **refuses to cache a cell whose count is not
zero**.

## The difference that remains, and is not hidden

The system prompt is Codex's harness prompt, which carries a skill listing
(~15k input tokens against the API path's ~5k). The *user* prompt is asserted
byte-identical to `subagent_cell.build()`, which is the text `runner.py` would
send. This is the same class of difference the sub-agent arm already declares,
and it is recorded in each cell's `run_mode` field rather than in a changelog.

No `--output-schema` is used, deliberately: constraining the decode would make
this arm's replies easier to parse than every other arm's, and the comparison
is between models, not between JSON validators. Replies go through
`salvage.parse` exactly like an API reply.


---

# Amendment 2 — 2026-08-19, post hoc, and NOT part of the roster

**Two new models are being run, and section 9 forbids adding models after
seeing results. They are therefore not added.** Neither may enter D1, D2, the
roster, or any mean over models. They are reported in their own paragraph,
marked post hoc, or not at all.

## What is being run

    nvidia/nemotron-3-nano-30b-a3b::high      (new, post hoc)
    nvidia/nemotron-3-super-120b-a12b::high   (already a roster model)
    nvidia/nemotron-3-ultra-550b-a55b::high   (new, post hoc)

One architecture, one training recipe, three sizes, all at `--reasoning high`
because that is what the middle rung ran at — a ladder whose rungs use
different decoding settings measures the settings, not the scale.

## Why, and what it is for

The paper's tier claim inverted under the sixteen-model roster (+0.083 frontier
against +0.063 replication), while its *explanation* held: r = −0.66 between a
model's C1 starting point and what C6 buys it. The cross-lab roster cannot
separate capability from lab, recipe and data, because every rung differs in
all four at once. A within-family ladder holds three of them fixed.

This is a question the experiment was not designed to answer, discovered after
the results were in. That is exactly what section 9 means by "reported
explicitly as post hoc", and it gets no more standing than that.

## The distinction this amendment turns on

Amendment 1 obtained a **declared roster model** by a route the plan did not
know existed. The Vertex Gemini arms and the NIM GLM-5.2 arm are the **same
models on a different host**, reported beside the roster and verified not to
substring-match a roster label. This amendment is neither: nano and ultra are
**models that were never on the roster**. Blurring those three cases would make
"the roster is fixed" mean nothing, so they are kept apart in the text and in
the labels.
