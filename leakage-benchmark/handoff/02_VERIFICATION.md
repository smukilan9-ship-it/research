# Verification — how numbers get from data to prose

This is the part of the project most worth understanding before you edit
anything, because it is what stops the paper rotting.

## The flow

```
raw CSVs + responses/ ──► verify_paper.py ──► NUMBERS.txt ──► PAPER*.md
                                                    │
                                       five checkers read both ends
```

`NUMBERS.txt` is **generated**, 24 sections, ~1,300 lines. Editing it by hand
defeats the entire stack. To change a figure, change the code.

## The five checkers, and why one was not enough

Each exists because it catches a class the others structurally cannot. This is
not defence in depth for its own sake — every one of them was written *after* an
error the existing checkers had passed clean.

| checker | asks | the error that created it |
|---|---|---|
| `verify_tables.py` | does this table **row** match its source row? | table rows drifting from regenerated numbers |
| `verify_arithmetic.py` | is this stated relation self-consistent? | subtraction errors in F1 deltas |
| `claim_audit.py` | does this decimal appear **somewhere** in NUMBERS? | `12.6%` — which appeared, somewhere else |
| `prose_pins.py` | does this **sentence's** quantity match the function that computes it? | **the big one, below** |
| `consistency.py` | is any stale figure loose across the deliverables? | Kaggle counts changing in one file and not another |

### Why `prose_pins.py` exists

The paper once said *"8 of 64 positives (12.5%)"* while the corpus had moved to
8 of 56. **8/64 is 12.5%.** The pair was internally perfect and externally
wrong. `verify_arithmetic` passed it — the relation holds. `claim_audit` passed
it — 12.5 appears in NUMBERS. `verify_tables` never saw it — a sentence is not a
row. Every drift found in this project (12.6% base rate, 8 of 64, 15 of 46,
17 of 30, 42 of 46) sat in a section that was *not rewritten* in the revision
that moved the underlying number. Regeneration protects tables; nothing
protected sentences.

A pin is a pair: a regex capturing what the prose states, and a function
recomputing it from `NUMBERS.txt`. **20 pins currently.**

Three design rules in it are load-bearing:

- **A missing pattern is a FAILURE, not a skip.** A checker that stops looking
  when prose is reworded is the same defect one layer up.
- **`r0()` rounds half-up.** Python's `round()` is banker's: `round(96.5)` is 96.
  Pinning a correctly-rounded 97% against it reported a failure on a right
  number, and a checker that cries wolf gets muted.
- **A flattened-whitespace fallback.** A claim rewrapped across different line
  breaks is the same claim; reflowing a paragraph must not silently unpin it.
- **Duplicate pins declare their primary.** A quantity stated twice must agree
  with itself; a quantity stated once is not unchecked. `PAPER_SHORT.md`
  legitimately reports `1 not applicable` for this reason.

## Conventions that are stated because they are choices

- **Mean over models, complete rosters.** Subtype aggregates average per-model
  rows over the **nine** models with no missing cell. A per-model row is a
  per-model claim and is honest about its own cells; a mean treats each row as
  one comparable unit, and a row missing cells non-randomly is not one.
  `incomplete_rosters()` derives that set from the live quarantine, never a
  hardcoded list, so a refill moves it automatically. Both figures are printed;
  including the incomplete roster moves nothing by more than a point.
- **Matched cells.** Every condition comparison is made on the (dataset,
  shuffle) pairs answered under **both** arms. Restricting on datasets alone
  gave a REASON denominator of 51 where it should have been 42.
- **Baselines are swept on the answers**, making each an upper bound no
  deployment could reach. Deliberate: an untuned baseline is a strawman.

## Determinism

Anything stochastic is seeded, and the seeding is verified across
`PYTHONHASHSEED`, not assumed. This caught a real bug: `subtype_sensitivity.py`
drew a *different* adversarial subset on every run despite a fixed seed, because
its population list was built from set-iteration order, which follows Python's
string hash. Two regenerations of §21 disagreed in the third digit. The fix is a
`sorted()`; the check is:

```bash
for i in 1 2; do PYTHONHASHSEED=$i python3 subtype_sensitivity.py | md5sum; done
```

Both hashes must match. Do the same for anything new that samples.

## After any edit

Re-run all five on **both** manuscripts. They share `NUMBERS.txt`, so a number
that moves invalidates sentences in each.
