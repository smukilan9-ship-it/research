# Harvesting protocol — label-derived column provenance

Version 0.1. Fix this before harvesting begins. Every later change goes in §10.

---

## 1. Scope and unit of analysis

**One record = one (dataset, column, source) triple.**

Not one per dataset, and not one per column. A column named as label-derived by
two different papers produces two records. This is deliberate: the disagreement
between sources is a measurement we intend to report, so it must survive in the
raw data rather than being collapsed at entry.

The **corpus** is the set of datasets. The **item** being classified downstream
is a column. The **evidence** is a record.

## 2. What we are labelling

A column is **label-derived** *with respect to a stated target and a stated
prediction point* when it could not have been recorded, or could not have taken
its observed value, at that prediction point because the target's outcome had
not yet occurred.

**Provenance is not a property of a column alone.** It is a property of
(column, target, prediction point). A dataset with several targets has several
answers for the same column: UCI 579 (Myocardial Infarction Complications)
carries twelve target columns, each a different complication, and a column
recording one of them may be a legitimate covariate for predicting another.

Every record therefore names both:

- `target` — the target column the judgment is made against. One record per
  (column, target) pair where a dataset has several.
- `prediction_point` — the moment a deployed model would be asked to predict,
  in the dataset's own vocabulary (e.g. "at admission", "at loan origination",
  "at screening"). Datasets have a temporal ladder, and a column can sit after
  one rung and before the next.

Where the documentation does not state a prediction point, record
`prediction_point: "UNSTATED"` and treat the dataset as **contested by
default** — the ambiguity is a property of the dataset, not of the coder.

Test to apply (Kaufman et al. 2012, availability criterion): *at the moment a
deployed model would need this column to make its prediction, does the value
exist?* If no, the column is label-derived.

Three sub-types, recorded separately because they behave differently:

| code | meaning | example |
|---|---|---|
| `REASON` | records why the outcome was assigned | `koi_fpflag_ss`, `r_charge_degree` |
| `CONSEQUENCE` | records something that happened because of the outcome | `recoveries`, `body` |
| `TIMING` | available only after the prediction point, no causal claim | `last_pymnt_d` |

`REASON` and `CONSEQUENCE` are the paper's subject. `TIMING` is recorded for
completeness and analysed separately — it is the type feature stores already
solve via point-in-time joins.

**Explicitly NOT label-derived**, however predictive: legitimately available
covariates, identifiers, and proxies for the outcome that were recorded before
it. A column being highly correlated with the target is *never* evidence.

## 3. Inclusion criteria (dataset level)

A dataset enters the corpus if **all** hold:

- **I1** Publicly downloadable without payment. A free click-through agreement
  is acceptable; the agreement is recorded.
- **I2** Tabular, with named columns. Anonymised column names (`V1`…`V27`)
  are excluded — provenance is unrecoverable in principle, so the dataset
  cannot carry ground truth.
- **I3** Has a defined prediction target used in published work.
- **I4** *(removed at v0.2 — see §10.)* Presence of a label-derived column is an
  **outcome**, not an inclusion criterion. Screening only datasets already known
  to leak would make the prevalence estimate circular and would enrich the
  evaluation set for leaks obvious enough to have been noticed. Datasets with
  zero positives remain in the corpus and are reported as zeros.
- **I5** Column names in the distributed file match the names in the evidence
  source, or a documented mapping exists.

### 3a. Sampling frame

Two frames, one screening pass.

**Frame A (prevalence).** The **N most-downloaded tabular classification
datasets** on a named registry, as of a fixed date, taken in rank order without
skipping. Rank, registry, date and retrieval query are recorded before
screening begins. Every dataset in Frame A that satisfies I1–I3 and I5 is
screened in full, whatever it turns out to contain.

**Frame B (detector evaluation).** The subset of Frame A with ≥1 positive.
Selection is by outcome here and that is legitimate: Frame B measures detector
performance on positives, never prevalence.

No dataset may enter the corpus outside Frame A. Datasets encountered
opportunistically (including any used while developing this protocol) are
recorded separately as a **convenience set**, reported apart from Frame A, and
excluded from every prevalence figure.

### 3b. Attrition reporting

Report the funnel: candidates considered, and the count excluded at each
criterion with the reason. Datasets excluded for lacking a retrievable
dictionary are reported as a finding in their own right — a benchmark whose
column semantics are undocumented cannot be provenance-audited by anyone.

## 4. Evidence standard — what licenses a label

A column may be labelled label-derived **only** on one of these, in descending
strength. Record which tier was used.

- **E1 — Official documentation states the timing.** The dataset's own
  dictionary, codebook, or archive page contains language placing the column at
  or after the outcome ("post charge off", "at discharge", "cause of death",
  "follow-up"). *Strongest: the dataset's authors labelled it.*
- **E2 — Official documentation warns against use.** The source explicitly says
  the column should be discarded for realistic prediction.
- **E3 — A peer-reviewed publication excludes it as leakage.** The paper names
  the column (or an unambiguous group) and states it was removed for
  leakage/availability reasons.
- **E4 — A preprint or competition rule does the same.** Recorded, but flagged
  as non-peer-reviewed and reported separately in any aggregate.

**Not acceptable as evidence:** our own judgment; high correlation or feature
importance; a blog post; another dataset's convention; an LLM's opinion.

The last one matters. The models under evaluation must never have contributed
to the ground truth they are scored against.

For every record, capture the **verbatim licensing phrase** (≤25 words) and its
locator. If no such phrase can be quoted, the record is not admissible.

## 5. Search strategy

