# Draft replacement — the memorisation control

*Filed as `SECTION7_DRAFT.md` because that is the name the overnight brief
reserved for it. The material it replaces is **§6.3(a)–(c)** of the current
`PAPER.md` (lines ~723–758), the "Memorisation control, three ways" block
inside "The tuning objection, measured". Two other passages move with it and
are given at the end: the abstract's memorisation sentence (~line 43) and the
§8 limitation bullet (~line 1010).*

*Regenerate every number here with `memcheck_report_all.py` (recall rates),
`memcheck_score.py` (direct tests, → `MEMCHECK_SCORED.txt`), and
`verify_paper.py` §11 (paraphrase, → `NUMBERS.withui.txt`). Working record and the
correction that prompted this rewrite: `MEMCHECK_FINDINGS.md`.*

> **Not final.** The paraphrase figures are from `NUMBERS.withui.txt`, which
> includes the hand-run Opus and GPT arms. The repair chain still has **11
> `gemini-3.5-flash` cells unrestored** (daily quota), so gemini-3.5's row may
> move slightly; no other row depends on those cells. Nothing in this draft has
> been applied to the paper.

---

## Why the existing text has to go

The current §6.3 makes three claims, and the first two do not survive being run
against more than one model.

1. It reports **19%** of leaking columns recalled. That is `gemini-3.5-flash`,
   the first model measured. At four models the range is **19% to 61%** and the
   figure the paper quotes is the bottom of it.
2. It drops the three fully-recalled datasets and reports that every frontier
   model stays above 0.855. At four models, **ten of the twelve** Stratum-A
   datasets have at least one leaking column recalled by somebody. The check
   cannot be run at four models; there is not enough corpus left.
3. It reports the paraphrase arm pooled over three models, and omits the two
   the headline rests on. Pooling hides the one model that genuinely depends on
   the strings, and omitting Opus and GPT meant the control could not speak to
   the results it was defending.

There is also a fourth claim that was never in the paper and nearly went in:
that the models reproduce headers and data rows verbatim. They do not. That is
the strongest thing in this section and it points the other way.

---

## 6.3 (replacement) Memorisation, measured four ways

Every table in Stratum A is a well-known public dataset, and Bordt et al. (2024)
show that language models have memorised many such tables verbatim, with
contamination concentrating in datasets with *meaningful column names* —
precisely this setup. We therefore ask, with their instrument and with ours, on
every API-served model we can reach: **how much of the detection result could be
recall?**

The question decomposes. A model might have memorised **the data**, **the
schema**, or **the answer** — and these are separable, measurable, and in our
results they come apart sharply.

### (a) The data: no verbatim reproduction, anywhere

`tabmemcheck`'s row-completion test shows a model twenty-five consecutive rows
of a table and asks for the next one; its header test shows the head of the file
and asks for the continuation. Both are scored against the ground truth the
checker itself returns, with every judgement call made in the model's favour:
reasoning text is mined for its last CSV-shaped line, and comparison is
truncated to the length of the truth so a model that over-runs is not penalised.

| model | header exact | rows exact | mean row similarity |
|---|---|---|---|
| `deepseek-v4-flash-0731` | 0 / 15 | **0 / 300** | 0.580 |
| `nemotron-3-super-120b` | 0 / 15 | **0 / 375** | 0.393 |

**Not one row of 675, and not one header of 30, was reproduced** — including on
AI4I, BANK and HEARTFAIL, the three datasets the schema test below scores as
*completely* recalled. No CSV-shaped line could be mined from 50 of 705
completions (7.1%); those are the only cells where the scorer rather than the
model could be responsible for a miss.

What the models return instead is a well-formed forgery. Nemotron on AI4I:

```
true    L,300.4,311.8,1433,42.2,14,0,0,0,0,0
model   M,300.3,311.8,1592,32.1,11,0,0,0,0,0
```

Correct schema, correct units, plausible value ranges, and a tool-wear counter
within three of the true one because the rows are sequential and the model is
*counting*. This is a model reconstructing a distribution, not reciting a table.

We report this because it bounds what the rest of the section can mean. Whatever
these models have, it is not the fifteen tables.

### (b) The schema: substantial recall, and it varies by a factor of three

The feature-names test asks the model to complete a table's column list from its
name alone.

| model | all columns | **leaking columns** | errored |
|---|---|---|---|
| `gemini-3.7-flash` ⚠ | 75% | 17/36 = 47% | 2 |
| `deepseek-v4-flash-0731` | 73% | **22/36 = 61%** | 2 |
| `nemotron-3-super-120b` | 62% | 15/36 = 42% | 2 |
| `gemini-3.5-flash` | 34% | 7/36 = 19% | 2 |

