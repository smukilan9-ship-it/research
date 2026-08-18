# Stratum E — state of the unseen-tables experiment

Written 2026-08-19, mid-run. Read `PREREG.md` first: it fixes the question,
the measurement and the decision rule, and it was fixed before any table
existed. Nothing in this file may loosen anything in that one.

## What this is

Every dataset in Strata A–D is public and almost certainly in pretraining, so
none of them separates *the model reasoned about this table* from *the model
recalls this table*. Stratum E is twenty tables generated locally, never
published, with leakage injected by rule and verified row by row.

The surviving objection it exists to kill: *the model memorised these tables,
C1 fails to cue retrieval, and the C6 clause cues it.* That account fits every
number in the paper. It cannot fit a table that has never left this machine.

## The corpus

20 tables, 840 columns, 120 injected positives — exactly 40 REASON,
40 CONSEQUENCE, 40 TIMING. Leak density 14.3% against the real Stratum A's
13.1%. Frozen with SHA256 in `synth/tables/MANIFEST.json`, **`.gitignore`d**.

Each table is its own data-generating process, not one template renamed — a
business rule, a latent hazard, a human adjudicator, a logistic dose-response,
issuer fraud rules, a statutory declaration, element condition states.
Prevalence spans 0.5% to 28%. Mechanism mixes vary (2/2/2, 1/1/3, 3/2/1,
3/3/2) and two tables deliberately lack a mechanism entirely, because their
process does not produce one: `TOWER_OUTAGE` is a physical event with no
adjudication step, so there is nothing that "assigned" the label and inventing
a REASON column there would be inventing the mechanism.

Every table independently passes the PREREG §6 band — B3 between 0.45 and
0.80, judged per table, never on the mean.

## Result so far — PRELIMINARY, 10 of 16 models (2026-08-19 01:05)

    D1  CONSEQUENCE - REASON at C1 : +35.3 points   95% CI [+19.5, +51.8]
    D2  REASON C6 - REASON C1      : +23.1 points
    real corpus: D1 +23.2, D2 +24.8       reading on the subset: REPLICATES

| model | C1 REA | C1 CON | C6 REA | D1 | D2 |
|---|---|---|---|---|---|
| claude-opus-5-max | 60.0% | 87.5% | 85.0% | +27.5 | +25.0 |
| gpt-5.6-sol-xhigh | 40.0% | 82.5% | 82.5% | +42.5 | **+42.5** |
| nemotron-3-super-120b-a12b::high | 32.5% | 77.5% | 62.5% | +45.0 | +30.0 |
| gemini-3.1-pro-preview::vertex | 55.0% | 80.0% | 75.0% | +25.0 | +20.0 |
| gemini-2.5-pro::vertex | 45.0% | 80.0% | 65.0% | +35.0 | +20.0 |
| grok-4.20-reasoning::vertex | 55.0% | 85.0% | 77.5% | +30.0 | +22.5 |
| grok-4.20-non-reasoning::vertex | 57.5% | 80.0% | 60.0% | +22.5 | +2.5 |
| grok-4.1-fast-reasoning::vertex | 40.0% | 85.0% | 65.0% | +45.0 | +25.0 |
| grok-4.1-fast-non-reasoning::vertex | 17.5% | 62.5% | 37.5% | +45.0 | +20.0 |

`gpt-5.6-sol-xhigh` came in via the codex arm at 40/40, every cell with zero
tool calls, and has the largest clause repair in the table.

## Supplementary arms — reported BESIDE the roster, never inside it

Same models on a different host, so a within-model real-vs-synthetic
comparison stays host-consistent. Verified not to substring-match any roster
label, which is what keeps them out of D1/D2:

    gemini-3.5-flash::vertex-think16000-t0.0     40/40 Stratum E, 70 main
    gemini-3.7-flash::vertex-think16000-t0.0     in progress, 72 main
    z-ai/glm-5.2::high            (NIM)          in progress, main chained after

And OFF-ROSTER new models, PREREG Amendment 2, post hoc, barred from every
mean over models:

    nvidia/nemotron-3-nano-30b-a3b::high         scale ladder, low rung
    nvidia/nemotron-3-ultra-550b-a55b::high      scale ladder, high rung

## THE NEMOTRON SCALE LADDER — post hoc, off-roster, and the best evidence
## in the experiment for the memorisation reading

PREREG Amendment 2. Three sizes of one architecture, one training recipe, one
host, one decoding setting, the same prompts. Nothing here enters D1, D2, the
roster, or any mean over models.

