# Glossary — terms used precisely

Words here mean something specific. Using them loosely is how the paper drifts.

**Feature-level target leakage.** A column whose value could not honestly have
been obtained at the prediction point. The object of this paper. Distinct from
train/test contamination, group leakage, benchmark contamination and external
leakage — all of which are procedural or evaluation-level and out of scope.

**Prediction point.** The moment the model is asked to answer. Leakage is a
property of the **triple (column, target, prediction point)**; the same column is
admissible under one prediction point and not another.

**Admissible / legitimate.** Kaufman et al.'s framing: a feature is legitimate if
it is available at the prediction point. The paper's central argument is that
availability and admissibility **come apart** — a column can be available and
still inadmissible, because the label was derived from it.

**REASON / CONSEQUENCE / TIMING / UPSTREAM.** The four mechanisms. The arrow
test: *REASON is about how the LABEL was made; CONSEQUENCE is about how the
COLUMN was made.*

**CONTESTED.** A positive that survives the precedence rule without landing in a
mechanism. Two of them exist.

**Stratum A / B / C / D.** Main (documentation-coded) / transfer (source names
the column, held out) / external validation (four other documentation cultures)
/ mechanically verified (a rule holds on every row). **Never pooled.**

**Tier-E3.** The evidence tier of the genuinely arguable positives — 22 of them.
The subtype robustness analysis reports a restricted result on exactly these,
because the rest carry a data check and are about as disputable as arithmetic.

**C1 / C6 / C9.** Primary condition (names + target) / + derivation criterion /
+ derivation criterion stated without reference to time. C1 and C6 carry the
claims; C9 shows the intervention is brittle.

**Matched cells.** A condition comparison made on the (dataset, shuffle) pairs
answered under **both** arms. Not "the same datasets" — the same shuffles.

**Complete roster.** A model with no missing cell. Mean-over-models aggregates
are computed over complete rosters only; per-model rows are not.

**Cell.** One (model, dataset, condition, seed, paraphrase-flag) answer. 1,812
cached; 1,308 in the scored real-name population; 462 paraphrase-arm.

**Quarantined cell.** A cell removed from the live cache and not yet
regenerated. Kept in `responses_truncated/` so §17 can name it. **A missing cell
is not a model that found nothing.**

**Frozen sieve.** The lexical instrument written *before* the sweep and never
edited afterwards. Editing it to catch its own misses would be fitting the
instrument to its answer.

**Anchoring.** Attaching a surviving sentence to a named column. The dominant
loss in the sweeps — only 17–30% of surviving sentences anchor, because listings
rarely expose a schema.

**Legitimate by default.** A column with no admissible record is coded
legitimate. This is why **precision is a lower bound**.

**Upper bound (of a baseline).** Every baseline threshold is swept on the
answers, so no deployment could reach the reported figure. Deliberate — an
untuned baseline is a strawman.

**B1 vs B1-tuned.** B1 applies the frozen §4.3 vocabulary to column names
(F1 0.174). B1-tuned adds 34 name patterns fitted to Stratum A (F1 0.394 on A,
**0.000 on B**, which is out-of-sample).

**Documented-but-inert.** A leak its own authors warn about that costs nothing
to remove. Klaverjas2018. The reason detection and downstream cost are reported
on separate axes.

**Triage.** The defensible product: put 48 of 306 columns (16%) in front of a
human reviewer, with that 16% containing all 40 documented leaks. Recall 1.000.

**Pin.** A regex over the manuscript plus a function recomputing the value from
`NUMBERS.txt`. A missing pattern is a **failure**, not a skip.

**`[N §x]`.** A citation to a section of `NUMBERS.txt`. Validated by
`claim_audit.py` since one pointed at a section that did not exist.

**†** on a table row. That row is computed from a model with non-randomly
missing cells (`gemini-3.5-flash`) and is not like-for-like with unmarked rows.
