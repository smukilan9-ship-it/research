# Decisions and their reasons — including the reversed ones

Recorded so nobody re-litigates a settled question, and so the reversals are
visible rather than buried.

## Scope and framing

**TMLR, not a top conference.** TMLR's criteria are *claims supported by
evidence* and *of interest to some audience*. This paper's contribution is an
evaluand plus careful negatives — exactly what that bar rewards and what a
novelty bar would punish.

**The P1–P9 "registered prediction" framing was cut.** They were the assistant's
predictions, not the author's, and a prediction nobody committed to in advance
is decoration. The scarcity result stayed; the framing went.

**SURROGATE was withdrawn as a mechanism.** The §4.4 audit found it could not
survive its own evidence. Withdrawing the category was chosen over defending a
label the sources do not license.

**Four mechanisms, cut for codability rather than coverage.** A taxonomy that
cannot be applied against a written source is not usable by a second coder.

## Inter-coder reliability — the reversal worth reading

The question was raised as "why do we need a second coder — where are we even
using κ?" The answer went in two stages, and the second corrected the first.

1. **First answer, conceded:** κ appears nowhere in the paper, so it was not
   load-bearing for the binary labels.
2. **Self-correction:** that was right about the binary labels and **wrong about
   the subtypes**. §6.2 — the definitional finding, the paper's most interesting
   result — rests entirely on the subtype partition, which is one coder's
   reading.

**Resolution: no κ.** Three raters was rejected as genuinely tedious without the
column-name explanations an LLM could give. Instead:

- **§21, adversarial perturbation.** Relabel a fraction of REASON/CONSEQUENCE
  positives, randomly and adversarially, and measure whether the finding
  survives. Reported **mixed and as such**: 3 adversarial flips cut the lift
  margin from 21.8 to 2.4, but the picks are KOI's `koi_fpflag_*`; restricted to
  the 22 tier-E3 positives — the only genuinely arguable ones — the margin holds
  at **+7.2 with half of them overturned**. The *direction* is not an artefact
  of the coding; the *magnitude* should not be read to a decimal.
- **Stratum D.** Positives where a rule reconstructs the target on every row.
  Agreement 1.000, no threshold, no quotation to read. For these records
  reliability is not merely unnecessary but **undefined** — a second coder cannot
  disagree with a crosstab.

A blind coding packet (`coding_packet.py`, `coding_html.py`, `coding_score.py`)
was built and **deliberately not run**. The HTML version is kept because it
works and may be wanted if a referee insists.

## Validation sources considered and declined

- **Water-leakage literature and KIOS LeakDB.** Different object entirely —
  water escaping from pipes. Declined.
- **Building our own 25 datasets.** Declined: labels we author ourselves are not
  independent evidence, and the whole point of the protocol is that a *written
  source* licenses each positive.
- **NASA / government datasets.** Partially adopted — the KOI cumulative table
  is in Stratum A — but they do not solve the problem, because the scarcity of
  *documented* leakage is a property of documentation, not of data providers.

## Manuscript decisions

**Two manuscripts, one source of truth.** `PAPER_SHORT.md` (11 body pages) is
the submission; `PAPER.md` (30) is kept so anything cut can be pulled back. The
short version preserves §1–10 numbering so cross-references survive.

**12 pages, not 20 or 30.** Two proposals of 30 and then 20 were corrected by
the author, twice. A 42-page main body is a review-latency risk more than an
acceptance risk, and reviewers are volunteers.

**Page count is measured, not estimated.** `pagecount.py` renders at TMLR-ish
geometry and asks a layout engine where pages fall. Two words-per-page estimates
of the same file had differed by three pages and neither was checkable.

**`gemini-3.5-flash` keeps its per-model rows, with a †, and is excluded from
every mean-over-models aggregate.** A per-model row is a per-model claim and is
honest about its own cells; a mean treats each row as one comparable unit, and a
row missing cells non-randomly is not one. Dropping the model outright was the
alternative and was rejected as discarding real data; see `05_OPEN_WORK.md` for
when to revisit.

**STEEL kept and disclosed; MI excluded; ChessFraud left uncoded.** All three
follow one principle — *a column that is itself an outcome is not a feature* —
and the STEEL exception is justified by the practitioner scenario being real.

## Reporting decisions

**Baselines are tuned on the answers.** An untuned baseline is a strawman.
Everything is therefore an upper bound, stated as such. `B1-tuned` was added for
exactly this reason: `B1` (the frozen sieve vocabulary) is too weak to be a fair
test of "could a keyword rule do this?"

**Detection and downstream cost are reported on separate axes and never
combined.** Klaverjas is why: a dataset can sit at the top of one and the bottom
of the other, and a single quality score would collapse three distinct
properties.

**Precision is a lower bound**, because a column with no admissible record is
coded legitimate, so a model flagging something real but undocumented is scored
wrong.

**Uncertainty resamples datasets, not columns.** Columns are not independent
draws — CRIME contributes 144 of them and 17 positives, nine resting on one
sentence.