| rung | C1 REA | D1 | D2 | F1 synth | F1 real | real − synth |
|---|---|---|---|---|---|---|
| nano 30B-a3b | 52.5% | +17.5 | +20.0 | 0.630 | 0.632 | **−0.002** |
| super 120B-a12b | 32.5% | +45.0 | +30.0 | 0.617 | 0.652 | **−0.035** |
| ultra 550B-a55b | 42.5% | +27.5 | +27.5 | 0.605 | 0.725 | **−0.120** |

**D1 does NOT rise with scale**: +17.5, +45.0, +27.5. Super is an outlier, not
a rung on a trend. nano and super alone looked like a clean pattern; ultra
destroyed it. Do not report a scale story about D1.

**The finding is in the last three columns.** On unseen tables F1 is flat and
mildly declining — 0.630, 0.617, 0.605 — so an 18x parameter increase buys
nothing, and all three sit below B3 (0.717). On the real corpus F1 rises
cleanly — 0.632, 0.652, 0.725. The gap therefore grows monotonically with
size: −0.002, −0.035, −0.120.

The 30B model performs identically on public and unseen data. The 550B model
loses 0.120. **Whatever advantage scale buys is concentrated on data the model
has seen.** On tables that never existed publicly, 550B ≈ 30B.

This is the one comparison the sixteen-model roster structurally cannot make:
the cross-lab roster confounds capability with lab, data and recipe at every
step. It also supplies a mechanism for the F1 inversion recorded above, where
strong models lose ~0.15 and the two weakest gain.

All three rungs are 40/40. Caveats that must travel with the result: three
points is suggestive, not established; it is post hoc; and F1-real is computed
on Stratum A only — which is not a limitation but the deliberate basis, since
every other F1 figure in this file uses the same twelve datasets.

## NIM returns an EMPTY BODY when max-tokens is too high, and lowering it fixes the cell

`ERROR Expecting value: line 1 column 1` is not a transient and retrying at the
same settings does not help. CONTAINER_DAMAGE C6 on ultra failed three times at
`--max-tokens 16000` and succeeded immediately at 8000. This is very likely the
same cause as the six main-corpus cells both new rungs lost (MI, CRIME and
STUDENT at C1 and C6 — the three EXPLICIT datasets, which have the widest
column lists) and as deepseek-v4-flash's four lost Stratum E cells.

The remedy is to lower `--max-tokens`, not to retry. Those six EXPLICIT cells
were deliberately NOT chased: the ladder's F1-real basis is Stratum A by
design, and widening it for two rungs alone would make them incomparable with
every other model in the table.

## z-ai/glm-5.2 on NIM is unusable, and the featherless arm is unaffected

Two independent runs produced the SAME four cells — WAREHOUSE_FULFILMENT and
COMPONENT_REMOVAL at C1 and C6 — and then failed every remaining call with
`no choices in response`. Not dataset-specific: the first four calls succeed
and everything after fails, which reads as a per-model entitlement on that
endpoint. deepseek-v4-flash and all three nemotron rungs run fine on the same
key. The arm was a hedge against featherless stalling; it did not pay off, and
nothing depends on it. `zai-org/GLM-5.2::high` on featherless is the roster
slot and is filling normally.

## Analysis-script hazard worth remembering

`import runner` pulls the repository-root `score.py` into `sys.modules`, so a
later plain `import score` returns the WRONG module — the root scorer, not
`synth/score.py`. It failed loudly with an AttributeError here, but the same
shadowing could return a plausible wrong number instead. Load it by path:
`importlib.util.spec_from_file_location("synth_score", "synth/score.py")`.

## Two mistakes from the 2026-08-19 session, both worth not repeating

**A short cell count is not automatically a gap.** `gemini-3.5-flash::vertex`
holds 70 cells against a 72-cell reference arm. Those two are KOI C9 s1000 and
CRIME C9, and `verify_paper.rescued()` documents them by name: greedy decoding
at t=0.0 loops inside the thinking channel, 46,080 thinking tokens against a
16,000 budget the API does not enforce, `finishReason: MAX_TOKENS`. Determi-
nistic, so it "cannot be retried into existence". Both already exist in the
`::vertex-think16000-t0.7` rescue arm. Ten minutes were spent re-deriving this.

**Two streams of the same model id on one NIM key stall each other.** GLM's
Stratum E run produced 4 cells in two minutes, then nothing for eleven, from
the moment a second `z-ai/glm-5.2` stream started. Four concurrent NIM streams
of *different* models are fine. Same id, serialise. When killing either, kill
the DRIVER before the child, or the script advances into its next stage.

