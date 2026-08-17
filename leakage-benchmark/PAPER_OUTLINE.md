# Paper outline — target TMLR

**Working title:** *What Do Language Models Mean by "Leakage"? Semantic Detection
of Label-Derived Columns, and Why a Single F1 Cannot Tell Retrieval from Reasoning*

Shorter alternative: *Timing Is Not Derivation: A Controlled Study of LLM
Leakage Detection in Tabular Data*

**Note on numbers.** Every figure below is currently computed on the 10-dataset
corpus. STEEL and ECHO were added afterwards, so the whole results section must
be recomputed on 12 before drafting. B3 in particular moved 0.812 (6 datasets)
→ 0.719 (10) and will move again.

---

## Abstract (~180 words)

Four sentences of setup, four of result.

Data leakage from label-derived columns is a known failure mode, and the tools
that ship today detect it statistically — by correlation or univariate power.
We show those tools are blind by construction to a large class of real leakage,
and that language models are blind to a *different* class, for a reason that can
be named and fixed with one sentence of prompt.

Headline numbers to carry: **12 datasets, 306 columns, 45 documented positives**;
a tuned-on-answers correlation baseline reaches F1 **0.719**; the best model
reaches **0.865**; a paraphrase control collapses one model (0.828 → 0.400)
and leaves another untouched; stating a derivation criterion raises REASON-subtype
recall **44% → 89%** while leaving other subtypes at **81% → 81%**.

---

## 1. Introduction (1.5 pp)

- Open with the concrete case, not the abstraction: `TITANIC.body` correlates
  with survival at 0.014 and is a perfect leak. Correlation cannot see it.
- The gap: point-in-time feature stores solve *bookkeeping*; statistical screens
  solve *correlated* leakage; nothing addresses **semantic provenance** —
  whether a column could have existed at the prediction point.
- Why now: this needed domain knowledge, which was not automatable before ~2023.
- **Contributions**, stated as four bullets:
  1. A documentation-grounded benchmark: 12 datasets, 45 positives, each with a
     verbatim quote, a locator and an evidence tier. No label rests on our
     judgment.
  2. A memorisation control with mechanical self-checks, which separates
     string-retrieval from rule-following and which caught the authors biasing
     two positives in their own favour.
  3. A mechanism: models operationalise leakage as **timing**; a large class of
     real leakage is **derivational** and temporally prior. Established by a
     controlled intervention, not inferred from errors.
  4. A complementarity result and a triage protocol with measured reviewer cost.

---

## 2. Related work (0.75 pp)

Four short paragraphs, each ending in what it does *not* cover.

- **Leakage taxonomy**: Kaufman et al. (2012) availability criterion; Kapoor &
  Narayanan illegitimate features. Defines the problem, offers no detector.
- **Deployed tooling**: feature stores (point-in-time joins) solve TIMING and
  pass REASON columns straight through; statistical screens (deepchecks,
  AutoML target-leakage detectors) are our B2/B3 and we measure their ceiling.
- **Procedural leakage**: notebook static analysis, Roth (2026)'s 2,047-dataset
  study. Different problem — pipeline order, not column semantics.
- **LLMs on tabular data**: the published warning about latent knowledge of
  public tabular datasets, which is *why* the paraphrase control is mandatory
  rather than optional.

Do not oversell novelty. The honest claim is that the *task* was unspecified,
not that nobody thought about leakage.

---

## 3. Problem formulation (0.75 pp)

- **Definition.** A column is label-derived w.r.t. a stated target and a stated
  prediction point if it could not have taken its observed value at that point.
- **Provenance is relative to (column, target, prediction point).** Motivate
  with UCI 579's twelve targets and with SUPPORT2, where the evidence names
  `hospdead` as label-derived and therefore forces the target to be `death`.
- **The three subtypes** (REASON / CONSEQUENCE / TIMING), defined here because
  the whole results section is stratified by them.
- State plainly that TIMING is the subtype existing tooling already solves.

---

## 4. Benchmark construction (1.5 pp)

The section that makes everything else admissible.

- **Evidence standard E1–E4** and the explicit exclusion list: not our judgment,
  not correlation, not feature importance, not an LLM's opinion. Emphasise the
  last: *the models under evaluation never contributed to the ground truth they
  are scored against.*
- **Scope matters** (§8a): a dictionary's silence is informative, a paper's
  exclusion list's silence is not; agreement is computed only within scope.
- **Harvesting pipeline**: anchored on distributed column lists (I5), two
  licence vocabularies (temporal and derivational), sentence-scoped for the
  latter.
- **Table 1**: the 12 datasets — rows, columns, positives, target, prediction
  point, evidence tier.
- **Attrition (§3b)**: 20 datasets processed → 12 with evidence → 8 with none.
  POLISH excluded by I2 (anonymised columns). This is a **finding**, not an
  apology: 40% of datasets we could load could not be provenance-audited from
  their own literature.
