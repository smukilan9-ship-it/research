# Paper edits owed — ALL SIX APPLIED, PLUS THE PREDICTION CUT

*Applied to `PAPER.md` and `APPENDIX.md` on 16 Aug. `NUMBERS.txt` regenerated.
Backups: `PAPER.md.bak_preedit`, `PAPER.md.bak_prepredcut`, `PAPER.md.bak_p9cut`,
`APPENDIX.md.bak_preedit`, `APPENDIX.md.bak_p9cut`, `NUMBERS.txt.bak_preedit`,
`NUMBERS.txt.bak_p9cut`. Nothing committed to any repository.*

| # | item | status |
|---|---|---|
| 1 | nine table cells | **APPLIED** |
| 2 | §4.3's OpenML zero | **APPLIED** — reports 6 frozen AND 7 corrected |
| 3 | memorisation (§6.3 + abstract + §8) | **APPLIED** — four-way rewrite, 8 models |
| 4 | two Stratum C records | **APPLIED** — §6.4 inserted; ChessFraud left uncoded |
| 5 | re-upload filter precision | **APPLIED** — §6.4.7 + Appendix K |
| 6 | §3 Related work | **APPLIED** — plus Larsen mapping in Appendix J |
| 7 | **the P1–P9 cut** | **APPLIED** — see below |

## 7. The prediction cut

Every "registered prediction" claim is gone from `PAPER.md`. The measurements
under them all survive and are reported as measurements:

| was | is now |
|---|---|
| P1 (sieve fires less on Kaggle) | §6.4.2 — both denominators, "neither is preferred" |
| P2 (anchoring dominates) | §6.4.2 — "**Anchoring, not triggering, is the dominant loss** … only 17–30%" |
| P3 (2–8 admissible Kaggle records) | §6.4.2 — "**The Kaggle arm yields no admissible record at all**" |
| P9 (positive downstream delta) | §6.4.6 — the three-record delta table, Klaverjas reported as documented-but-inert |
| §7.2 "a failed registered prediction" | "The derivation clause moves a different subtype than expected" |

**Why.** Those predictions were written in a scratchpad markdown file. No
external timestamp, no registry deposit, no third party. Calling them
"registered" in a TMLR submission is an overclaim, and the first reviewer to ask
*registered where?* gets an answer nobody wants to give. Deleting a claim you
cannot substantiate is not concealment.

**The same argument retired "pre-registered" for the sieve**, everywhere —
paper, appendix, source, and the `records_founding.jsonl` notes. The
*substance* stays, because it is a claim about code that existed before the
sweep and can be re-run from the artefact bundle: the wording is now "frozen
sieve" / "frozen-sieve rate", and §4.3 says the number "is what the instruments
as frozen found, and is the number the sieve code in the artefact bundle
produces when re-run". `REGISTERED_SCORECARD.md` is retired to
`WORKING_scorecard_superseded.md` with a header explaining why.

## Two real defects found while doing it