## Earlier result — 7 of 16 models

    D1  CONSEQUENCE - REASON at C1 : +32.9 points   95% CI [+17.2, +49.4]
    D2  REASON C6 - REASON C1      : +19.3 points
    real corpus: D1 +23.2, D2 +24.8

Per model, all 40/40 cells at 100% coverage:

| model | C1 REA | C1 CON | C6 REA | D1 | D2 |
|---|---|---|---|---|---|
| claude-opus-5-max | 60.0% | 87.5% | 85.0% | +27.5 | +25.0 |
| gemini-3.1-pro-preview | 55.0% | 80.0% | 75.0% | +25.0 | +20.0 |
| gemini-2.5-pro | 45.0% | 80.0% | 65.0% | +35.0 | +20.0 |
| grok-4.20-reasoning | 55.0% | 85.0% | 77.5% | +30.0 | +22.5 |
| grok-4.20-non-reasoning | 57.5% | 80.0% | 60.0% | +22.5 | +2.5 |
| grok-4.1-fast-reasoning | 40.0% | 85.0% | 65.0% | +45.0 | +25.0 |
| grok-4.1-fast-non-reasoning | 17.5% | 62.5% | 37.5% | +45.0 | +20.0 |

**The definitional finding replicates and is larger on unseen tables.**
`claude-opus-5-max` — produced by a completely different run mode, one
sub-agent per cell — lands within a point or two of the real corpus on every
figure.

## The other half, which cuts against the paper

F1, real corpus vs Stratum E:

| model | real C1 | synth C1 | Δ | real C6 | synth C6 | Δ |
|---|---|---|---|---|---|---|
| claude-opus-5-max | 0.905 | 0.754 | −0.151 | 0.909 | 0.852 | −0.057 |
| gemini-3.1-pro-preview | 0.886 | 0.723 | −0.163 | 0.929 | 0.805 | −0.124 |
| gemini-2.5-pro | 0.850 | 0.702 | −0.148 | 0.876 | 0.723 | −0.153 |
| grok-4.20-reasoning | 0.810 | 0.669 | −0.141 | 0.905 | 0.705 | −0.200 |
| grok-4.1-fast-reasoning | 0.759 | 0.677 | −0.082 | 0.867 | 0.723 | −0.144 |
| grok-4.20-non-reasoning | 0.574 | 0.738 | **+0.164** | 0.787 | 0.753 | −0.034 |
| grok-4.1-fast-non-reasoning | 0.425 | 0.683 | **+0.258** | 0.609 | 0.741 | +0.132 |

Strong models lose ~0.15; the two weakest *gain*. That inversion is what a
memorisation account predicts: the models with most to recall lose most when
recall is unavailable.

PAPER.md's claim (2) — *"Evidence that models detect what correlation cannot"*
— rests on the best model beating B3 by **+0.288**. On unseen tables at C1 the
margin is **+0.036**.

## THE CAVEAT THAT LIMITS THE NEGATIVE HALF

**B3 scores 0.717 on the synthetic tables and 0.630 on the real ones.** The
correlation baseline is *stronger* on this generator's output, so the closing
margin has two causes and only one of them is about the models. A generator we
wrote produces cleaner correlation structure than nature does.

What survives the caveat is the **absolute** drop (0.905 → 0.754), which makes
no reference to B3. What is shakier is specifically "models no longer beat
correlation".

Do NOT retune the generator to fix this. PREREG §9 gives up that flexibility,
and tuning a baseline after seeing results is the failure the whole file
exists to prevent. Report the absolute drop as primary and the B3 comparison
as secondary, with this paragraph attached.

## Roster status

Complete (40/40), 10 of 16: claude-opus-5-max, gpt-5.6-sol-xhigh,
nemotron-3-super-120b-a12b, gemini-3.1-pro-preview, gemini-2.5-pro,
grok-4.20-reasoning, grok-4.20-non-reasoning, grok-4.1-fast-reasoning,
grok-4.1-fast-non-reasoning (+ the non-roster gemini-3.5-flash::vertex arm).

In progress: Kimi-K3 30/40, deepseek-v4-flash 4/40.

Queued behind Kimi on featherless: GLM-5.2, DeepSeek-V4-Pro,
Qwen3-Coder-480B. Featherless is the bottleneck — Kimi runs at 10.4 min/cell
against its own 2.6 min/cell on the main corpus, one key, and the org
concurrency cap forces --workers 1. Estimated 6-17 h for all four.