- **Reliability**: SUPPORT2 κ = 0.316 between two published papers — the field
  itself agrees on 4 of 15 columns.

---

## 5. Experimental setup (0.75 pp)

- **The condition ladder** C0–C7, one variable each. C0 is the ill-posed
  control (no target); C6 adds the derivation criterion; C7 adds surrogates.
- **Models**: 2 Gemini Flash + 4 open (480B, 80B, Mistral-Large, Llama-70B).
  State plainly that Pro-tier was unreachable (no quota on the available keys).
- **Baselines B0–B4**, thresholds swept on the test answers, therefore **upper
  bounds**. Say why a weak baseline would be a strawman.
- **Scoring**: positive class only (14.6% prevalence makes accuracy
  meaningless); ABSTAIN counted as not-flagged (conservative, matches what a
  practitioner experiences).
- Seeds, shuffling, and the completeness rule: a cell covering fewer datasets
  is never compared to a full one.

---

## 6. Results

### 6.1 LLMs clear the statistical ceiling (0.5 pp)
Table 2: baselines vs models. B3 = 0.719 with 3 false positives that include
`TITANIC.sex`. Best model 0.865. Note the asymmetry: B3's threshold is fitted
on the answers, the model saw none.

### 6.2 The same score, two different mechanisms (0.75 pp)
**Table 3** — the paraphrase control. Qwen-480B 0.828 → 0.400; gemini-3.7
0.828 → 0.828. AI4I is the vignette: 4/4 → 0/4 on `TWF` → `tw_f`, same letters,
one inserted underscore.
State the limitation *here*, not in §8: the control preserves domain, so it
separates string-retrieval from rule-following and does not exclude
re-identification. Quote the model decoding `hd_f` → "heat dissipation failure".

### 6.3 Prompt engineering does nothing (0.4 pp)
C0–C5 flat. `gemini-3.7-flash` returns the **byte-identical** set of 12 columns
at every condition including C0, where it is not given a target and the question
is formally ill-posed. This is the negative result that motivates §6.4.

### 6.4 The failure is definitional (1 pp) — **the central section**
**Table 4**: recall by subtype × condition. REASON pinned at 44% across five
conditions, → 89% at C6; CONSEQUENCE+TIMING 81% → 81%; precision *rises*.
Reproduced in a second model.
Paired quotes from the same column at C1 and C6 — same knowledge, different
question:
> C1 `koi_fpflag_ss` AVAILABLE — "generated by automated vetting prior to disposition"
> C6 `koi_fpflag_ss` UNAVAILABLE — "records the flag used to determine the target"

### 6.5 A fourth subtype the taxonomy was missing (0.5 pp)
SUPPORT2's `prg2m`/`prg6m` are prior *estimates of the target* — not later, not
consequences, not inputs. C7's clause was registered in code before the run and
moved exactly those two, FP 1 → 0. Also report honestly that the authors had
mis-coded these as CONSEQUENCE from the source records.

### 6.6 The screens are blind in opposite directions (0.75 pp)
**Table 5 / Figure 1**: B3 REASON 89% / CONSEQUENCE 48%; LLM the mirror image.
Explain the mechanism — a REASON column determines the label so it correlates
by construction; a CONSEQUENCE column is weakly correlated and semantically
obvious. List the columns each screen finds alone.

### 6.7 Triage (0.5 pp)
Tier 1 (both agree): precision **1.000**. Tier 2 (either): 16% of columns
reviewed, 89% of leaks caught. Frame as reviewer effort, and say explicitly
that autonomous deletion is **not** recommended — B3 would delete `sex`.

### 6.8 Transfer test (0.4 pp) — **report the null**
STEEL/ECHO held out. Both models already at 6/6 REASON at C1, so C6 has no gap
to close: no harm, no confirmation. Explain why — STEEL's REASON columns are
*lexically transparent* (`Other_Faults` vs `Pastry`…), whereas KOI/AI4I are
opaque. **REASON splits into transparent and opaque, and the C6 effect lives in
the opaque half.** State that this leaves the tuning objection open.

### 6.9 How little explicit documentation exists (0.5 pp) — **new, and it may belong in §1**
Both public repositories swept in full: 660 UCI records, 6,420 OpenML
descriptions. Sieve over every prose field plus a heading pass; every hit read.
**6 datasets in 7,080 (0.085%) carry an explicit, column-level statement of
feature-level target leakage — none of them on OpenML.** OpenML's ten
leakage sentences are entirely about duplicate rows, identifiers and train/test
overlap. Table: hits classified as target-leak / group / contamination /
identifier / false positive, per repository.

This is the motivation as a measurement. It answers "why does no tool exist?"
without speculation — there is no labelled corpus to build or evaluate one on —
and it justifies the cost of hand curation. **Consider promoting the headline
number into the introduction**; it is the most quotable sentence in the paper.

