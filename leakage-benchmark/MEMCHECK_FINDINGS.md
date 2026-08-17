# Cross-model memorisation — §6.3's bound is computed on the wrong model, and
the direct tests were being read wrong

**Status: 4 of 14 models on the feature-names test, 3 on the direct tests. The
trend across models is one-directional and the numbers will get worse, not
better. Written now so the direction is on record before it is convenient.**

## CORRECTION, 16 Aug — the row-completion and header claims were false

An earlier version of this file said nemotron *"completed the header test on 15
of 15 datasets — verbatim reproduction of the CSV header"* and called it *"the
strongest single piece of memorisation evidence in the project"*.

That was a misreading of my own reporting script. `memcheck_report_all.py`
counts cells that **executed without an API error**. It never compared the
model's completion to the truth. Nemotron's TITANIC header cell, counted as a
success, is:

```
true continuation   ,211.3375,S,2,,1\n1,male,0.9
model completion    1,female,29.0,0,0,30,C,2,,1
```

— not the continuation, but a mangled copy of the prefix it had just been
shown. `memcheck_score.py` now scores both direct tests against the ground
truth tabmemcheck itself returns, and the result reverses the claim. Recorded
rather than quietly amended, because the error ran in the direction that would
have made the paper's own memorisation worry look worse than it is, and a
reader has no way to catch that from the outside.

## The direct tests: no verbatim recall of data, anywhere

`memcheck_score.py`, scored generously to the model (reasoning text mined for
its last CSV-shaped line; comparison truncated to the length of the truth, so
overrun is not penalised):

| model | header exact | mean similarity | rows exact | mean similarity |
|---|---|---|---|---|
| deepseek-v4-flash-0731::high | **0/15** | 0.064 | **0/300** | 0.580 |
| nvidia/nemotron-3-super-120b-a12b::high | **0/15** | 0.203 | **0/375** | 0.393 |

**Zero of 675 data rows and zero of 30 headers were reproduced.** Not one, on
any of the fifteen datasets — including AI4I, BANK and HEARTFAIL, the three the
feature-names test scores as *fully* recalled. No CSV-shaped line could be mined
from 50 of 705 completions (7.1%), the only cells where the scorer rather than
the model could be responsible for a miss.

What the models actually produce is a well-formed *fake*. Nemotron on AI4I:

```
true    L,300.4,311.8,1433,42.2,14,0,0,0,0,0
model   M,300.3,311.8,1592,32.1,11,0,0,0,0,0
```

Right schema, right units, right value ranges, tool-wear counter within three
of the true one because the rows are sequential and the model is *counting*.
That is a model reconstructing a distribution, not reciting a table. It is the
distinction the whole memorisation question turns on, and it is measurable.

## DATA LOSS, 16 Aug 01:23 — gemini-3.7-flash's results were erased

`memcheck_all.py` loaded `memcheck_all.json` **once at startup** and wrote its
whole in-memory copy back after every test. Two passes run concurrently by
design — the loop's child on featherless, a hand-launched one on gemini, because
they are different providers with different quotas — so the two clobbered each
other: last writer wins, and every model the *other* process had added since the
snapshot vanished.

The featherless pass had been running since **20:23**, holding a five-hour-stale
view. gemini-3.7-flash was complete across 15 datasets at 00:38 and was gone by
01:23. Only the payloads are stored; the logs keep just the ok/FAIL line, so
nothing recovers it and the tests are being re-run.

**Every gemini-3.7-flash number below is therefore from a measurement that no
longer exists on disk.** They were real when taken and are reproduced here from
the 01:0x report, but they are marked ⚠ and must be re-confirmed before they
reach `PAPER.md`.

Fixed: `save()` now re-reads the file at the point of write, merges per
(model, dataset, test), and renames a temp file into place. This is the sixth
instance in this project of one bug — state inferred from a stale view and
written back as if current — and `guard.py` had the same one with
`guard_state.json`.

## The feature-names test: the bound is the lowest model measured

§6.3 rests on `tabmemcheck` run against **one** model, gemini-3.5-flash: 33% of
columns from memory but only **19%** of the *leaking* ones (7 of 36), with the
three fully-recalled datasets dropped leaving every frontier model above 0.855.

| model | datasets | all columns recalled | **leaking columns recalled** | errored |
|---|---|---|---|---|
| gemini-3.7-flash ⚠ | 13 | **75%** | 17/36 = 47% | 2 |
| deepseek-v4-flash-0731::high | 13 | 73% | **22/36 = 61%** | 2 |
| nvidia/nemotron-3-super-120b-a12b::high | 13 | 62% | 15/36 = 42% | 2 |
| gemini-3.5-flash | 13 | 34% | 7/36 = 19% | 2 |

deepseek recalls **more than three times** the fraction of leaking columns that
gemini-3.5 does. The bound the paper reports is the **lowest** of the four
models measured and is presented as though it bounded the benchmark.

## The clean set is collapsing

| models measured | datasets with NO leaking column recalled by anyone |
|---|---|
| 1 (gemini-3.5 only) | 3 — the paper's figure |
| 2 (+ nemotron) | 6 |
| 3 (+ deepseek) | 3 |
| **4 (+ gemini-3.7 ⚠)** | **3: BONEMARROW, ECHO, STUDENT** |

**STUDENT is Stratum B.** Within Stratum A — the twelve datasets §6.3's
leave-out check actually operates on — the clean set is **two: BONEMARROW and
ECHO**. BONEMARROW is already excluded from the downstream headline as
degenerate (§8). So the leave-recalled-out check, run honestly across four
models, has one usable dataset left.