PREREG section 8 voids the run below 12 complete models. Reachable without any
Gemini AI Studio cell: 14.

Blocked: **gemini-3.7-flash** 1/40 — AI Studio quota, one key. `keyring()`
reads `GEMINI_API_KEY_1..9` or `GEMINI_API_KEYS` as a comma list; more keys
turn hours into minutes. This is the ONLY model that can still end up absent.

**gpt-5.6-sol-xhigh is no longer blocked.** It was going to be reported absent
because a sub-agent here is Claude. The Codex CLI ships inside
`/Applications/ChatGPT.app/Contents/Resources/codex` — not on `PATH`, found via
`CODEX_CLI_PATH` in `~/.codex/config.toml` — and is authenticated on this
machine, so the model's own harness runs non-interactively. See
`synth/codex_cell.py` and **PREREG Amendment 1**, which records the added run
mode as post-hoc in those words and was committed before any of its cells were
scored.

Queued, nothing left to launch: `/tmp/synth_feather3.sh` chains Kimi-K3 →
GLM-5.2 → DeepSeek-V4-Pro → Qwen3-Coder-480B; `/tmp/synth_nv.sh` chains
nemotron-3-super → deepseek-v4-flash; `/tmp/synth_gem.sh` chains 3.5-flash →
3.7-flash. All serial, `--workers 1 --http-timeout 1800`.

## Run modes are not equivalent, and PREREG says so

13 models via API through `runner.py`. `claude-opus-5-max` by one sub-agent per
cell — user prompt byte-identical and hash-matched, but the *system* prompt is
the harness's and reasoning effort is not settable to "max" from here. Each
such cell carries a `run_mode` field recording that.

`gpt-5.6-sol-xhigh` by `codex exec`, one ephemeral session per cell, with
`shell_tool` and `unified_exec` disabled — the session has no command execution
at all, so unlike a sub-agent it structurally cannot read the answer key
(verified: asked to `ls synth/`, it replies that shell execution is
unavailable). Each cell records `tool_items` from the JSONL event stream and
the driver refuses to cache any cell whose count is not zero. Its system prompt
is Codex's, recorded per cell in `run_mode`. No `--output-schema`, so replies
go through `salvage.parse` like every other arm's.

A sub-agent can also read the answer key, which an API model cannot. Evidence
it did not: the last ACCESS time on every ground-truth file predates the first
dispatch (16:18–17:01 vs ~17:50). Note that a zero-error cell is NOT evidence
of contamination — six cells scored perfectly on tables whose leaks are
transparently post-outcome.

## Files

    PREREG.md                  the plan. fixed before any table existed.
    synth/tables.py            20 independent builders + per-table checks
    synth/generate.py          shared primitives, mechanism-typed
    synth/check.py             PREREG gate validation — run after any change
    synth/export.py            freeze + SHA256 + runner-compatible bundles
    synth/score.py             D1/D2, cluster bootstrap, decision rule
    synth/subagent_cell.py     hand-run cell prep + recording
    synth/codex_cell.py        gpt-5.6-sol-xhigh via `codex exec`, 1 session/cell
    synth/.codexroot/          empty dir each codex session is rooted at
    synth/tables/              THE TABLES — gitignored, never published yet
    synth/prompts/             40 prompt files for the sub-agent path
    synth/answers/             sub-agent raw answers

`runner.py` treats Stratum E through the identical code path as every other
stratum (`SYNTH()` + a branch in `spec_bundle`), so prompts, cache keys and
coverage audit cannot diverge. Stratum E bundles do NOT pass through
`audit.apply()` — that corrects coded labels against evidence records, and
there is no evidence record for a table we generated.

## Next

1. Finish the roster. Everything is running or queued; only gemini-3.7-flash
   needs a human (more AI Studio keys, supplied through the environment loop —
   never pasted into chat).
2. Re-run `synth/score.py`. It refuses to say "verdict" until all 16 are in,
   and refuses to admit a model with fewer than 40 cells — it printed a false
   FAILS TO REPLICATE once, entirely from one 12%-complete row.
3. Only then decide the framing, using PREREG §7's table.

## Do not push the response cache until the runs finish

The cached Stratum E responses list every column name and every verdict.
Pushing them publishes the tables in all but the raw values, which is the
novelty guarantee PREREG §3 rests on. Local commits are fine.
