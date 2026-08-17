# Detecting Feature-Level Target Leakage with Language Models

A source-grounded benchmark, the code that builds it, and the code that checks
the paper against it.

A column **leaks** when it could not honestly have been known at the moment a
model is asked to predict. No splitting scheme repairs it, because the column is
wrong in every split. This repository is the evaluand that did not previously
exist: 604 columns across 15 datasets, 68 documented positives, each licensed by
a written record and most by a verbatim quotation from the dataset's own
documentation.

## Start here

| file | what it is |
|---|---|
| `PAPER_SHORT.md` | the 12-page submission version — **read this one** |
| `PAPER.md` | the long version, ~30 body pages, superset of the above |
| `APPENDIX.md` | generated companion: every record, quotation, prompt and prompt hash |
| `NUMBERS.txt` | **the single source of truth.** Every number in the paper comes from here |
| `PROTOCOL.md` | the coding protocol, written before the corpus was built |

## The rule this project runs on

> A number that is not in `NUMBERS.txt` is unverified and does not belong in the
> paper.

`NUMBERS.txt` is generated, never edited. Everything downstream of it is checked
by a program rather than by rereading:

```bash
python3 verify_paper.py > NUMBERS.txt   # regenerate the source of truth
python3 verify_tables.py  PAPER_SHORT.md   # every table row vs its source row
python3 verify_arithmetic.py PAPER_SHORT.md   # every stated relation is self-consistent
python3 prose_pins.py     PAPER_SHORT.md   # every quantity stated in a SENTENCE
python3 claim_audit.py    PAPER_SHORT.md   # no decimal appears that NUMBERS lacks
python3 consistency.py    PAPER_SHORT.md   # no stale figure across deliverables
python3 pagecount.py                       # body pages, paginated not estimated
```

All five pass on both manuscripts. They exist because each of them caught
something the others structurally could not:

- `verify_tables.py` matches a table **row** against its source row. A number
  stated in a sentence is not a row.
- `claim_audit.py` asks whether a decimal appears **somewhere** in `NUMBERS.txt`.
  `12.6%` appeared — somewhere else.
- `verify_arithmetic.py` asks whether a stated relation is self-consistent. The
  paper once said *"8 of 64 positives (12.5%)"* while the corpus had moved to 8
  of 56. **8/64 is 12.5%.** The pair was internally perfect and externally wrong,
  and a clean arithmetic run is exactly what you get.
- `prose_pins.py` closes that gap: each pin ties one sentence to the function
  that recomputes its value. A **missing** pattern is a failure, not a skip —
  a check that stops looking when prose is reworded is the same defect one layer
  up.

## Layout

```
PAPER_SHORT.md  PAPER.md  APPENDIX.md  NUMBERS.txt   the deliverables
verify_*.py  prose_pins.py  claim_audit.py           the checkers
runner.py  prompts.py  drive*.py  harness.py         the experiment
subtypes.py  explicit_*.py  screen.py                the corpus and its sieve
baselines*.py  downstream*.py  stats_uncertainty.py  the comparisons
responses/                    1,812 cached model cells — every result derives
responses_truncated/          quarantined cells, kept so §17 can name them
openml/  openml_meta/  kaggle_meta/  hf_meta/  ucimeta/    the repository sweeps
figures/                      the two figures, and the code that draws them
```

Scripts locate their data relative to their own file, so the flat layout is
load-bearing. Run them from this directory.

## Before you re-run anything

Four cache files are stored gzipped to keep the repository clonable:

```bash
./restore_caches.sh
```

Raw dataset files are not committed. `python3 missing_data.py` names the ones
your checkout lacks and where each came from; `MANIFEST.md` explains the rest of
what is in and out. **The five checkers above need none of it** — they read
`NUMBERS.txt` and `responses/`, both committed. Raw data is needed only to
re-run `verify_paper.py` itself.

## Credentials

None are in this repository, and none belong in it. Providers are read from
`0600` files that are `.gitignore`d (`feather.env`, `nvidia.env`, `gemini.env`,
`kaggle.token`) and passed to `curl` through `-K` header files so they never
appear in the process table.