Fully recalled by at least one model, at four models measured:

| dataset | leaking columns recalled | by |
|---|---|---|
| AI4I | 4/4 | all four |
| BANK | 1/1 | all four |
| HEARTFAIL | 1/1 | all four |
| SUPPORT2 | 6/6 | gemini-3.7 ⚠ |
| COMPAS | 4/4 | deepseek |
| KOI | 4/4 | nemotron |
| LC | 2/2 | deepseek, nemotron |
| TITANIC | 2/2 | deepseek |
| DIABETES | 1/1 | gemini-3.5, nemotron |
| STEEL | 5/6 | deepseek, gemini-3.7 ⚠ |

SUPPORT2 went from 3/6 to **6/6** on adding one model, and it supplies 15 of
the 46 Stratum-A positives. Re-run against the ten, the leave-out check would
remove nearly all of the corpus and all but a handful of its positives — at
which point it no longer answers the question it was built to answer, because
there is not enough corpus left to answer it with.

## tabmemcheck cannot reach the held-out stratum at all

Every feature-names rate above is over **13 of 15 datasets**, and the two
missing ones are not a sampling choice:

| dataset | columns | feature_names_test successes, across all models |
|---|---|---|
| every other dataset | 9–48 | 4 of 4 |
| **CRIME** | 144 | **0 of 4** |
| **MI** | 122 | **0 of 4** |

The failures are identical for every model and are **parsing errors, not API
errors** — `Error: Could not determine delimiter` and `Exception: Unable to
construct a query where the desired output …`. tabmemcheck's delimiter sniffing
does not survive a 144-column CSV.

**MI and CRIME are Stratum B — the held-out transfer set.** So the
feature-names measurement covers Stratum A and is structurally blind to the
stratum whose whole purpose is to show the result generalises. §6.3 currently
reports a memorisation bound without saying which datasets it could be computed
on. (The *direct* tests do reach all three: row completion ran on CRIME, MI and
STUDENT, and scored 0/25 on each.)

This is a limitation of the instrument, and reporting it is better than quietly
averaging over whatever happened to parse.

*Operational note, no effect on any number:* these twelve failures were being
**retried on every pass by every model**, because the resume logic treated any
stored error as worth another attempt. They are deterministic — byte-identical
message, same two files, every time — so each pass spent its first calls on the
corpus's two widest tables to rediscover a fixed fact, while gemini-3.7, which
needed the quota to finish its remaining datasets, waited behind them.
`memcheck_all.permanent()` now distinguishes a parse failure from a transient
`429`; the 12 permanent ones are skipped and the 31 quota ones are still
retried. They remain stored as errors, excluded from every rate and counted
separately, exactly as before.

## What this does NOT mean, and the evidence for that

It does **not** follow that the detection result is memorisation, and three
independent lines say otherwise.

**One — no data recall at all.** Zero rows in 675. Whatever the models have, it
is not the tables.

**Two — the paraphrase control.** 42 model-condition cells across 6 models, 40
of them live (two score 0.000 in both arms at C3): mean decrement **+0.096**,
median **+0.061**. Four of six models are under +0.06 on average; gemini-3.7 at
C1 is **−0.010**, slightly *better* on aliases. On cirrhosis — the Mayo Clinic
PBC trial, four further copies on Kaggle, `pbc` in R's `survival`, the most
redistributed table in the corpus — six of seven models score identically when
every column name is replaced with a string-distinct alias.

The exception is real and should be reported, not buried: **Qwen3-Coder-480B
loses 0.759 F1 at C5 and 0.523 at C2**, mean **+0.376**, decrement above 0.15 at
five of seven conditions. **DeepSeek-V4-Pro is second at +0.170** once its C3
cell is set aside — there it scores 0.000 on real names and 0.889 on aliases, a
model failure at C3 rather than a paraphrase effect, and averaging it in
understates the model at +0.019. Two models in the roster depend on the strings
more than the rest; that is a per-model finding the single-model bound could
never have produced.

*Scorer fix, same session:* `verify_paper.py`'s paraphrase summary dropped a
join-failed cell from **one** arm and scored the other, turning a matched
comparison into an unmatched one — the exact shape of the earlier 0.000-recall
incident. Both arms now drop the union. It moved nemotron's C1 decrement from
+0.114 to **+0.082**.

**Three — recalling a name is not knowing it leaks.** A model that can complete
Titanic's schema still has to decide that `boat` is unavailable at boarding, and
the paraphrase control shows most of them make that decision without the name.

So the honest statement is narrower and still uncomfortable: **the paper's
stated bound is too generous and was computed on whichever model happened to
run first.**

## What to do

1. Report the **maximum** across models, not the first one measured. At four
   models that is deepseek's 61%, and it will likely rise.
2. §6.3's leave-out check cannot survive dropping ten of twelve Stratum-A
   datasets. Replace it with the paraphrase control as the primary memorisation
   argument — per-model, 500 columns across 16 datasets, no parsing blind spot,
   and it already shows the result surviving for five of six models.
3. Report the direct tests **scored**, not counted. 0/675 rows is a stronger
   and more surprising result than anything the feature-names test gives, and
   it is currently absent from the paper in both directions.
4. Keep excluding errored cells from every rate and counting them separately.
   An API failure is not a memorisation result; the first campaign reported 55
   HTTP 429s as data.

Regenerate: `memcheck_report_all.py` (recall rates), `memcheck_score.py`
(direct tests, → `MEMCHECK_SCORED.txt`), `verify_paper.py` §11 (paraphrase).
