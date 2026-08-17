# Draft §3 — Related work

*Replaces the placeholder at `PAPER.md` line 167. Every citation is verified in
`RELATED_WORK.md` against a publisher or indexing record; the two entries that
are **identified but unread** are flagged there and are handled below in a way
that does not depend on their contents.*

*Nothing here has been applied to `PAPER.md`.*

---

## 3. Related work

### 3.1 The formulation, and what it left unbuilt

Leakage was given its modern formulation by Kaufman, Rosset, Perlich and
Stitelman (2012; KDD 2011), who defined it in terms of *legitimacy* — a feature
is legitimate if it is available at the prediction point — and proposed the
**learn–predict separation** as the avoidance discipline. The canonical examples
come from the same group's competition post-mortems (Rosset et al., 2010), where
a patient identifier carried the outcome of the KDD Cup 2008 task.

That work is about avoiding leakage in data you collected. This paper is about
detecting it in data somebody else published, and the two differ in what is
available to the practitioner: not the collection process, but a table and its
documentation. Kaufman et al. supply the definition we adopt in §2.1 and no
corpus against which a detector could be scored, because scoring one was not
their problem. **The missing evaluand is the gap this paper fills**: column-level
labels, each licensed by a quotation from the dataset's own source, with a
measured instrument on top.

### 3.2 Scale

Kapoor and Narayanan (2023) surveyed leakage across **17 scientific fields and
294 affected papers** and proposed a taxonomy of eight leakage types. Field-level
studies reach the same conclusion independently: Roberts et al. (2021) screened
2,212 COVID-19 imaging studies and found **none clinically usable**, with leakage
among the recurring causes; Varoquaux and Cheplygina (2022) and Whalen et al.
(2021) report the pattern in medical imaging and genomics.

Their eight types are a *survey* taxonomy spanning fields and failure modes. Our
five mechanisms (§2.2) are a *coding* taxonomy for a single one of theirs —
feature-level target leakage — cut for codability against a written source
rather than for coverage. §2.2 gives the mapping explicitly rather than leaving
a reader to construct it.

### 3.3 What existing tooling targets

Data-validation systems check schemas and distributions: TFX data validation
(Breck et al., 2019) and Deequ (Schelter et al., 2018) express constraints over
*values*. Neither expresses a constraint over a column's relationship to a
target, because that relationship is not a property of the data — a column of
integers is legitimate or not depending on when it was written down. Sculley et
al. (2015) name the surrounding condition, *data dependencies* and *undeclared
consumers*, without proposing a detector.

The most recent dedicated tooling makes the point sharpest. **LeakageDetector**
(arXiv:2503.14723; 2.0 at ICSME 2025, arXiv:2509.15971) is a static analyser for
notebook pipelines, and it detects exactly three things: **overlap,
preprocessing, and multi-test leakage**. All three are procedural — the leak is
in the code, and reading the code finds it. A feature-level target leak is
invisible to any analysis of the pipeline, because the pipeline is correct: the
column is split cleanly, scaled after the split, and used once. What is wrong is
what the column *means*, and that lives in the documentation, not the program.

We are not aware of an annotated, column-level corpus of target-leaking features
prior to this one, under any of six search phrasings (§3.5).

### 3.4 LLMs over tabular schemas, and the contamination risk

Language models have been applied to tabular tasks that are semantic rather than
statistical: data wrangling and integration (Narayan et al., 2022) and few-shot
classification from serialised rows (Hegselmann et al., 2023). Deciding whether
`boat` was recorded before or after a shipwreck is a task of the same kind — it
is answered from what the column name and its documentation *mean*, and not from
the values.

The direct threat to that reading is **Bordt et al. (2024)**, who show that
language models have memorised many popular tabular datasets verbatim, with
contamination concentrating in datasets with meaningful column names — precisely
our setting. We take this as a measurement problem rather than a rhetorical one
and run their released checker against four models on all fifteen of our tables
(§6.3), alongside a renaming control of our own. The results cut both ways and
we report both: **no model reproduced any of 675 data rows or any of 30
headers**, but column names are recalled substantially, up to 61% of the leaking
ones. A concurrent framework for tabular contamination (arXiv:2510.20351) is
identified but unread at the time of writing and is not relied on here.

