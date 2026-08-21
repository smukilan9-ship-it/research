# References

Every work cited in `PAPER.md`, `PAPER_SHORT.md` or `APPENDIX.md`. Entries are
copied from the verified block in `RELATED_WORK.md`, which records what was
checked against the source and what was not.

`verify_citations.py` checks this file against the manuscripts in both
directions: every in-text citation must appear here, and every entry here must
be cited somewhere.

---

Bendinelli, T., Dox, A. & Holz, C. (2025). "Exploring LLM Agents for Cleaning
Tabular Machine Learning Datasets." *ICLR 2025 Workshop on Foundation Models in
the Wild.* arXiv:2503.06664.

**Bordt, S., Nori, H., Rodrigues, V., Nushi, B. & Caruana, R. (2024).
"Elephants Never Forget: Memorization and Learning of Tabular Data in Large
Language Models." *COLM 2024.* arXiv:2404.06209.**
Package: `github.com/interpretml/LLM-Tabular-Memorization-Checker`.

> ⚠️ **Two traps, both recorded in `RELATED_WORK.md` and both disarmed here.**
> (1) **Five authors, not three** — an earlier draft had "Bordt, Nori &
> Caruana", dropping Rodrigues and Nushi.
> (2) **Two papers share the title prefix.** `arXiv:2403.06644` is the earlier
> *"Testing Language Models for Memorization of Tabular Data"*;
> `arXiv:2404.06209` is the COLM paper and the one this work uses.
> This is the citation a reviewer of §6.3 is most likely to check, because it
> is the paper they would reach for to attack it: `tabmemcheck` is theirs, and
> every Stratum A table is a popular public tabular dataset.

Breck, E., Polyzotis, N., Roy, S., Whang, S. E. & Zinkevich, M. (2019). "Data
Validation for Machine Learning." *SysML 2019.*

Hegselmann, S., Buendia, A., Lang, H., Agrawal, M., Jiang, X. & Sontag, D.
(2023). "TabLLM: Few-shot Classification of Tabular Data with Large Language
Models." *AISTATS 2023*, PMLR 206, 5549–5581.

> ⚠️ **Six authors, not three.** `RELATED_WORK.md` flags an earlier
> "Hegselmann et al." given with three.

Kapoor, S. & Narayanan, A. (2023). "Leakage and the reproducibility crisis in
machine-learning-based science." *Patterns* 4(9), 100804. PMID 37720327.

Kaufman, S., Rosset, S., Perlich, C. & Stitelman, O. (2012). "Leakage in Data
Mining: Formulation, Detection, and Avoidance." *ACM TKDD* 6(4), 1–21.

Larsen, K. R. & Becker, D. S. (2021). "Seven Types of Target Leakage in Machine
Learning and an Exercise." Chapter 24 of *Automated Machine Learning for
Business*, Oxford University Press. ISBN 9780190941666.

> ⚠️ **YEAR UNRESOLVED — confirm before submission.** `RELATED_WORK.md` records
> **2019**; `PAPER.md`, `PAPER_SHORT.md` and `APPENDIX.md` all say **2021**.
> The manuscripts were written after the chapter was read (Appendix J quotes it
> verbatim), which favours 2021, but this has not been checked against the
> book. One lookup settles it.

Narayan, A., Chami, I., Orr, L. & Ré, C. (2022). "Can Foundation Models Wrangle
Your Data?" *PVLDB* 16(4), 738–746.

Pushkarna, M., Zaldivar, A. & Kjartansson, O. (2022). "Data Cards: Purposeful
and Transparent Dataset Documentation for Responsible AI." *ACM FAccT 2022.*

Quinlan, J. R. (1993). *C4.5: Programs for Machine Learning.* Morgan Kaufmann.

Roberts, M. et al. (2021). "Common pitfalls and recommendations for using
machine learning to detect and prognosticate for COVID-19 using chest
radiographs and CT scans." *Nature Machine Intelligence* 3, 199–217.

Rosset, S., Perlich, C., Świrszcz, G., Melville, P. & Liu, Y. (2010).
"Medical data mining: insights from winning two competitions." *Data Mining and
Knowledge Discovery* 20(3), 439–468.

Schelter, S., Lange, D., Schmidt, P., Celikel, M., Biessmann, F. & Grafberger,
A. (2018). "Automating Large-Scale Data Quality Verification." *PVLDB* 11(12),
1781–1794.

Sculley, D., Holt, G., Golovin, D., Davydov, E., Phillips, T., Ebner, D.,
Chaudhary, V., Young, M., Crespo, J.-F. & Dennison, D. (2015). "Hidden
Technical Debt in Machine Learning Systems." *NeurIPS 2015.*

Sharma, R. et al. (2014). **[INCOMPLETE — MUST BE COMPLETED BEFORE SUBMISSION]**

> ⚠️ Cited in Appendix J for *same-method bias*, and **verified nowhere in this
> repository** — it appears in `appendix_jk.md` and `APPENDIX.md` and in no
> reference list, `RELATED_WORK.md` entry, or verification note. Authors, title,
> venue and year are therefore unconfirmed, and are deliberately **not written
> out here rather than guessed**: a fabricated entry is worse than a missing
> one. Either complete it from the source or drop the parenthetical from
> Appendix J, which loses nothing — the row's claim stands without it.

Varoquaux, G. & Cheplygina, V. (2022). "Machine learning for medical imaging:
methodological failures and recommendations for the future." *npj Digital
Medicine* 5, 48.

Whalen, S., Schreiber, J., Noble, W. S. & Pollard, K. S. (2021). "Navigating
the pitfalls of applying machine learning in genomics." *Nature Reviews
Genetics* 23, 169–181.
