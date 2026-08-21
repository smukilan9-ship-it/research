# References

Every work cited in `PAPER.md`, `PAPER_SHORT.md` or `APPENDIX.md`.

**Verification status.** Fifteen of the seventeen entries below were checked
against a retrieved source in a citation audit (`CITATION_CHECK_PROMPT.md` is
the prompt that produced it). Two — Quinlan and Sculley — were **not checked**
and are marked so rather than assumed. `verify_citations.py` checks that every
in-text citation resolves here and every entry is cited; it checks
correspondence, not correctness.

---

Bendinelli, T., Dox, A. & Holz, C. (2025). "Exploring LLM Agents for Cleaning
Tabular Machine Learning Datasets." *ICLR 2025 Workshop on Foundation Models in
the Wild.* arXiv:2503.06664. ✓ verified

**Bordt, S., Nori, H., Rodrigues, V., Nushi, B. & Caruana, R. (2024).
"Elephants Never Forget: Memorization and Learning of Tabular Data in Large
Language Models." *First Conference on Language Modeling (COLM 2024).*
arXiv:2404.06209.** DOI 10.48550/arXiv.2404.06209. ✓ verified

> Five authors in this order, confirmed. `arXiv:2403.06644` is a **different,
> earlier three-author paper** ("Testing Language Models for Memorization of
> Tabular Data") — do not cite it here. COLM issues no publisher DOI; use the
> arXiv DOI. Some indexes render the third author as "Vanessa Cristiny
> Rodrigues Vasconcelos". This is the citation a reviewer of §6.3 is most
> likely to check, because `tabmemcheck` is theirs.

Breck, E., Polyzotis, N., Roy, S., Whang, S. E. & Zinkevich, M. (2019). "Data
Validation for Machine Learning." *Proceedings of Machine Learning and Systems
1 (MLSys 2019).* ⚠ author order contested

> Two orders circulate. This form matches dblp and most citing papers; the
> official proceedings page lists Polyzotis, Zinkevich, Roy, Breck, Whang.
> Either is defensible — be consistent. Note the venue was SysML in 2018 and
> MLSys from 2019.

Hegselmann, S., Buendia, A., Lang, H., Agrawal, M., Jiang, X. & Sontag, D.
(2023). "TabLLM: Few-shot Classification of Tabular Data with Large Language
Models." *AISTATS 2023*, PMLR 206, 5549–5581. ✓ verified — six authors

Kapoor, S. & Narayanan, A. (2023). "Leakage and the reproducibility crisis in
machine-learning-based science." *Patterns* 4(9), 100804.
DOI 10.1016/j.patter.2023.100804. PMID 37720327. ✓ verified

> "Eight types" confirmed verbatim. **"17 fields, 294 papers" matches the
> published version**; the arXiv preprint (2207.07048) says 329, so a reviewer
> checking the preprint will see a different number. The L-prefix scheme is
> confirmed, but the **literal wording of the L2 label was not retrievable** —
> §3.2 quotes it as "model uses features that are not legitimate" and that
> string should be checked against Figure 1 of the published paper before
> submission.

Kapoor, S. et al. (2024). "REFORMS: Consensus-based Recommendations for
Machine-learning-based Science." *Science Advances* 10(18), eadk3452.
DOI 10.1126/sciadv.adk3452. PMID 38691601. ✓ verified

Kaufman, S., Rosset, S., Perlich, C. & Stitelman, O. (2012). "Leakage in Data
Mining: Formulation, Detection, and Avoidance." *ACM TKDD* 6(4), Article 15,
1–21. DOI 10.1145/2382577.2382579. ✓ verified

Larsen, K. R. & Becker, D. S. (**2021**). "Seven Types of Target Leakage in
Machine Learning and an Exercise." Chapter 24 of *Automated Machine Learning
for Business*, Oxford University Press. ISBN 9780190941666. ✓ verified

> **Year resolved: 2021.** The book is © Oxford University Press 2021
> (LCCN 2020049814). The 2019 in earlier notes traces to the authors' own
> ResearchGate preprint of ch. 24, whose running header carries an anticipated
> 2019 publication date that slipped. No second edition exists.

Narayan, A., Chami, I., Orr, L. & Ré, C. (2022). "Can Foundation Models Wrangle
Your Data?" *PVLDB* 16(4), 738–746. DOI 10.14778/3574245.3574258. ✓ verified

> The arXiv version (2205.09911) has **five** authors, adding Simran Arora.
> The four-author form above is correct for the PVLDB record.

Pushkarna, M., Zaldivar, A. & Kjartansson, O. (2022). "Data Cards: Purposeful
and Transparent Dataset Documentation for Responsible AI." *ACM FAccT 2022*,
1776–1826. DOI 10.1145/3531146.3533231. ✓ verified

Quinlan, J. R. (1993). *C4.5: Programs for Machine Learning.* Morgan Kaufmann.
ISBN 1-55860-238-0. ⚠ **NOT VERIFIED**

> Bibliographically uncontroversial but not checked against a source. Confirm
> against the Morgan Kaufmann/Elsevier record before submission.

Roberts, M. et al. (2021). "Common pitfalls and recommendations for using
machine learning to detect and prognosticate for COVID-19 using chest
radiographs and CT scans." *Nature Machine Intelligence* 3(3), 199–217.
DOI 10.1038/s42256-021-00307-0. ✓ verified

> ~50 authors with the AIX-COVNET collaboration; "et al." is the standard form.
> §3.2's prose was **corrected** against this: they identified 2,212 studies,
> included 415 after initial screening, and reviewed **61** in depth — it is
> those 61 of which none were of potential clinical use.

Rosset, S., Perlich, C., Świrszcz, G., Melville, P. & Liu, Y. (2010). "Medical
data mining: **insights** from winning two competitions." *Data Mining and
Knowledge Discovery* 20(3), 439–468. DOI 10.1007/s10618-009-0158-x. ✓ verified

> ⚠ Kaufman et al. (2012)'s own bibliography miscites this as "**Lessons** from
> winning two competitions". Cross-checking via Kaufman introduces the error.
> "Insights" is correct.

Schelter, S., Lange, D., Schmidt, P., Celikel, M., Biessmann, F. & Grafberger,
A. (2018). "Automating Large-Scale Data Quality Verification." *PVLDB* 11(12),
1781–1794. DOI 10.14778/3229863.3229867. ✓ verified

Sculley, D., Holt, G., Golovin, D., Davydov, E., Phillips, T., Ebner, D.,
Chaudhary, V., Young, M., Crespo, J.-F. & Dennison, D. (2015). "Hidden
Technical Debt in Machine Learning Systems." *NeurIPS 2015.* ⚠ **NOT VERIFIED**

> Plausible but unconfirmed. Check the ten-author order and page range against
> the NIPS 2015 proceedings before submission.

Varoquaux, G. & Cheplygina, V. (2022). "Machine learning for medical imaging:
methodological failures and recommendations for the future." *npj Digital
Medicine* 5, 48. DOI 10.1038/s41746-022-00592-y. PMID 35413988. ✓ verified

Whalen, S., Schreiber, J., Noble, W. S. & Pollard, K. S. (**2022**).
"Navigating the pitfalls of applying machine learning in genomics." *Nature
Reviews Genetics* 23(3), 169–181. PMID 34837041. ✓ verified

> **Year corrected: 2022, not 2021.** March 2022 issue; Epub ahead of print
> 26 Nov 2021. Semantic Scholar's "year 2021, volume 23" generates the
> confusion.