Column names *are* substantially recalled, and the spread across models is more
than threefold. **We report the maximum, 61%, as the bound.** An earlier version
of this work reported 19% — the first model we happened to run — and we note the
correction because a single-model memorisation bound is not a bound on a
multi-model benchmark, and the direction of the error is not random: whichever
model runs first is as likely to be the most conservative as the least.

Two datasets cannot be tested at all. **CRIME (144 columns) and MI (122)** fail
inside the checker for every model with `Could not determine delimiter` — a
parsing failure, not an API failure. Both are **Stratum B, the held-out transfer
set**, so this instrument is structurally blind to the stratum whose purpose is
to show the result generalises. The direct tests in (a) do reach all three
Stratum-B tables, and score 0/25 on each.

### (c) Why we do not report a leave-recalled-out rescoring

At one model, three datasets were fully recalled and dropping them left nine
datasets and 34 positives. At four models, **ten of twelve Stratum-A datasets**
have at least one leaking column recalled by at least one model, and the clean
set is **BONEMARROW and ECHO** — of which BONEMARROW is already excluded from the
downstream headline as degenerate (§8). SUPPORT2, which alone supplies 15 of the
46 Stratum-A positives, went from 3/6 leaking columns recalled to **6/6** on the
addition of a single model.

A leave-recalled-out check run honestly across four models therefore has one
usable dataset. We report that it cannot be computed rather than computing it on
the subset that flatters us, and we note that the one-model version — which does
produce a comfortable number — is available to anyone who wants to run only one
model.

### (d) The answer: renaming every column

This is the control that has none of the above problems. It is per-model, it has
no parsing blind spot, and it separates the capability under test from the
strings the model might have memorised: a model that can complete Titanic's
schema still has to decide that `boat` is unavailable at boarding.

All 306 Stratum-A columns are mapped to string-distinct aliases under a
bijection passing four mechanical checks (Appendix E); the dataset name is
renamed too, so nothing in the prompt identifies the table. Both arms are scored
on the same datasets, conditions and shuffle seed. The statistic is the
**decrement**: F1 on real names minus F1 on aliases, matched cell by cell.

Across **46 model-condition cells from 8 models**, of which **44 are live** —
two score 0.000 in both arms at C3, so their difference carries no information:
mean decrement **+0.089**, median **+0.053**.

| model | mean | C1 | C6 | worst condition | datasets |
|---|---|---|---|---|---|
| **`claude-opus-5`** | **−0.015** | **−0.011** | **−0.019** | −0.011 (C1) | 14 |
| `nemotron-3-super-120b` | +0.009 | +0.082 | +0.013 | +0.089 (C0) | 13–14 |
| `gemini-3.7-flash` | +0.013 | −0.010 | +0.021 | +0.057 (C2) | 12 |
| `DeepSeek-V4-Pro` | +0.019 † | +0.211 | +0.030 | +0.320 (C0) | 13 |
| `gemini-3.5-flash` | +0.049 | +0.041 | +0.000 | +0.138 (C0) | 12 |
| **`gpt-5.6-sol`** | **+0.059** | **+0.140** | **−0.022** | +0.140 (C1) | 14 |
| `deepseek-v4-flash-0731` | +0.158 | +0.158 | +0.231 | +0.231 (C6) | 14 |
| `Qwen3-Coder-480B` | **+0.376** | +0.157 | +0.326 | **+0.759 (C5)** | 12 |

**The two models the headline rests on are now in the control.** They were the
gap in every earlier version of this section: `claude-opus-5` and `gpt-5.6-sol`
run through an agent loop rather than an HTTP endpoint, so no background pass
could reach them, and a renaming experiment that omits the two best models
cannot answer the question it is asked. Both were run by hand over a 36-prompt
packet mirroring their existing real-name cells exactly — same 14 datasets,
same conditions, same seeds, same column ordering — and ingested only after
every cell passed a column-coverage and verdict-vocabulary check.

At **C6, the condition the headline rests on, both are slightly NEGATIVE**:
Opus −0.019, GPT −0.022. They score marginally *better* when every column is
renamed. Whatever these two are doing, it does not depend on the strings.

**GPT's C1 is the exception and is reported as one.** It loses **0.140** with
names removed (0.864 → 0.725), the third-largest C1 decrement in the roster.
The pattern is coherent rather than anomalous: under aliasing GPT's C1→C6 gain
is **+0.215** (0.725 → 0.940) against **+0.054** on real names. The derivation
clause does more work precisely when the names carry no information — which is
what §6.2 claims the clause is for, arrived at here from the opposite
direction.

