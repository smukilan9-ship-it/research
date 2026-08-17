# Audits received, and how each item was resolved

Four rounds of external review, all applied. Nothing below is outstanding except
where marked.

## Round 1 — `VERIFY_V4.md` (stale numbers)

Applied. The audit found figures the manuscript quoted from earlier corpus
states. All fixed and, more usefully, this round produced `prose_pins.py` so the
class cannot recur silently.

## Round 2 — `TO_87.md` (N1–N7)

Applied. One item was **rebutted in part**: the claim that "every documented
leak" overstated what `NUMBERS.txt` supports was checked and the phrasing found
to be exactly what the triage numbers license (48 of 306 columns containing 40
of 40).

## Round 3 — simulated TMLR referee report (items a–g, R1–R7, questions 1–6)

All applied. The ones that changed the paper materially:

- **(e)** an aggregate matched neither averaging rule → `verify_paper.py` now
  emits the mean-of-models figure and the paper cites rather than computes.
- **(f)** "ten of ten" reverted to "eight of ten" after
  `DIABETES.discharge_disposition_id` was resolved.
- **§9 duplicate paragraph** removed.
- **R5** — mark `gemini-3.5-flash` provisional. Done in §8 *and*, in a later
  round, in the tables themselves with a † and a footnote.

## Round 4 — blind audit (independent, agreed with the internal read)

The audit independently identified the same top two fixes already on the list:
the API run and gemini. Its four items:

**1. The headline rests on cells no reader can re-run.** *Open by design* —
this is `05_OPEN_WORK.md` item 1, waiting on purchased API access. The audit's
"second best" option (re-headline on `gemini-3.7-flash` or `Kimi-K3`) was **not**
taken, because running `claude-opus-5` through Vertex achieves the same end
without demoting the headline.

**2. The abstract oversells a lift §6.5 shows is not significant.** ✅ Applied.
The long version already carried the clause; the short one now states explicitly
that measured in F1 the lift concentrates in weak detectors and that a cluster
bootstrap is consistent with no effect for the three strongest models.

**3. Drop `gemini-3.5-flash` from the main tables.** ✅ Applied, in the sharper
form: per-model rows keep it with a †, and **no mean-over-models statistic
includes it**. The audit's precise complaint — partial rows entering a summary
statistic beside comparable ones — is answered exactly. Aggregates moved by at
most a point (REASON 63→62 at C1; "eight of ten" → "seven of nine") and the
paper reports both conventions. The truncation finding was promoted to
**Appendix L**.

**4. Add a non-LLM, non-correlation baseline.** ✅ Applied as **B1-tuned**, and
the result is the opposite of what the audit predicted — in the paper's favour.

> The audit expected a keyword rule to score *well* on Stratum B (lexically
> easy) and poorly on Stratum A. It scores **0.394 on A and 0.000 on B.**

The tuned vocabulary was fitted on Stratum A only, so Stratum B is a genuine
out-of-sample test: the rule that recovers 14 of 40 positives on one stratum
recovers **0 of 28** on the other, where `gpt-5.6-sol` at C1 is exact. This is
the direct answer to the memorisation reading of §6.3 — if the models were
matching a learned vocabulary of leaky names, the rule encoding exactly that
vocabulary would not score zero where they score one. It also refines what
"Stratum B is lexically easy" means: easy to a reader of English, not to a regex.

**Two smaller items**, both applied:
- The renaming control (−0.019, −0.022 at C6, both frontier models marginally
  *better* fully aliased) is now the abstract's contamination defence, labelled
  as the stronger one — the previous defence (no rows or headers reproduced)
  rules out verbatim memorisation only.
- The **16% triage number** (48 of 306 columns containing 40 of 40 documented
  leaks) now closes both abstracts, replacing the F1 comparison.

**Certification note from the audit**: a live candidate for Featured/Expert, on
the strength of §4.4, Klaverjas and §8 rather than the F1 numbers, and worth
writing the submission comment to point the action editor there. That comment is
**not yet written** — deliberately, until after the API run, since the numbers it
should point at may move.

## Related external input

An Opus run flagged a methodological caveat about the paraphrase control, which
was folded into §6.3's decrement reporting. Two supplied verdict files
(`gpt56_paraphrase_verdicts1.md`, `opus5_paraphrase_verdicts.md`) informed the
alias arm.

Ground truth for Stratum D arrived as three author-supplied files
(`exact_leak_downstream.csv`, `exact_leakage_corpus.csv`,
`exact_ground_truth.md`) and is **re-verified row by row from the downloaded
CSVs on every run** rather than trusted — `stratum_d.py` refuses any rule that
does not hold on 100% of rows.