### 3.5 Two qualifications we would rather state than have inferred

**The term is overloaded.** Most recent work labelled "leakage benchmark" —
AntiLeak-Bench, LessLeak-Bench, "Benchmarking Benchmark Leakage in LLMs"
(arXiv:2404.18824), Tab-MIA and others — concerns *benchmark contamination*,
training data leaking into evaluation sets. That is a different object, excluded
in §2.3, and it now dominates the search term. Our sense is the Kaufman one.

**Target leakage has been taxonomised before, and only one of its types is our
object.** Larsen and Becker (2019, ch. 24 of *Automated Machine Learning for
Business*, OUP) give **seven types of target leakage** under a deliberately
expansive definition — a target leak has occurred whenever "model performance
metrics are better than what is possible in a real-world scenario due to the
inclusion of illegitimate features", which they note "goes beyond the
conventional description, which focuses only on features that are not available
at the time of prediction".

That conventional description is their **type 1**, and it is the whole of what
this paper measures:

| their type | what it concerns | relation to this paper |
|---|---|---|
| **1. feature not available at prediction time** | a column's value does not exist yet | **our object.** §2.2's five mechanisms partition it by *why* |
| 2. evaluation set precedes training cases in time | validation protocol | procedural; excluded in §2.3 |
| 3. feature available but absent in the deployed population | who the model is run on | deployment validity, not the column–target relation |
| 4. feature outside the model's use case | problem framing | as above |
| 5. feature interacts with how the target was operationalised | target definition | measurement artefact |
| 6. target values obtained from outside sources | competition conduct | *external leakage* in Kaufman et al.'s term; excluded in §2.3 |
| 7. subjects knew their own target status | survey design | same-method bias |

So our five mechanisms **refine their type 1** rather than compete with their
seven. Theirs is a pedagogical chapter with an exercise, not a benchmark, an
evaluation or a detector; and their broader scope makes the point this paper
starts from — that the one type an automated detector can act on from
documentation alone is a single line in a list of seven, and it is the line
nobody has built an evaluand for. A full mapping is in Appendix F.

Two further papers are adjacent without overlapping. Bendinelli et al. (2025)
put LLM agents on tabular *cleaning* — sensor faults, entry errors, integration
mistakes — with no leakage ground truth. And "LLM-Guided Automated Feature
Engineering for Time Series Data with Temporal Leakage Control" (*AI* 7(7), 245)
couples LLMs to explicit temporal availability constraints, the closest published
analogue to our C2 condition; if it operationalises availability as our models
do, it is independent support for §9's claim that availability and admissibility
come apart.

---

## Notes for the author, not for the reader

1. **§3.5's second qualification is load-bearing and currently unverifiable.**
   It is written so that it is true whatever the seven types turn out to be, but
   a reviewer who owns the book will check the mapping. Obtaining the chapter is
   the single highest-value remaining literature task.
2. **Gebru et al. (2021) and Pushkarna et al. (2022) are deliberately not in
   §3.** They propose what documentation *should* contain; §4.4 measures what it
   *does* contain (406 complete-dictionary datasets, 23 flagged columns, 8 of 64
   known positives recovered). That is a direct empirical answer to their agenda
   and reads as a contribution where it sits in §4.4, and as a literature note
   if moved here. Recommend citing them in both places, with the paragraph in
   §4.4.
3. **The novelty claim is hedged to "we are not aware of".** Six queries is a
   sieve, and §4.3.2 is this paper's own demonstration of what sieves do. Before
   submission, re-run against Google Scholar and Semantic Scholar and walk the
   papers citing Kaufman et al. — a competing corpus would be hiding in that
   citation list.
4. Author-list and title corrections already applied here: Varoquaux &
   Cheplygina's title includes *"for the future"*; Bordt et al. is five authors
   and is arXiv:2404.06209 (COLM 2024), **not** arXiv:2403.06644; Hegselmann et
   al. is six authors; Sculley et al. is ten.