Five of the eight lose under 0.06 F1 on average from having every column renamed,
and `gemini-3.7-flash` is *better* on aliases at C1. **`Qwen3-Coder-480B` is the
outlier by a factor of two over the next model**: it loses 0.759 F1 at C5 and
0.523 at C2, and its decrement exceeds 0.15 at five of seven conditions. One
model in this roster substantially depends on the column strings, and we report
it as a per-model result rather than averaging it away — the pooled three-model
table in the earlier version of this section could not have shown it.

† **`DeepSeek-V4-Pro`'s mean is misleading and we do not use it.** It is an
average over six positive decrements (+0.030 to +0.320) and one cell, C3, where
the model scores **0.000 on real names and 0.889 on aliases** — a −0.889 outlier
that is a model failure at C3, not a paraphrase effect. Excluding C3 its mean is
**+0.170**, which puts it second only to Qwen-480B. A reader should take the
per-condition column, not the mean, for this model.

Two further cautions. The comparison is matched cell-by-cell within a model but
**not across models**: `deepseek-v4-flash` and `nemotron` carry 14 datasets
because the Stratum C tables entered their grid, the rest carry 12, so the
column of means is six within-model differences and not a ranking on common
ground. And a join failure on `nemotron`/KOI/C1 drops that dataset from **both**
arms — earlier drafts of the scorer dropped it from one, which inflated that
cell's decrement from the true +0.082 to +0.114.

The same control on **cirrhosis** (§6.4.5) is the sharpest single case: the Mayo
Clinic PBC trial, with four further copies on Kaggle and `pbc` shipped in R's
`survival` package, is the most redistributed table in the corpus, and **six of
seven models score identically on it under aliasing**.

### (e) What the four measurements say together

* The models do not have the **data** (0/675 rows).
* Several do have much of the **schema** (up to 61% of leaking columns).
* Most do not need the schema to produce the **answer** (median decrement
  +0.053 over 44 live cells; five of eight models under +0.06 on average), and
  one of six does.

Recalling a column's name is a different capability from knowing which column
leaks, and these results separate the two directly rather than by argument.

A further reassurance is behavioural: `gpt-5.6-sol` at C1 abstained on **all 40**
KOI columns — *"the deployment prediction point is unspecified"* — and flagged
all four `koi_fpflag_*` correctly at C6. Its abstentions fall from 83 at C1 to 38
at C6. Refusal contingent on the prediction point is not what a memorised answer
key produces.

**The residual risk we cannot exclude** is that a model has memorised not the
table but the *discussion* of it — the Kaggle notebooks and blog posts saying
that `boat` leaks. No renaming defends against that, because the reasoning
survives renaming exactly as the honest capability does. The only clean answer
is a post-cutoff table, and Stratum C supplies one: **ChessFraud** (§6.4.4) was
published in 2026, and models with no possible exposure to it recover
`assistance_line_rank`, whose missingness alone reproduces the label.

---

## Two other passages that move with this section

**Abstract (~line 43).** Replace:

> Because every dataset here is a well-known public table, we run the released
> memorisation checker of Bordt et al. (2024) over all fifteen. The model
> reproduces 33% of column names but only **19% of the leaking ones**, and none
> at all on seven of the datasets; removing the three it recalls completely
> leaves every frontier result above 0.855.

with:

> Because every dataset here is a well-known public table, we run the released
> memorisation checker of Bordt et al. (2024) across four models. They reproduce
> **none of 675 data rows and none of 30 headers**, but up to **61% of the
> leaking column names** — so we test the result by renaming every column, and
> across 44 model-condition cells the median cost is **0.053 F1**, with one
> model of six the clear exception.

**§8 limitations (~line 1010).** Replace the bullet beginning *"The memorisation
evidence is `gemini-3.5-flash` only"* with:

> * **The memorisation evidence covers 4 of 14 models on the schema test and 2
>   on the direct tests**, all of them API-served; `claude-opus-5` and
>   `gpt-5.6-sol` are absent because they were run through an agent loop rather
>   than an HTTP endpoint. Two datasets (CRIME, MI) are too wide for the checker
>   to parse and both are Stratum B. The leave-recalled-out rescoring reported
>   in earlier drafts is withdrawn: at four models it has one usable dataset.
> * **Memorised commentary is not excluded by renaming.** A model that has read
>   that `boat` leaks retains that whether or not the column is called `boat`.
>   ChessFraud (2026, §6.4.4) is the only table in the corpus for which this is
>   ruled out by date.

---

## Open, for the author

The `Qwen3-Coder-480B` decrement is the one number here that argues against the
paper. It is large, it is at five of seven conditions, and Qwen-480B is
otherwise a mid-roster model whose C6 REASON result (33/55 → 55/55) is cited in
§6.3's leave-one-dataset-out as *surviving* the KOI drop when both Gemini models
do not. So the model that best survives the tuning objection is the model that
worst survives the memorisation objection. That tension is real and belongs in
§9 rather than being resolved here.
