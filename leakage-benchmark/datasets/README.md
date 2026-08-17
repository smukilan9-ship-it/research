# The datasets

All 15, exactly as the experiment used them. 604 columns, 68 documented
positives — the same totals `NUMBERS.txt` reports, and `verify_datasets.py`
checks that on demand.

```
datasets/
  MANIFEST.csv          one row per dataset: rows, columns, positives, SHA256
  <NAME>/
    data.csv.gz         the exact frame the numbers were computed on
    schema.md           what the model actually received, plus the ground truth
```

## What the models saw — read this before assuming

**The models never saw values.** At **C1**, the primary condition and the one
the headline rests on, a model receives *the column names and the target*. No
values, no row counts, no descriptions. That is the paper's whole subject:
leakage lives in what a column *means*, and meaning is carried by documentation
and naming rather than by numbers.

Only **C4** adds five sample rows, and C4 is the ablation — the condition that
tests whether seeing data helps. It is not where any headline comes from.

So the artefact that literally answers "what did the models see" is each
dataset's **`schema.md`**, not its `data.csv.gz`. Each one lists the exact
column names in canonical order, the target, and the prediction point. Column
order is shuffled per seed at run time; the file records the unshuffled order.

## What `data.csv.gz` is, and what it is not

It is **the frame the bundle resolved to** — post-preprocessing, corpus columns
only, plus the target. Every number in the paper that touches values comes from
this: the ground-truth checks, the downstream forests, the baselines.

It is **not** the upstream source file. The loaders drop dead columns, coerce
types and select the corpus columns, so the raw archive download reproduces none
of the paper's numbers on its own. If you want the upstream files, run
`python3 missing_data.py` from the parent directory — it names each one and its
provenance, and deliberately does not guess download URLs.

## Why there are checksums

One of these tables is re-issued by its archive under the same name: NASA
regenerates the KOI cumulative table, so "the same dataset" fetched next year is
a different corpus wearing the same filename. `MANIFEST.csv` carries a SHA256
per frame, and `verify_datasets.py` re-hashes them. That is what makes *the
actual data we used* a checkable claim rather than a hopeful one.

```bash
python3 verify_datasets.py      # from the parent directory
```

It reads `datasets/` **without importing the loaders** — a check that rebuilt
the frames from the same code that exported them would agree with itself by
construction and tell you nothing.

## The corpus at a glance

| stratum | datasets | columns | positives |
|---|---|---|---|
| **A** — coded from documentation | 12 | 306 | 40 |
| **B** — source names the column, held out | 3 | 298 | 28 |

Stratum A: `AI4I BANK BONEMARROW COMPAS DIABETES ECHO HEARTFAIL KOI LC STEEL
SUPPORT2 TITANIC`
Stratum B: `CRIME MI STUDENT`

**STUDENT contributes zero positives and is kept deliberately.** A transfer set
made only of tables that contain leaks would be a different test — and an easier
one.

The strata are **never pooled**. "A source names this column" and "we read a
source's description" is a property of the labels, not noise to average away.

## Licensing

Provenance and licence are recorded per dataset in each `schema.md`. Most are
UCI under CC BY 4.0; COMPAS is ProPublica's public release; the KOI table is
NASA public domain.

**One needs checking before you redistribute it further: `LC`** (Lending Club
accepted loans, obtained via Kaggle). It is included here because it is part of
the corpus and the paper's numbers depend on it, but the Kaggle terms are not
the same as a CC licence. Flagged rather than quietly shipped.
