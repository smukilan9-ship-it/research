# §3 Related work — verified citation list and positioning

*Every entry below was checked against a publisher or indexing record on
2026-08-15. Where I could not reach the source itself, the entry says so. The
notes marked **POSITION** are what the paragraph has to do, not filler.*

---

## 1. The formulation

**Kaufman, S., Rosset, S., Perlich, C. & Stitelman, O. (2012). "Leakage in Data
Mining: Formulation, Detection, and Avoidance." *ACM Transactions on Knowledge
Discovery from Data* 6(4), Article 15.** DOI `10.1145/2382577.2382579`.
Earlier version: KDD 2011.

Verified. Contributes the legitimacy formulation, the *learn–predict
separation*, and detection methods for the case where the modeller did not
control collection.

> **POSITION.** They formulated the problem and proposed avoidance by
> construction. They offer no annotated corpus, because the paper is about
> avoiding leakage in data you own, not detecting it in data someone else
> published. Your contribution is the missing evaluand: a corpus with
> source-licensed column-level labels, and a measured instrument on it. Say
> this in two sentences and do not overclaim beyond it.

**Rosset, S., Perlich, C., Świrszcz, G., Melville, P. & Liu, Y. (2010).
"Medical data mining: insights from winning two competitions." *Data Mining and
Knowledge Discovery* 20(3), 439–468.** DOI `10.1007/s10618-009-0158-x`.

Verified. KDD Cup 2008 + INFORMS 2008. One of its three stated topics is
information leakage and its effect on competitions. The origin of the canonical
patient-identifier story.

---

## 2. Scale and the reproducibility argument

**Kapoor, S. & Narayanan, A. (2023). "Leakage and the reproducibility crisis in
machine-learning-based science." *Patterns* 4(9), 100804.**
PMID `37720327`. Published 8 September 2023.

Verified, including the numbers you cite: **17 fields, 294 affected papers, a
taxonomy of eight leakage types.**

> **POSITION.** Their eight types are a *survey* taxonomy across fields; your
> five mechanisms are a *coding* taxonomy for one type of theirs. Build the
> mapping explicitly in §2.2 — a reviewer who knows this paper will construct
> it themselves otherwise, and you want to control that comparison.

**Roberts, M. et al. (2021). "Common pitfalls and recommendations for using
machine learning to detect and prognosticate for COVID-19 using chest
radiographs and CT scans." *Nature Machine Intelligence* 3, 199–217.**
arXiv:2008.06388.

Verified. 2,212 studies screened, 61 in the final analysis, none clinically
usable. Good for §1's stakes.

**Varoquaux, G. & Cheplygina, V. (2022). "Machine learning for medical imaging:
methodological failures and recommendations **for the future**." *npj Digital
Medicine* 5, 48.** DOI `10.1038/s41746-022-00592-y`.

Verified. ⚠️ **Title correction** — I previously gave it without *"for the
future"*. The full title is required.

**Whalen, S., Schreiber, J., Noble, W. S. & Pollard, K. S. "Navigating the
pitfalls of applying machine learning in genomics." *Nature Reviews Genetics*.**
PMID `34837041`.

Verified. ⚠️ **Year correction** — published online November 2021; the print
issue is 2022. Check which your style guide wants; the online-first date is
2021, not 2022 as I first said.

---

## 3. What existing tooling actually targets

*This is the section that earns your claim that no tool does what you measure.*

**Breck, E., Polyzotis, N., Roy, S., Whang, S. E. & Zinkevich, M. (2019). "Data
Validation for Machine Learning." *Proceedings of MLSys (SysML) 2019*.**

Verified. Google's TFX data validation. Schema and distribution checks — not
target-relative provenance.

**Schelter, S., Lange, D., Schmidt, P., Celikel, M., Biessmann, F. &
Grafberger, A. (2018). "Automating large-scale data quality verification."
*PVLDB* 11(12), 1781–1794.** DOI `10.14778/3229863.3229867`. (Deequ.)