### 6.10 Held-out, explicitly-sourced evaluation (0.75 pp) — **a null, and it must be the honest kind**
3 datasets, 298 columns, 30 positives, ground truth = the source's own words
(`explicitness: NAMED_BY_SOURCE`), selected by a criterion independent of any
model. Full ladder, Qwen-480B, 3 seeds on C1/C2/C6.

**No condition effect survives.** The C1 seed spread is **0.312 F1**, four
times the +/-0.07 measured on the main corpus and larger than any difference
between conditions. On MI, CONSEQUENCE recall runs 27% / 100% / 100% across
three shuffles of the same 122 column names.

What is stable: REASON 24/24 and TIMING 27/27 at 100% in every condition and
every seed. The split is **lexically transparent vs opaque**, not condition.

This is the paper's honest limit and should be written as one, in the results,
not the limitations section. It reframes the contribution: the benchmark and
the scarcity result are the durable parts; the prompt effect is corpus-specific
and order-sensitive. **Order-averaging (k shuffles, majority vote) becomes a
requirement rather than a refinement** — flag as the obvious next experiment.

### 6.11 What the leakage costs (0.75 pp) — **the section that makes it matter to a practitioner**
Four arms differing only in columns present; two learners; group-aware splits.
Documented leaks inflate AUC by **+0.130 (rf) / +0.133 (gb)**, max 0.357.
Dropping what the LLM flags lands **0.025** from the honest ceiling; the tuned
correlation baseline lands 0.076 away and misses in *both* directions —
under-dropping `recoveries` on LC, over-dropping `sex` on TITANIC. That
two-sided failure is the argument that a threshold cannot do this job.

---

## 7. Discussion (0.75 pp)

- The finding is a **definitional gap**, not a capability ceiling — and gaps are
  closable with a sentence, which is good news for practitioners.
- Why no such software exists: the task was never specified, and the field does
  not agree (κ = 0.316).
- What a leakage-detection tool should therefore be: a two-screen triage with a
  human in the loop, not an autonomous deleter.

## 8. Limitations (0.5 pp, its own section, not a footnote)

Seeds; paraphrase covers 6 of 12; re-identification not excluded; C6/C7 tuned
and evaluated on overlapping data with the transfer test inconclusive; SUPPORT2
is 1/3 of all positives; 21 of 45 subtype codes are analyst-assigned; negatives
are legitimate-by-default; Pro-tier models untested; C3 rests on 2 datasets.

## 9. Conclusion (0.2 pp)

---

# Appendix

**A. Protocol, verbatim.** The full harvesting protocol including the deviations
log with dates and reasons. Reviewers who care will read this; it is the
strongest evidence of good faith.

**B. Complete evidence table.** All 45 positives: dataset, column, target,
prediction point, subtype, coder, evidence tier, scope, source citation,
locator, verbatim quote (≤25 words). One row per record, so disagreements are
per-row.

**C. Attrition detail.** The 8 datasets with zero admissible evidence and why;
the 20-dataset funnel; the reject file's reason histogram.

**D. Prompts, verbatim.** All eight conditions exactly as sent, including the
system message and one full worked example. Note the C6 clause is appended
after the JSON format spec — a structural flaw, reported rather than silently
fixed, because the transfer test requires a byte-identical instrument.

**E. Paraphrase map and its checks.** The full alias table plus C1–C4 and what
they caught, including the two positives the authors made harder in their own
favour before the check fired.

**F. Per-dataset, per-condition results.** The full grid with coverage counts,
so no partial cell can be read as complete.

**G. Model reasons, curated.** ~20 verbatim reasons, chosen to show mechanism
rather than to flatter: the KOI C1/C6 pair, the AI4I paraphrase decode, the
SUPPORT2 surrogate reasons, and `discharge_disposition_id` where we think the
model's argument is better than our label.

**H. Bugs found and fixed.** All 12, each with what it would have changed. Pair
with the sanity suite (10 checks). This is a credibility asset — most papers
cannot show their instrument caught them out.

**I. Compute and reproducibility.** Model versions, dates, token counts, cache
structure, cost. Note the response cache makes every number re-derivable
without re-calling any API.

---

## Figures

1. **Complementarity** — grouped bars, recall by subtype for B3 / LLM / union.
   The single most quotable image in the paper.
2. **Condition ladder** — F1 across C0–C7 per model, flat then a step at C6.
3. **Paraphrase collapse** — before/after per dataset, Qwen vs Gemini.

Three is enough. Everything else is a table.

## Ordering advice

Write §4 (benchmark) and §6.4 (the central result) first — the rest follows from
them. Write the abstract last. Do not draft anything until the 12-dataset
recompute, seeds, and leave-one-dataset-out are done, or the numbers will
change under the prose.
