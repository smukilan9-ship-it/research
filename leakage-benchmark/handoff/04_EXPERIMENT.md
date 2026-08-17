# The experiment — conditions, models, cache, providers

## The condition ladder

Each condition adds **exactly one thing** to the previous.

| | |
|---|---|
| **C0** | names only (ill-posed control) |
| **C1** | **+ target column — PRIMARY** |
| C2 | + prediction point |
| C3 | + dataset description |
| C4 | + sample rows (the ablation) |
| C5 | domain-expert reasoning (process → timeline → columns) |
| **C6** | **+ derivation criterion stated (C1 + one clause)** |
| C7 | + surrogate-outcome criterion (C6 + one clause) |
| **C9** | **+ derivation criterion stated *without reference to time*** |

C1 and C6 carry the paper's claims. C9 exists to show the intervention is
brittle: C6 and C9 fail in mirror image, and no wording is uniformly better.
There is no C8.

Prompts are built in `prompts.py`; every prompt is hash-matched and reproduced
in `APPENDIX.md`.

## The models

Ten, from eight laboratories, in two tiers. The tiers are a division of
**provenance, not a ranking** — `Kimi-K3` scores 0.876 above two of the four
frontier models.

**Frontier**: `claude-opus-5` (max), `gpt-5.6-sol` (xhigh), `gemini-3.7-flash`,
`gemini-3.5-flash`
**Replication** (open weights, `reasoning_effort: high`): `Kimi-K3`, `GLM-5.2`,
`Qwen3-Coder-480B`, `nemotron-3-super-120b-a12b`, `DeepSeek-V4-Pro`,
`deepseek-v4-flash-0731`

The canonical list is `MODELS` in `verify_paper.py`. Do not retype it elsewhere.

## The response cache — the irreplaceable artefact

`responses/` holds **1,812 cells**. One cell = one (model, dataset, condition,
seed, paraphrase-flag) answer, stored with its raw completion.

Three counts appear in the paper and count different things:

- **1,812** cached in total
- **462** paraphrase-arm cells with aliased column names (§6.3)
- **1,308** real-name Stratum A/B cells that parse — **the population every
  detection table is computed on**

`responses_truncated/` holds quarantined cells and is kept **deliberately**:
`verify_paper.py` §17 diffs it against the live cache on every run and names the
models whose numbers are provisional. Deleting it would make the paper look more
complete than it is.

### The 216 hand-run cells

`provider: "ui"` marks cells obtained by hand through a chat interface —
108 each for `claude-opus-5` and `gpt-5.6-sol`, across C1/C2/C6/C9 and 15
datasets, prompt hash-matched to the API runs. **These cannot be re-fetched at
any price.** They are the paper's largest reproducibility hole and the subject
of `05_OPEN_WORK.md`.

### The seven missing cells

`gemini-3.5-flash`: KOI at C1/C2/C7, LC at C1/C6, STUDENT at C1/C6. Every table
row computed from this model carries a **†**. The cause is an instrument
interaction, not our token budget — see `07_MISTAKES.md`.

## Providers

| provider | how | models |
|---|---|---|
| `featherless` | API key in `feather.env` | most open-weight models |
| `nvidia` (NIM) | API key in `nvidia.env` | nemotron |
| `gemini` | API key in `gemini.env` | gemini-3.5/3.7-flash |
| `ui` | **hand-run**, ingested via `ingest_ui.py` | claude-opus-5, gpt-5.6-sol |

Keys live in `0600` files, are `.gitignore`d, and are passed to `curl` through
`-K` header files so they never appear in the process table. See
`09_ENVIRONMENT.md`.

## Shuffles and seeds

Column order is shuffled per seed. Most models have **one** shuffle on Stratum
A; `gemini-*` and some others have 3–5. The measured spread between shuffles
reaches **0.380**, which is why §8 says single-shuffle figures should not be read
to three decimals — and why buying more shuffles for the headline model is on the
open-work list.

## Scripts by role

- **run the experiment**: `runner.py`, `prompts.py`, `harness.py`, `drive.py`,
  `drive_nv.py`, `rerun_loop.py`, `ingest_ui.py`
- **build the corpus**: `subtypes.py`, `explicit_scan.py`, `explicit_specs.py`,
  `screen.py`, `newspecs.py`, `stratc_specs.py`
- **sweeps**: `harvest.py`, `kaggle_harvest.py`, `openml_harvest.py`,
  `hf_anchor.py`, `kaggle_deep.py`
- **comparisons**: `baselines10.py`, `baselines_lex.py`, `downstream2.py`,
  `stratc_downstream.py`, `stats_uncertainty.py`, `subtype_sensitivity.py`,
  `stratum_d.py`, `memcheck_all.py`
- **verify**: `verify_paper.py` then the five checkers, plus `pagecount.py`,
  `missing_data.py`
- **build documents**: `build_appendix.py`, `make_figures.py`
