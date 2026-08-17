# Overnight summary — read this first

*Covers roughly 00:30–04:00 UTC, 16 Aug. Nothing has been committed to any
repository.*

> **SUPERSEDED IN TWO WAYS — read `PENDING_PAPER_EDITS.md` for current state.**
>
> 1. Everything below has since been applied to `PAPER.md` and `APPENDIX.md`.
> 2. The **P1–P9 "registered prediction" framing has been cut** from the paper,
>    along with "pre-registered" for the sieve: neither had a registry deposit
>    behind it, so the wording was an overclaim. Every measurement survived;
>    only the framing went. Read "a failed registered prediction" below as
>    "zero admissible Kaggle records", and `REGISTERED_SCORECARD.md` is now
>    `WORKING_scorecard_superseded.md`.

---

## The one-paragraph version

Stratum C is finished on the Kaggle side and the answer is a **failed
registered prediction, reported as one**: zero admissible datasets in 8,693,
against a forecast of 2–8. The sweep still earns its place, because P2 —
that anchoring, not triggering, would be the dominant failure — **holds in
three independent populations**. Separately, the memorisation section got
materially stronger and its old version turned out to be wrong in our favour:
the models reproduce **none of 675 data rows and none of 30 headers**, which is
the best evidence in the project that the result is not recall. Eight bugs were
found and fixed, one of which had silently destroyed a completed measurement.

---

## What needs your decision (nothing else is blocked on you)

**1. ChessFraud's coding — the biggest open item.** Five candidate positives
that are not equivalent: three are the label-producing apparatus (unambiguous),
`is_accused_by_opponent` is post-game and arguably CONTESTED, and
`is_cheating_player_game` is plausibly a *second target* rather than a feature.
On a record with ΔF1 = 0.632 — the largest downstream effect in the corpus — a
self-serving coding choice would do more damage than anywhere else, so it is
left open. It is also the only post-cutoff (2026) table in the corpus, which
makes it the one memorisation control with nothing to recall. **Bike Sharing
has been admitted** in the meantime, because its coding is the uploader's word
("Leakage") and not a reading of mine.

**2. §4.3's OpenML zero is false** and the fix is a framing call. Klaverjas2018
documents two columns as *"should not be used as predictors"*. The cause is a
methods defect — the UCI and OpenML columns were produced by *different* sieves
and presented under one row label. `6 in 7,109 — 0.084%` becomes
`7 in 7,109 — 0.098%`.

**3. Two drafts are ready to drop in**: `SECTION3_DRAFT.md` (§3 Related work,
which was still a placeholder) and `SECTION7_DRAFT.md` (the memorisation
section). Both are written; neither is applied.