**1. `openml_candidates.jsonl` had been overwritten by the Stratum C harvest.**
The file that `openml_scan.py` (the frozen STRONG sieve) owns held 145
wider-gate rows in the harvest's schema. `NUMBERS.txt` was therefore reporting
`OpenML sentences surviving 145 across 85` where §4.3's table says `89 (89
datasets; 10 distinct)` — **the paper's own table row had no source on disk.**
Fixed: the harvest output moved to `openml_wider_candidates.jsonl`, and
`openml_scan.py` re-run. It reproduces its frozen log exactly — 6,420 scanned,
89 sentences across 89 datasets, 1 anchored (`munich-rent-index-1999` /
`cheating`).

Re-running it the first time returned **0 anchored**, because the anchoring step
fetches column lists from the OpenML API and every call failed behind the proxy;
`features()` swallows the exception and returns `[]`. It would have written a
file that looked fine and had silently lost the result. `openml_scan.py` now
reads `openml_meta/features.json` first — the same data, cached by the harvest —
and falls back to the API only for datasets the cache lacks.

**2. `APPENDIX.md` was stale and un-regenerable.** Appendices J and K had been
appended to the built file by hand, so re-running `build_appendix.py` would have
dropped them — which meant it was never re-run, and Appendix F ("`NUMBERS.txt`
in full") was an *older* NUMBERS.txt. It still carried the superseded
DeepSeek-V4-Pro cells (0.757/0.854, 36%) that §7.3 had already been corrected to
(0.582/0.772, 53%): **the appendix contradicted the paper.** J and K now live in
`appendix_jk.md`, which `build_appendix.py` reads, and the appendix is generated
again. Appendix F is now byte-identical to `NUMBERS.txt` (1,131 lines, checked).

**A third, smaller one:** `NUMBERS.txt` said `COMBINED RATE: 7 (6 pre-registered
+ 1 post-hoc)` — the cond_scan combination — while `APPENDIX.md` had a
hand-added WIDER-GATE block with a *different* `CORRECTED RATE: 7`. Two
different sevens side by side. `verify_paper.py` §4 now emits all three tiers in
one place, matching §4.3's stack: **6 frozen (0.084%) → 7 with the OpenML gate
repaired (0.098%) → 8 with the conditional family admitted (0.113%)**.

## Verification state

| check | result |
|---|---|
| `verify_tables.py` | **76 verified, 0 failures** |
| `verify_arithmetic.py` | **438 relations, 0 inconsistent** |
| `claim_audit.py` | **0 unsourced numbers** |
| `consistency.py` | clean, exit 0 |

`verify_arithmetic` was smoke-tested by planting `+9.999` in a delta column: it
failed, named the line, and printed the recomputed value. A checker that cannot
fail is worse than no checker, and this project has already been bitten by one.

## Known-provisional, stated in §8

* **`gemini-3.5-flash`: 11 quarantined cells never restored** (provider quota).
* **Six cells remain truncated** by our own token budget (CRIME, DIABETES, KOI,
  MI ×3). Both lists are printed by `verify_paper.py` §17 on every run.
* **The Opus/GPT paraphrase arm has no seed variance** on CRIME and STUDENT.
  Seed-spread comparisons between arms are invalid; the cell-matched decrement
  is unaffected (re-scoring at seed 1000 alone moves all four cells by 0.000).

## Still open

* ChessFraud's coding, deliberately left open (§6.4.4).
* Memcheck covers 6 of 14 roster models; `gemini-3.7-flash` is at 10/15 and
  `Kimi-K3` at 1/15.

## Round 8 — the VERIFY_V4 audit (Claude Sci)

Three stale figures fixed, one argument repaired, one count reconciled.

| audit item | was | now | source |
|---|---|---|---|
| S1 | triage "contains 91% of the documented leaks (42 of 46)" | "contains **every** documented leak (40 of 40, recall 1.000)" | NUMBERS §14 |
| S1b | "burden sits between 10% and 21%" | "between 10% and **23%**" | NUMBERS §14, max 0.229 |
| S3 | "SUPPORT2 supplies 15 of 46; CRIME 17 of 30" | "**9 of 40**; CRIME **17 of 28**" | NUMBERS §1 |
| S6 | "base rate 12.6%", "8 of 64 positives (12.5%)" | "**11.3%**", "**8 of 56 (14.3%)**" | NUMBERS §15 |
| §3.2/§3.5/App J | "five mechanisms" | "**four**" — §2.2 is *Four mechanisms* since SURROGATE was withdrawn | §2.2 |

S6 needed no code re-run: `verify_paper.py` §15 was already emitting the
audited values (68/604 = 11.3%, 8/56 = 14.3%). Only the prose was stale.
CRIME's "9 of those resting on a single sentence about data vintage" **checks
out** and was left alone — 9 of its 17 records quote the '90-Census/'95-UCR
vintage sentence, 8 quote the calculation sentence.

### The §7.3 repair (the audit's one real finding)

The diagnosis paragraph said DeepSeek-V4-Pro "did not get sloppier, it applied a
narrower rule confidently". The premise for that was a precision *rise* which
the audited numbers reversed: matched cells give C1 P 0.627 → C6 P **0.457**,
false positives 19 → **38**. Substituting "recall holds at 0.800" kept a true
sentence and deleted the reason for the conclusion.

Rewritten to state what actually happened — REASON 10/15 → 8/15 at unchanged
recall, precision falling with it, C6 worse on both axes — and to rest the
diagnosis where it always really rested: **the same six columns flagged and then
un-flagged with the same six words, "measured concurrently."** That is a direct
observation and needs no precision argument. The C9 result it motivates is
untouched.

### New checker: `prose_pins.py`

The audit's sharpest observation was structural: the two fixed items were in
sections rewritten heavily, the three stale ones in sections untouched. That is
the signature of hand-editing rather than regeneration, and **none of the three
existing checkers can see it**:

* `verify_tables` matches table rows; a sentence is not a row.
* `claim_audit` asks whether a decimal appears *somewhere* in NUMBERS. 12.6% did.
* `verify_arithmetic` asks whether a relation is self-consistent. The paper said
  **8 of 64 positives (12.5%)** — and 8/64 *is* 12.5%. Internally perfect,
  externally wrong, and a clean run is exactly what it produced. Confirmed by
  planting the stale pair back: verify_arithmetic still reported 0 inconsistent.

`prose_pins.py` pins seven prose quantities to their source in `NUMBERS.txt` and
fails if either the value disagrees **or the sentence has been reworded away** —
a missing pattern is a failure, not a skip. Smoke-tested by reinstating all
three original stale values: 3 of 7 pins fail, exit 1.

| check | result |
|---|---|
| `verify_tables.py` | 76 verified, 0 failures |
| `verify_arithmetic.py` | 440 relations, 0 inconsistent |
| `prose_pins.py` | **7 pins, 0 failing** |
| `claim_audit.py` | 0 unsourced numbers |
| `consistency.py` | clean, exit 0 |

### Left open from the audit, deliberately

Not stale numbers — additions, listed here so they are not lost:
A3 (circularity named in §7.1), A4 (ECHO contradiction), A5 ("exact" scoped in
the abstract), A6 (bootstrap CIs / McNemar), figures, and naming K&N's **L2**
plus quoting their refusal to sub-categorise it in §3.2.

## Round 9 — A3/A4/A5/A6, L2, figures

| item | done |
|---|---|
| **A3** circularity | §7.1 no longer claims GPT's exact Stratum B run is an independent audit. It names the circularity (GPT is under evaluation; using its agreement to license the labels and the labels to license its score) and states the weaker non-circular reading: labels and model may share a common cause, so exact agreement is evidence Stratum B is **lexically easy** — consistent with REASON 24/24 at C0. Says outright that a non-LLM second reader would break the tie and we do not have one. |
| **A4** ECHO | §7.5 called 0.677 "a ceiling". Keeping every column scores **0.684** under the same learner, so the documented cleaning *costs* 0.006 there. Now reported as a second documented-inert case beside Klaverjas, with the sign flipping under gradient boosting (0.721 → 0.742). |
| **A5** "exact" | Abstract now says the 894 judgments are 298 columns judged three times with an identical answer, not 894 independent ones. |
| **A6** stats | New `stats_uncertainty.py`; emitted as NUMBERS §19. |
| **L2** | §3.2 names **L2, "model uses features that are not legitimate"**, and that it is the one K&N type carrying no sub-types. |
| **Figures** | Figure 1 (Stratum C funnel) referenced in §6.4.2; **Figure 2** (new forest plot) in §6.5. |

### A second copy of the S3 stale figure, which the audit missed

§6.3(c) also carried "SUPPORT2 ... supplies 15 of the 46 Stratum-A positives" —
same drift, different line, not in VERIFY_V4. Fixed to 9 of 40. Its companion
claim went **3/6 → 6/6 recalled** and a live re-run of `memcheck_report_all.py`
gives **3/6**: the 6/6 came from gemini-3.7 data destroyed by the concurrent-write
race and only partly re-measured. The unreproducible narrative is cut and the
current number stated, with the denominator explained — it is 6 not 9 because
`feature_names_test` supplies part of the schema and scores only what it withholds.
The paragraph's argument (clean set = BONEMARROW and ECHO, 10 of 12 datasets
recalled) re-verified and unchanged.

### A6, and what it does to the paper's story

`stats_uncertainty.py` resamples **datasets**, not columns — CRIME's 17 positives
include 9 resting on one sentence, and a column bootstrap would treat them as 17
independent draws and return an interval far too narrow. Paired with McNemar's
**exact** binomial on discordant per-column decisions (several cells have
b+c < 25, where the chi-square approximation is not trustworthy).

The result qualifies the C6 claim and is not flattering:

* **Every interval that excludes zero belongs to a model scoring under 0.66 at C1.**
  `claude-opus-5` moves +0.004, CI [−0.018, +0.050], p = 1.000 with two columns
  going each way. `Kimi-K3` does not move at all. `gpt-5.6-sol` +0.053, p = 0.125.
* The large, significant gains are Qwen +0.168, deepseek-v4-flash +0.142,
  nemotron +0.132 — all p < 0.01.
* **DeepSeek-V4-Pro is significantly worse at C6** (−0.121, p = 0.009), which is
  independent confirmation of the §7.3 repair made in round 8.

So C6 is a **repair for weak detectors**, not an improvement to the best
instrument — the same conclusion §7.2 reaches from the subtype side by a route
that involves no significance testing at all. §6.5 states this and says the
interval width is the strongest argument in the paper for a larger corpus.

### A third real error, found by the new pin

The abstract said models "reading only column names and a target reach **F1
0.918**". **0.918 is C6** — column names, target, expert framing *and* a
derivation clause. C1's best is **0.905**. The abstract was crediting the leanest
condition with the best number. Nothing in the stack could see it: both figures
are real, both are in NUMBERS, and no arithmetic relation was stated between
them. Fixed, and pinned.

The pin then caught **my own first fix** — I wrote 0.864, which is gpt's C1, not
the best C1. Corrected to 0.905 on the same run.

| check | result |
|---|---|
| `verify_tables.py` | 76 verified, 0 failures |
| `verify_arithmetic.py` | 450 relations, 0 inconsistent |
| `prose_pins.py` | **8 pins, 0 failing** |
| `claim_audit.py` | 0 unsourced numbers |
| `consistency.py` | clean, exit 0 |

### One thing deliberately NOT done

§3.2 names L2 but **quotes nothing**. The audit supplied a verbatim sentence
("requires domain knowledge and can be highly problem specific. As a result, we
do not provide sub-categories for this sort of leakage") and the egress proxy
blocks arxiv, cell.com and sciencedirect, so it could not be checked against the
published text. A paper whose §4 protocol demands verbatim, locatable quotation
cannot ship an unverified one. **Before submission: open the K&N paper, confirm
that sentence, and add it to §3.2 — it is the strongest positioning line
available.**

## Round 10 — TO_87 (N1–N7)

| item | done |
|---|---|
| **N1** roster | §6.4.1 now declares the Stratum C roster explicitly, in four groups, with the reason. §6.4.6's numbers **recomputed** — see below. |
| **N2** forward ref | §4.3 now points to §6.4.5 at the sentence that admits the OpenML zero was wrong. |
| **N3** §9 scarcity | New "**Why no such tool exists**" paragraph: 6 in 7,109 = 0.084% → 0.113% repaired, plus the four-culture replication and its two admissible records. |
| **N4** visibility | Abstract gains a Stratum C paragraph; §1 contribution (1) gains a third-stratum sentence; §8's now-false post-cutoff bullet rewritten and **two new limitation bullets** added. |
| **N5** citations | `[N §11]`, `[N §16]`, `[N §17]`, `[N §18]` added. **All 19 NUMBERS sections are now cited.** |
| **N6** appendices | J and K declared in the paper's appendix list. |
| **N7** four/five | Landed in round 8; 0 occurrences of "five mechanisms" in either document. |

### N1 was worse than reported: the §6.4.6 numbers were wrong, not just the roster

The audit flagged "eight" against §5.3's ten. The cache holds **ten** models on
cirrhosis, and they are largely a *different* ten — only `nemotron-3-super::high`
and `deepseek-v4-flash::high` are in the §5.3 roster; `Kimi-K3` and `GLM-5.2` ran
at a different effort setting; six ran on Stratum C only; six §5.3 models never
ran on it. Recomputed from the response cache:

| paper said | actually |
|---|---|
| "Eight API-served models" | **ten** |
| "Six of eight flag `N_Days` at C1" | **four of ten** (all four with zero false positives) |
| "five of them with zero false positives" | all four |
| "Kimi-K3 and GLM-5.2 are exact at both conditions" | **neither is.** Kimi-K3 hits at C1 and loses it at C6; GLM-5.2 does the reverse |
| — | the only model exact at both is **`nemotron-3-super`** |
| "the two that miss at both" | holds — Qwen2-72B and gemma-4-E4B |

The paragraph is rewritten to the recomputed values, and the finding is now a
**negative** one: fewer than half a ten-model roster finds this leak at the
primary condition, and no model finds it reliably across conditions. C6 raises
hits 4 → 6 but false positives 14 → 20.

**Why this was invisible.** §6.4.6 had no source in `NUMBERS.txt` — Stratum C
detection was never emitted, so no checker could contradict the paragraph.
`verify_paper.py` §18 now prints the full per-model cirrhosis table with the
totals the prose quotes.

**On the roster question specifically**, the composition rules out the reading
the audit feared, and in the wrong direction for us: the Stratum C set contains
**no frontier model at all**, so its numbers are lower bounds on what §5.3's
roster would produce. §6.4.1 says exactly that, and says the two missing
frontier models are missing because they have no API key here and every one of
their cells is prompted by hand.

### On the S1 / §3.2 sequencing note

Already satisfied. S1 landed in round 8: §9 reads "48 of 306 columns — 16% — and
that 16% contains every documented leak (40 of 40, recall 1.000)", and
`prose_pins.py` enforces it against NUMBERS §14 on every run, so it cannot
silently revert. §3.2 quoted no detection figure, so there was no contradiction
to sequence around. Taking the stable-figure suggestion, §3.2 now ends by
pointing at the **burden** — 48 of 306, 16% — which is true pre- and post-audit,
and says what it is for: K&N's remedy for L2 is expert review of the feature
set, and triage puts 16% of the columns in front of that expert instead of all
of them.

| check | result |
|---|---|
| `verify_tables.py` | 76 verified, 0 failures |
| `verify_arithmetic.py` | 450 relations, 0 inconsistent |
| `prose_pins.py` | 8 pins, 0 failing |
| `claim_audit.py` | 0 unsourced numbers |
| `consistency.py` | clean, exit 0 |

Still owed before submission: the K&N verbatim quote for §3.2 (egress blocks
arxiv/Cell/ScienceDirect from this container).

## Round 11 — the TMLR referee's items (a)–(g), plus the §18 collision

All seven applied against `NUMBERS.txt`, and all seven **pinned** so they cannot
drift again. `prose_pins.py` goes 8 → 15 pins.

| item | was | now | source |
|---|---|---|---|
| (a) | "1,279 cells across 4 providers; 114 paraphrased" | **1,808** cached / **462** paraphrase-arm / **1,304** scored, each named for what it counts | §10, §17 |
| (b) | tier gain "+0.083 against +0.044", stated twice | **+0.063 / +0.040**, plus **+0.100** excluding the one negative model | §20 |
| (c) | C4 ablation, 3 models, wrong signs | the **full six-model table**; five up, one sharply down | §6b |
| (d) | "All ten exceed at C6, nine of ten at C1" | **nine** and **eight** | §5, §6 |
| (e) | REASON "62% → 81%" | **60% → 84%**, with the averaging convention stated | §20 |
| (f) | "Eight of ten score REASON below CONSEQUENCE" | **ten of ten** — strengthened, as the referee said | §20 |
| (g) | 6,420 vs 6,418 | **not a typo** — two different sweeps; the one line using the wrong figure is fixed and the distinction is now stated | §4 |
| — | `NUMBERS.txt` had **two sections numbered 18** | Stratum C 18, uncertainty 19, prose quantities **20** | — |

### What made (e) and (f) invisible

Both were computable two defensible ways and the paper stated a third. Mean-of-
models gives REASON 59.8% → 83.5%; pooling columns gives 51.7% → 86.9%. The
manuscript said 62% → 81%, which is neither — and no checker could see it,
because both conventions are plausible readings of the same table and neither
produces a stated arithmetic relation. `verify_paper.py` now **emits the
aggregate itself** (§20), so the paper cites a number instead of computing one,
and the convention is stated in §6.2 in one sentence.

(f) was understated, not overstated: it is ten of ten, not eight. Worth noting
because every other error this round ran the flattering way.

### Two bugs in the new pins, both caught by their own smoke test

* **Python's `round()` is banker's rounding.** `round(96.5)` is **96**, so a
  correctly-rounded 97% in the paper reported as a failure. A pin that cries
  wolf gets muted, which is worse than no pin. Added `r0()`, half-up.
* **A source function pointed at the wrong section** and raised
  `AttributeError` instead of reporting a miss. The subtype aggregate lives in
  §20, not §6 — a source function that cannot locate its own block must fail
  loudly, and this one crashed instead.

Smoke-tested by reinstating the referee's three original figures: two report
FAIL with the source value, and the third — "All ten models exceed" — is caught
as **MISSING**, because rewording a pinned claim away is a failure and not a
silent skip.

| check | result |
|---|---|
| `verify_tables.py` | 76 verified, 0 failures |
| `verify_arithmetic.py` | 456 relations, 0 inconsistent |
| `prose_pins.py` | **15 pins, 0 failing** |
| `claim_audit.py` | 0 unsourced numbers |
| `consistency.py` | clean, exit 0 |

### Next, in the order agreed

3. REASON↔CONSEQUENCE swap sensitivity (replaces κ)
2. Stratum D — resolve the `LET_IS` second-target question first
4. gemini-3.5 restore when the quota resets

The coding packet and scorer are built and **not run**, by decision: Stratum D
answers the ground-truth objection better, and the subtype question is answered
by perturbation rather than by a second reader. Kept in the repo as offered
instruments.

## Round 12 — item 3: subtype robustness, in place of κ

New `subtype_sensitivity.py`, emitted as `NUMBERS.txt` §21, written up in §6.2.

**The question κ would have answered is not the question being asked.** κ says
how much two readers would agree; the reviewer wants to know how much §6.2's
result *depends* on their agreeing. The second is answerable from data already
in hand. 33 of the 40 Stratum-A positives sit on the REASON/CONSEQUENCE
boundary; the test relabels a fraction of them along that axis only, because
random relabelling across all four subtypes mostly damages TIMING, which nobody
disputes.

| relabelled | C1 gap | lift margin |
|---|---|---|
| **none, as coded** | **+29.5** | **+20.5** |
| 20% at random | +4.3 to +29.9 | +1.2 to +20.4 |
| 30% at random | −2.3 to +26.1 | −3.8 to +18.2 |
| 20% adversarial, unconstrained | −10.5 | −10.5 |
| 20% adversarial, tier-E3 only | +17.6 | +14.0 |
| 50% adversarial, tier-E3 only | +2.9 | +6.2 |

### The result is mixed, and the middle row is why the analysis was worth running

My prediction was that surviving 20% adversarial flipping would settle it. **It
does not survive** — three flips cut the lift margin from 20.5 to 1.1. That
looked bad until the picks were printed: all three are **KOI's `koi_fpflag_*`
columns**, the vetting decisions that produce `koi_disposition`, each carrying a
data check. Nobody would recode those; the exact-rule sweep would call them
mechanically REASON. The unconstrained adversary was not finding a coding
weakness, it was finding that **three columns can move a headline in a
12-dataset corpus** — the same fact §6.5's wide intervals report from the other
side.

So the fair worst case restricts the adversary to the **22 tier-E3 boundary
positives**, the weakest evidence and the only genuinely arguable ones. There
the lift margin holds at **+6.2 with half of them overturned in the worst
direction**.

§6.2 now states all three tiers and concludes narrowly: the *direction* is not
an artefact of the coding; the *magnitude* should not be read to a decimal; and
none of this shows the partition is correct, only how much the finding depends
on it.

### A real inconsistency found on the way

**`DIABETES.discharge_disposition_id` is REASON in `V.subtype()` — which every
table in the paper uses — and CONSEQUENCE in its own evidence record.** One
column, and it sits exactly on the boundary this whole analysis is about. The
corpus disagrees with itself. **Still open — needs a decision, not a default:**
one source has to win and the tables currently take `V.subtype()`.

| check | result |
|---|---|
| `verify_tables.py` | 76 verified, 0 failures |
| `verify_arithmetic.py` | 456 relations, 0 inconsistent |
| `prose_pins.py` | 15 pins, 0 failing |
| `claim_audit.py` | 0 unsourced numbers |
| `consistency.py` | clean, exit 0 |

NUMBERS sections renumbered again: 21 subtype robustness, 22 prose quantities.

## Round 13 — item 2: Stratum D

New `stratum_d.py`, emitted as `NUMBERS.txt` §20, written up as §6.4.8. Four
records fetched from UCI and **every rule re-verified row by row on each run** —
nothing taken from the supplied CSV on trust.

| UCI | target ← column | rule | n | ΔF1 (ours) | ΔF1 (as supplied) |
|---|---|---|---|---|---|
| 887 | `age_group` ← `RIDAGEYR` | `≥ 65` | 2,278 | **+0.603** | 0.599 |
| 419 | `class` ← `result` | `≥ 7` | 292 | +0.086 | 0.068 |
| 426 | `class` ← `result` | `≥ 7` | 704 | +0.073 | 0.085 |
| 857 | `class` ← `affected` | 1:1 relabelling | 200 | **+0.014** | 0.007 |
| 275 | `cnt` ← `casual,registered` | exact sum | 17,379 | +0.069 | — |

Ours differ slightly (encoding and `class_weight="balanced"`), and **the two
autism sets swap order** — 0.073 vs 0.086 against 0.085 vs 0.068. They are
within noise of each other at n = 704 and 292 and should not be ranked. The
finding that matters, a forty-fold spread at identical evidential status, is
unaffected.

### The admission rule, and what it caught

An exact rule is not sufficient. **Two of the eight hits have a leak column that
UCI itself marks `Target`:**

* **MI `RAZRIV` ← `LET_IS` — EXCLUDED.** The table has twelve targets; admitting
  one pair licenses 132. Same principle that leaves ChessFraud uncoded, now
  stated once and applied uniformly: a column that is itself an outcome is not
  a feature. *(This reverses the instruction to admit it — the UCI role was a
  fact not in evidence when that call was made.)*
* **STEEL — KEPT and disclosed.** All seven fault columns are `Target`. Kept
  because the practitioner scenario is real there and not in MI, and §6.4.8 now
  says so before a reviewer can find it unmentioned.

### A free result

Scoring the role field as a detector: **"refuse any column the archive marks
`Target`" catches 2 of 8** — the two target-on-target cases — and misses every
genuine one. A second independent reproduction of §4.4's negative result, on a
population chosen by a rule rather than by us.

### Bug caught in my own code

The role-detector population omitted STEEL, so it printed "1 of 7" while the
prose claimed it caught MI **and** STEEL. Exactly the prose/number mismatch this
project keeps finding in the manuscript — reproducing it in the checker would
have been worse.

| check | result |
|---|---|
| `verify_tables.py` | 76 verified, 0 failures |
| `verify_arithmetic.py` | 456 relations, 0 inconsistent |
| `prose_pins.py` | 15 pins, 0 failing |
| `claim_audit.py` | 0 unsourced numbers |
| `consistency.py` | clean, exit 0 |

## NOT READY — what is still open after round 13

1. **Item 4, gemini** — 11 quarantined cells (quota) AND the half that is not
   quota-blocked: mark gemini-3.5 rows provisional *in the tables*, not only in
   §8. Plus the 6 JOIN ERROR cells (STUDENT C2, KOI C1), which are not
   quota-blocked at all and have never been diagnosed.
2. **`DIABETES.discharge_disposition_id`** — REASON in `V.subtype()`, CONSEQUENCE
   in its own record. Needs a decision.
3. **R4** — say at §7.1, not only §5.3, that the exactness result rests on
   hand-run chat-UI cells; pin dates.
4. **R7** — Larsen & Becker year: the referee says that volume is catalogued
   2021, not 2019.
5. **K&N verbatim quote** for §3.2 (egress-blocked here).
6. **R6, length** — the referee asked for a 25–30% cut and named two duplicated
   passages. The paper has grown since.
7. Referee questions 3, 5, 6 — ECHO `still_alive` unmarked in the headline,
   BONEMARROW in detection but not downstream, and pooling A+B in the abstract.

## Round 15 — items 1–5

| # | item | done |
|---|---|---|
| 1 | §8's gemini attribution | **rewritten** — see below |
| 2 | the JOIN ERROR cells | **diagnosed and reported** in §8 |
| 3 | `DIABETES.discharge_disposition_id` | **resolved to CONSEQUENCE**, and it moved real numbers |
| 4 | R4, hand-run frontier arm | **stated at §7.1**, at the claim, not only §5.3 |
| 5 | R7, Larsen & Becker year | **2019 → 2021** in §3.5 and Appendix J |

### 1. The gemini cells were never a token-budget problem

§8 said they were "truncated by our own token budget". Reproduced the real
cause: at **`temperature=0.0`** this model intermittently returns
`finish_reason="length"` after a few hundred visible tokens **whatever
`max_tokens` is** — 12 of 40 columns at a 16,000-token budget on KOI, twice,
deterministically; remove the temperature field and it returns 40/40 and stops
normally. Prompt-specific, not a size limit: CRIME at 144 columns never
truncates at the same setting.

Refilled by **retrying at the unchanged temperature**, not by dropping the
parameter — a cell run at a different temperature is not comparable with the
1,800 it is pooled against. **4 of 11 recovered** (1,808 → 1,812 cells); the
rest are rate-limited and stay quarantined. §8 now states the real cause and
says plainly that this is the paper's own thesis arriving in its own methods
section.

### 2. Both JOIN ERROR cells are format failures

`deepseek-v4-flash` on STUDENT C2 returned a single column named
`Pstatus,paid,etc...`; `nemotron-3-super` on the paraphrased KOI C1 returned the
literal placeholder `<column>`. Neither is a scoring bug or a leakage judgement.
The guard refuses both, correctly, and §8 now says so.

### 3. The DIABETES column — and it changed the headline

`subtypes.py` said REASON, its own evidence record said CONSEQUENCE. Settled by
§2.2's precedence rule: the quotation never says `readmitted` was computed from
the column (step 1 fails), and the terminal levels exist because the patient
died (step 2 applies). **CONSEQUENCE.** The code now matches the record.

This is not cosmetic. It moves §6.2:

| | was | now |
|---|---|---|
| REASON C1 → C6 | 60% → 84% | **63% → 89%** |
| CONSEQUENCE C1 → C6 | 89% → 93% | **85% → 89%** |
| C1 gap | +29.5 | **+21.9** |
| C6 gap | +9.0 | **+0.1** |
| models with REASON < own CONSEQUENCE | 10 of 10 | **8 of 10** |

**The referee's item (f) reverts.** They said "it is ten of ten — strengthen
it." Ten of ten was an artefact of the mis-coded column; correctly coded it is
eight of ten, and the paper now says eight.

The story gets *better* in one place and weaker in another, which is what an
honest correction looks like: the derivation clause now closes the REASON gap
almost exactly (21.9 → 0.1 points), and the C1 level gap is smaller than
claimed. §21's sensitivity was re-run on the corrected coding; **the lift margin
is the robust quantity and the level gap is not** — under 20% unbiased
relabelling the lift margin holds (+2.6 to +21.4) while the level gap already
spans zero. §6.2 now rests on the lift and says why.

### Knock-on corrections

Ten per-model subtype rows, two `gemini-3.5-flash` model rows, and §5.2's cell
counts (1,808 → 1,812; 1,304 → 1,308) all re-synced from `NUMBERS.txt`. Two
pins needed their patterns updated after the rewording.

| check | result |
|---|---|
| `verify_tables.py` | 76 verified, 0 failures |
| `verify_arithmetic.py` | 467 relations, 0 inconsistent |
| `prose_pins.py` | 15 pins, 0 failing |
| `claim_audit.py` | 0 unsourced numbers |
| `consistency.py` | clean, exit 0 |

### Still open

* 7 gemini cells rate-limited (job still running); tables still do not mark
  `gemini-3.5-flash` rows provisional — R5's second half.
* K&N verbatim quote for §3.2 (egress-blocked).
* R6 length; referee questions 3, 5, 6.
* ChessFraud coding, deliberately open.

## Round 16 — R6 and referee questions 3, 5, 6

| item | done |
|---|---|
| **R6** duplications | both removed — **one of them was mine** |
| **Q3** ECHO `still_alive` | headline now reported both ways [N §23] |
| **Q5** BONEMARROW | the two-axes rationale stated in §7.5 |
| **Q6** abstract pooling | strata given separately, combined figure marked "for scale" |

**R6.** The referee named two duplications. Both were still present, and the
§9 pair was **created by me in round 10** — I added a "why no such tool exists"
paragraph for item N3 without noticing the paper already had one making the same
argument with the 0.098% figure. Merged into one, and the §6.3 pair (the
`gpt-5.6-sol` KOI abstention paragraph, written twice with the same 83 → 38
figures) reduced to one. The broader 25–30% cut is **not** done.

**Q3.** `still_alive` implies the target on 45/45 rows, and every model gets it
free. New `verify_paper.py` §23 rescores the headline with it recoded
legitimate: every model loses **0.007–0.021 F1**, best C6 goes **0.918 →
0.905**, ordering unchanged. `DeepSeek-V4-Pro` at C1 *gains* 0.008 because it
never flagged it. The column stays — it is a real column — but the figure is now
in the paper rather than left for a reviewer to compute.

**Q5.** BONEMARROW is out of the downstream headline and in the detection
headline on purpose: they are different axes, which is the same argument
Klaverjas, CKD and ECHO make. Its ΔF1 is degenerate because the cleaned arm has
no signal left; that says nothing about whether its five positives are correctly
coded, and §4.4 recovers 5 of 5 from the dictionary's own wording. Now stated.

**Q6.** The abstract gave 604 columns and 68 positives pooled, in the one place a
reviewer reads first, while nothing else in the paper pools them. It now gives
12 datasets / 40 positives and 3 / 28 separately, with the combined figure
marked as being for scale only.

| check | result |
|---|---|
| `verify_tables.py` | 76 verified, 0 failures |
| `verify_arithmetic.py` | 467 relations, 0 inconsistent |
| `prose_pins.py` | 15 pins, 0 failing |
| `claim_audit.py` | 0 unsourced numbers |
| `consistency.py` | clean, exit 0 |