Verified. "Unit tests for data" — constraints on values, not on a column's
relationship to a target.

**Sculley, D. et al. (2015). "Hidden Technical Debt in Machine Learning
Systems." *NIPS 2015*, 2503–2511.**

Verified. Full author list: Sculley, Holt, Golovin, Davydov, Phillips, Ebner,
Chaudhary, Young, Crespo, Dennison. Cite for *data dependencies* and
*undeclared consumers*.

**🆕 LeakageDetector (2025).** Two papers I did not previously give you, and
you need them:
- **arXiv:2503.14723**, "LeakageDetector: An Open Source Data Leakage Analysis
  Tool in Machine Learning Pipelines."
- **arXiv:2509.15971**, "LeakageDetector 2.0: Analyzing Data Leakage in
  Jupyter-Driven ML Pipelines," ICSME 2025 Tool Demonstration track.

Verified. Static analysis of notebook code. It detects exactly three things:
**Overlap, Preprocessing, and Multi-test** leakage.

> **POSITION.** This is the strongest single piece of support for your framing
> and you were about to submit without it. The most recent dedicated leakage
> tool in the literature detects three procedural failures by reading *code*,
> and cannot detect a feature-level target leak at all, because the leak is not
> in the code — it is in what the column means. One sentence citing this does
> more for §1 than a paragraph of argument.

---

## 4. LLMs over tabular schemas

**Narayan, A., Chami, I., Orr, L. & Ré, C. (2022). "Can Foundation Models
Wrangle Your Data?" *PVLDB* 16(4), 738–746.** DOI `10.14778/3574245.3574258`.
arXiv:2205.09911.

Verified. Five data cleaning/integration tasks cast as prompting.

**Hegselmann, S., Buendia, A., Lang, H., Agrawal, M., Jiang, X. & Sontag, D.
(2023). "TabLLM: Few-shot Classification of Tabular Data with Large Language
Models." *AISTATS 2023*, PMLR 206, 5549–5581.**

Verified. ⚠️ Cite the full author list — it is six people, not "Hegselmann
et al." with three.

**Bordt, S., Nori, H., Rodrigues, V., Nushi, B. & Caruana, R. (2024).
"Elephants Never Forget: Memorization and Learning of Tabular Data in Large
Language Models." *COLM 2024*.** arXiv:2404.06209. Package:
`github.com/interpretml/LLM-Tabular-Memorization-Checker`.

Verified. ⚠️ **Author correction** — I gave you "Bordt, Nori & Caruana"; it is
five authors including Rodrigues and Nushi. Also note there are **two** papers
with this title prefix: arXiv:2403.06644 is the earlier *"Testing Language
Models for Memorization of Tabular Data"*; arXiv:2404.06209 is the COLM paper.
Cite the right one.

> **POSITION and RISK.** They find LLMs have memorised many popular tabular
> datasets **verbatim**. Every dataset in your Stratum A is a popular public
> tabular dataset. This is the paper a reviewer will use to attack §6.3, and
> your paraphrase control is a weaker instrument than their released tester.
> Read it before you finalise §6.3, and consider running their checker on your
> twelve — a negative result there is worth more than the paraphrase argument,
> and a positive one you need to know about before a reviewer tells you.

**🆕 "When Large Language Models Know the Table: A Framework for Assessing Data
Contamination in Tabular Datasets."** arXiv:2510.20351.

Found during the search, not verified beyond its abstract listing. Directly on
tabular contamination. Check it for the same reason as above.

---

## 5. Documentation standards

**Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W., Wallach, H.,
Daumé III, H. & Crawford, K. (2021). "Datasheets for Datasets." *CACM* 64(12),
86–92.** DOI `10.1145/3458723`. 57 questions in 7 categories.

Verified.

**Pushkarna, M., Zaldivar, A. & Kjartansson, O. (2022). "Data Cards: Purposeful
and Transparent Dataset Documentation for Responsible AI." *FAccT '22*.**
DOI `10.1145/3531146.3533231`. arXiv:2204.01075.