**4. ~~Larsen & Becker ch. 24~~ — RESOLVED, and favourably.** You supplied the
chapter. Their seven types are cut under a deliberately expansive definition,
and **only type 1** ("features not available to the model at the time of
prediction") is feature-level target leakage in our sense. Types 2 and 6 are
procedural/competition leaks already excluded by §2.3; types 3, 4, 5 and 7
concern deployment validity, use-case fit, target operationalisation and
same-method bias. So our five mechanisms **refine their type 1** rather than
compete with their seven — a stronger position than we had assumed. Mapping owed
in an appendix.

---

## The results, in order of how much they change the paper

**The models have the schemas, not the data.** Scored properly against
tabmemcheck's own ground truth, and generously to the model: **0 of 675 data
rows and 0 of 30 headers reproduced**, on any dataset, including the three the
schema test calls fully recalled. What they emit is a well-formed forgery —
right schema, right units, plausible ranges, wrong values. This was found only
because I checked my own reporting script: it had been counting tests that
*ran*, not completions that *matched*, and I had already written the false
claim that nemotron reproduced 15/15 headers verbatim. Correction is on the
record in `MEMCHECK_FINDINGS.md`.

**The memorisation bound in the paper is the lowest model measured.** §6.3
quotes 19% of leaking columns recalled — that is `gemini-3.5-flash`, the first
model run. Across four models the range is **19% to 61%**. Worse, the
leave-recalled-out check cannot be recomputed: at four models, ten of twelve
Stratum-A datasets have a leaking column recalled by someone, leaving a clean
set of two, one of which is already excluded downstream as degenerate.
`SECTION7_DRAFT.md` withdraws that check and puts the paraphrase control in its
place, per model.

**The paraphrase control is now complete, and the headline models pass it.**
At **C6 — the condition the headline rests on — `claude-opus-5` scores −0.019
and `gpt-5.6-sol` −0.022**: both are marginally *better* with every column
renamed. GPT's C1 is the exception, losing 0.140, and is reported as one; the
pattern is coherent, since under aliasing its C1→C6 gain is +0.215 against
+0.054 on real names — the derivation clause does most work when the names
carry nothing. Across 44 live cells from 8 models the median cost is 0.053.
`Qwen3-Coder-480B` remains the one model that genuinely depends on the strings:
it loses **0.759 F1** at C5 and averages +0.376, while five of eight models lose
under 0.06. And there is a tension worth putting in §9: Qwen-480B
is *also* the model that best survives the tuning objection in the
leave-one-dataset-out. The model that answers one objection worst answers the
other best.

**Stratum C, final.** The sieve's trigger rate transfers across four
documentation cultures; its **precision does not**. P2 confirmed at 17–30%
anchoring in three populations. P3 failed at zero. P1 came out **split** — on
the raw denominator the sieve fires *more* readily on Kaggle prose (2.97%) than
on UCI (1.89%), and only after exclusions does it fire less (1.50%). The
registration never said which denominator, so both are reported and neither
preferred. P4–P6 are **not scoreable yet**: their frontier arms are queued
behind a provider quota.

**A negative result worth keeping.** On Klaverjas2018 — the dataset that breaks
§4.3's zero, whose documentation plainly says the columns *"should not be used
as predictors"* — **three of four models miss both positives at C1 and at C6**.
Cirrhosis is the contrast: 7 of 10 models hit at both conditions.

---

## Bugs found and fixed

Eight, and they are one family: **state inferred from a stale or partial view.**

1. **`memcheck_all.py` destroyed a completed measurement.** It snapshotted its
   results file at startup and wrote the whole copy back after every test; two
   concurrent passes clobbered each other and gemini-3.7-flash's 15 datasets
   vanished. Now re-reads and merges per key at the point of write. The lost
   payloads are unrecoverable and are being re-measured; every affected figure
   is marked ⚠.
2. **`verify_paper.py` §11 compared unmatched arms** — a join failure dropped a
   cell from one arm and the other was scored anyway. Both arms now drop the
   union.
3. **`memcheck_report_all.py` was being read wrong** (above).
4. **The Kaggle sieve was recompiling regexes in its inner loop** — py-spy
   caught it at 100% CPU for eleven minutes having emitted nothing. 16× and 41×
   in the two hot functions; verified behaviour-identical on 1,500 real records
   with zero verdict changes.
5. **`guard`'s liveness check matched its own shell wrapper**, so a dead job
   read as alive and sat dead. Now walks `/proc` and requires a Python argv[0].
6. **`memcheck_all.py` retried failures that can never succeed** — 12
   deterministic parse errors re-attempted every pass, burning the quota
   gemini-3.7 needed.

7. **ChessFraud's headline ΔF1 had no script behind it.** `1.0000 → 0.3575,
   ΔF1 0.643` was computed ad hoc and the feature set was never recorded, so
   nothing on disk regenerated the corpus's largest downstream effect.
   `chessfraud_downstream.py` now pins every choice: **ΔF1 0.632**, with both
   1.0000 arms exact. The finding is insensitive to the encoding (0.63 ± 0.01),
   and the perfect-determinant result — `assistance_line_rank` null on precisely
   the 29,105 non-cheating rows, **agreement 1.000000** — does not involve a
   model at all.

   My *first* re-derivation of this got 0.3754, and that was wrong in the
   flattering direction: `select_dtypes(include=[np.number])` silently excludes
   `bool`, so three of the five documented columns were never features and the
   "drop the five" arm was really dropping two. A type assertion in the new
   script caught it. Worth knowing generally — numpy does not consider a boolean
   a number.

8. **A surviving supervisor propagated a dead environment.** The container
   restarted at ~02:58. `guard` survived it and correctly relaunched the jobs
   that died — but `guard` was holding the *pre-restart* environment, and the
   egress proxy had moved from port 37375 to 44187. So every job it relaunched
   inherited a dead proxy: four of six were failing every API call with
   `curl exit 7: Failed to connect`, while looking perfectly healthy in `ps`
   and writing "alive Nm" heartbeats to their logs.

   A supervisor surviving the thing it supervises is normally the point. Here it
   was the failure: the one job I relaunched *by hand* was the only one with a
   working proxy. Fixed by killing guard and everything holding the stale port,
   then relaunching from the live shell. **No number was contaminated** — the
   runner does not cache failed cells (zero response files written during the
   outage), and memcheck's 22 connection errors are stored as errors, excluded
   from every rate, and retried.

   Worth carrying forward: after any container restart, check the *environment*
   of long-lived processes, not just whether they are running.

`consistency.py` is a new standing check: it reads the live figures out of the
artefacts and flags any deliverable that quotes a number which should have
moved. It is currently clean.

---

## Judgement calls I made, so you can overrule them

* **I did not retune the re-upload filter**, though the audit found it only
  **48% precise** and though one of its false exclusions is the single most
  interesting card in the Kaggle corpus — a railway-delay table warning about
  *"potential target leakage if used as an input feature for real-time target
  prediction"*, which is exactly §2.1's triple-relative definition. By the time
  I had measured the filter I knew which datasets each threshold admits, and
  moving one then is choosing a filter by its output. The rate and the full
  exclusion list go in the paper instead. If you want it examined, the
  thirteen datasets in its class are enumerated in `MIRROR_PRECISION.md` —
  examine all of them or none.
* **I fixed one filter bug anyway**, because `'compas'` matching the word
  *"encompass"* is a rule failing, not a threshold. It moved three datasets and
  bought nothing.
* **The Opus and GPT paraphrase arms are now run and ingested** (36 hand-run
  prompts each, matched to their existing real-name cells). At C6 both are
  slightly NEGATIVE — Opus −0.019, GPT −0.022 — so the two models the headline
  rests on score marginally better with every column renamed. GPT's C1 loses
  0.140 and is reported as the exception.
* **I did not touch `PAPER.md`.** Eleven repaired cells are still outstanding
  behind Google's quota, and editing the tables twice risks the second edit
  contradicting the first.

---

## Where to look

| file | what it is |
|---|---|
| `PENDING_PAPER_EDITS.md` | **the master list** — six items, with a table saying which are mechanical and which need you |
| `SECTION3_DRAFT.md`, `SECTION7_DRAFT.md` | paper-ready replacements, unapplied |
| `STRATUM_C_SECTION.md` | paper-ready §6.4, final Kaggle numbers |
| `WORKING_scorecard_superseded.md` | P1–P9 scored — retired, kept as project history |
| `MEMCHECK_FINDINGS.md`, `MEMCHECK_SCORED.txt` | memorisation working record and the scored direct tests |
| `MIRROR_PRECISION.md` | the exclusion-filter audit and the decision not to retune |
| `STRATUM_C.md` | 1,012-line working record behind all of it |
| `chessfraud_downstream.py` | pins ChessFraud's arms; the ad-hoc 0.643 had no script behind it |
| `make_figures.py`, `fig_stratc_funnel.png/pdf` | the first paper figure, final numbers only |
| `consistency.py` | run it after any number changes |