Reproducible and pre-declared. For each candidate dataset:

1. Retrieve the official documentation page and any dictionary file.
2. Search the dictionary text for temporal markers:
   `post`, `after`, `following`, `at discharge`, `cause of death`, `outcome`,
   `final`, `resulted`, `recovery`, `follow-up`, `subsequent`, `closed`.
3. Retrieve up to **3** publications using the dataset, selected as the most
   cited among those with a stated feature-exclusion list. Record the query,
   the source searched, and the date.
4. Extract every column each source names as excluded-for-leakage.

Steps 2 and 4 are mechanical. Step 3 is the only place selection enters, which
is why the selection rule is fixed in advance and the query is logged.

## 6. Conflict adjudication

Sources will disagree. Resolution order, applied mechanically:

1. **E1/E2 beats E3/E4.** Official documentation outranks any paper.
2. Among papers of equal tier: if any names the column, it is recorded as
   **contested**, not resolved by majority.
3. **Contested columns are retained**, labelled `CONTESTED`, and excluded from
   the primary ground truth while forming the designated hard subset.

Never resolve a conflict by looking at the data. That would reintroduce
exactly the values-based reasoning the paper argues cannot recover provenance.

## 7. Record schema

One JSON object per record, one per line, in `records.jsonl`.

```
dataset_id        stable slug, e.g. "lending_club_2007_2011"
dataset_url       where the file was obtained
column            column name exactly as distributed
target            the target column this judgment is made against
prediction_point  when a deployed model would predict, or UNSTATED
label             LABEL_DERIVED | LEGITIMATE | CONTESTED
subtype           REASON | CONSEQUENCE | TIMING | null
evidence_tier     E1 | E2 | E3 | E4
source_type       DOCUMENTATION | PEER_REVIEWED | PREPRINT | COMPETITION
source_citation   full citation or URL
source_locator    page/section/table, or dictionary row
quote             verbatim licensing phrase, <= 25 words
coder             initials
date              ISO date
notes             free text, optional
```

Negative labels (`LEGITIMATE`) are **not** individually evidenced. Every column
of an included dataset that no source names is legitimate by default, and this
default is stated as a limitation: it makes recall on the positive class the
meaningful metric and precision partly a function of harvest completeness.

## 8. Reliability

- A random **20%** of datasets are independently coded by a second coder who
  has not seen the first coder's records.
- Report Cohen's κ on the column-level binary label.
- Report inter-**source** agreement separately — this is a finding, not a
  quality check: it measures whether the field agrees about provenance.
- κ below 0.6 on coder agreement halts harvesting until the criteria are
  revised, and the revision is logged in §10.

### 8a. Comparability of silence

Every source is recorded with a **scope**:

- `FULL_COLUMN_SET` — the source addresses every column (a data dictionary).
  Its silence about a column is informative: it means *not label-derived*.
- `EXCLUSION_LIST_ONLY` — the source names only what it removed (a paper's
  methods section). Its silence is **uninformative**: the column may be
  legitimate, unused, or unconsidered.

Agreement is computed **only between sources of equal scope**. Comparing a
dictionary against an exclusion list scores two different questions as though
they were one, and produces a κ that looks like disagreement but is an artifact
of the closed-world assumption holding for one source and not the other.

Cross-scope pairs are recorded and reported as skipped, with the count. A
dataset needs two same-scope sources before it contributes to the inter-source
agreement finding, and the number of datasets meeting that bar is reported.

## 9. Stopping rule

Declared in advance: harvest until **50 datasets** satisfy §3, or until the
candidate pool from §5 is exhausted, whichever comes first. If the target is
not reached, report the number reached and the reason. Do not extend the search
strategy to reach the number.

## 10. Deviations log

Every departure from this document, with date and reason. Empty at v0.1.

| date | clause | change | reason |
|---|---|---|---|
| 2026-08-12 | §8a added | agreement computed only between sources of equal scope | pilot produced κ = −0.667 between a data dictionary and a paper's exclusion list. Arithmetically correct, meaningless: a dictionary's silence means "not label-derived", a paper's silence may mean unused or unconsidered. |
| 2026-08-12 | §3 I4 removed; §3a, §3b added | presence of a positive is an outcome, not an inclusion criterion; sampling frame and attrition reporting specified | screening only datasets known to leak makes prevalence circular and enriches the evaluation set for easily-noticed leaks. |
| 2026-08-12 | §5 note | "collection", "ever", "to date" flagged as ambiguous markers | pilot on Lending Club: 3 of 10 sieve hits were prior-history columns (`collections_12_mths_ex_med`, `tot_coll_amt`, `num_accts_ever_120_pd`) available at application time. |
| 2026-08-12 | §2, §7 | provenance redefined as a property of (column, target, prediction point); `target` and `prediction_point` added to the record schema | UCI 579 has twelve target columns. A column recording one complication may be a legitimate covariate for another, so no target-free judgment exists. The same dataset has a temporal ladder (admission -> treatment -> complication), so the prediction point must be stated too. All records written before this amendment are target-implicit and must be re-stamped. |
| 2026-08-12 | §3a expansion | Kaggle rejected as a corpus source | 0 of the 60 top-voted CSV datasets expose any column schema, so no column can meet the §4 evidence standard. Kaggle datasets may well contain more label-derived fields than UCI's; none can be *evidenced*. |
| 2026-08-12 | §2 | subtype split to be tracked from dataset 1 | pilot yielded 5 TIMING vs 2 CONSEQUENCE on Lending Club. Only REASON/CONSEQUENCE are the primary subject, so effective corpus size may be ~1/3 of the raw positive count. |