Verified.

> **POSITION.** These propose what documentation *should* contain. Your §4.4 is
> a measurement of what it currently does contain: 406 complete-dictionary
> datasets, 23 flagged columns, 8 of 64 known positives recovered. That is a
> real empirical contribution to their agenda — neither paper asks whether a
> complete datasheet would let you find a leaking column, and you answer it.
> This is the most under-used citation in your list; give it a paragraph, not
> a parenthesis.

---

## 6. ⚠️ The one you must obtain before submitting

**Larsen, K. R. & Becker, D. S. (2019). "Seven Types of Target Leakage in
Machine Learning and an Exercise," Chapter 24 of *Automated Machine Learning
for Business*, Oxford University Press.** ISBN 9780190941666.

**A seven-type taxonomy of *target* leakage specifically — the exact object
your five mechanisms partition.** I could not read it: the preprint is on
ResearchGate and the network here blocks that host, as it blocks Wikipedia and
arXiv full text. So I have the existence and the framing, and not the seven
types.

> **This is the single largest positioning risk in the paper.** It is a
> textbook chapter, pedagogical, with an exercise — no benchmark, no evaluation,
> no detector — so your contribution stands. But "we propose a five-mechanism
> taxonomy of feature-level target leakage" cannot be written as though nobody
> has taxonomised target leakage before. Get the chapter, map their seven onto
> your five, and put the mapping in an appendix. If their seven are a superset,
> say so and explain why yours is cut for *codability against a source* rather
> than for teaching. That is a defensible answer; silence is not.

---

## Novelty check: does a benchmark like yours already exist?

I searched for one under six phrasings. **The claim survives, with a
qualification you should write into the paper rather than leave implicit.**

Everything the current literature calls a "leakage benchmark" is
**benchmark contamination** — training data leaking into evaluation sets.
AntiLeak-Bench, LessLeak-Bench (83 software-engineering benchmarks),
"Benchmarking Benchmark Leakage in LLMs" (arXiv:2404.18824), SrDetection,
AgentLeak, Tab-MIA. Different sense of the word, and §2.3 already excludes it —
but the collision is now dense enough that a reader searching the term will hit
those first. **Say in §1 that the term is overloaded and which sense you mean,
before you say anything else.**

Nearest genuinely adjacent work found:

- **Bendinelli, T. et al. (2025). "Exploring LLM Agents for Cleaning Tabular
  Machine Learning Datasets." ICLR 2025 Workshop on Foundation Models in the
  Wild.** arXiv:2503.06664. LLM + Python cleaning training data to improve
  downstream performance. Concerns sensor faults, entry errors and integration
  mistakes — *data errors*, not target-relative provenance — and has no
  leakage ground truth. Cite it; it does not scoop you, and it makes your
  downstream arms look better designed by contrast.
- **"LLM-Guided Automated Feature Engineering for Time Series Data with
  Temporal Leakage Control."** *AI* 7(7), 245. DOI `10.3390/ai7070245`. LLMs
  plus explicit temporal availability constraints. The closest thing to your
  C2 condition in print. Worth reading: if they operationalise availability the
  way your models do, that is independent support for §9's central claim that
  availability ≠ admissibility.

No annotated column-level corpus of target-leaking features turned up under any
phrasing.

---

## Honest limits of this check

- **ResearchGate, Wikipedia, arXiv full text and one blog are blocked by this
  environment's egress proxy.** Entries verified through publisher pages, DBLP,
  ACM DL, PMLR, PubMed and search-result metadata are solid; the Larsen chapter
  and arXiv:2510.20351 are *identified but unread*, and are marked so above.
- A literature search is a sieve, and §4.3.2 is this paper's own demonstration
  of what sieves do. Absence of a competing benchmark in six queries is
  evidence, not proof. Before submitting, run the same search once more against
  Google Scholar and Semantic Scholar directly, and check the papers that cite
  Kaufman et al. — that citation list is the highest-yield place a competitor
  would be hiding.
