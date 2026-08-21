I need every entry in a paper's reference list verified against the actual
published sources. This is for a TMLR submission, so an incorrect citation is a
real cost. Please use web search and check each one.

For EACH entry below, tell me:
  - CORRECT, or what specifically is wrong (authors, year, title, venue, IDs)
  - the full correct citation if anything is wrong
  - your confidence, and the URL you verified it against

Do NOT guess. If you cannot verify an entry, say "UNVERIFIED" and say what you
searched. An invented correction is worse than an unresolved one.

THREE ENTRIES MATTER MOST — check these first and most carefully:

1. **Larsen, K. R. & Becker, D. S. "Seven Types of Target Leakage in Machine
   Learning and an Exercise." Chapter 24 of *Automated Machine Learning for
   Business*, Oxford University Press. ISBN 9780190941666.**
   → The YEAR IS DISPUTED in my own notes: one source says 2019, three say
     2021. Which is right for the book and for this chapter? If the book had
     multiple editions or an online-first chapter, tell me that too.

2. **Sharma, R. et al. (2014)** — cited for "same-method bias" / common-method
   variance.
   → I have NO other details. Does a 2014 paper by a Sharma on same-method or
     common-method bias exist and is it the standard citation for this? If the
     standard citation is someone else entirely (e.g. Podsakoff et al.), say
     so — I would rather drop the parenthetical than cite the wrong thing.

3. **Bordt, S., Nori, H., Rodrigues, V., Nushi, B. & Caruana, R. (2024).
   "Elephants Never Forget: Memorization and Learning of Tabular Data in Large
   Language Models." COLM 2024. arXiv:2404.06209.**
   → Confirm the author list is exactly these FIVE, in this order, and that
     arXiv:2404.06209 is the COLM paper — NOT arXiv:2403.06644, which is a
     different, earlier paper ("Testing Language Models for Memorization of
     Tabular Data"). Confirm the COLM 2024 venue and whether there is a DOI.

THE REST, in the same format:

4. Bendinelli, T., Dox, A. & Holz, C. (2025). "Exploring LLM Agents for
   Cleaning Tabular Machine Learning Datasets." ICLR 2025 Workshop on
   Foundation Models in the Wild. arXiv:2503.06664.
5. Breck, E., Polyzotis, N., Roy, S., Whang, S. E. & Zinkevich, M. (2019).
   "Data Validation for Machine Learning." SysML 2019.
6. Hegselmann, S., Buendia, A., Lang, H., Agrawal, M., Jiang, X. & Sontag, D.
   (2023). "TabLLM: Few-shot Classification of Tabular Data with Large Language
   Models." AISTATS 2023, PMLR 206, 5549–5581.
   → Confirm SIX authors; an earlier draft of mine had three.
7. Kapoor, S. & Narayanan, A. (2023). "Leakage and the reproducibility crisis in
   machine-learning-based science." Patterns 4(9), 100804. PMID 37720327.
   → Also confirm: is their taxonomy EIGHT types, and is the "model uses
     features that are not legitimate" category labelled L2?
8. Kaufman, S., Rosset, S., Perlich, C. & Stitelman, O. (2012). "Leakage in
   Data Mining: Formulation, Detection, and Avoidance." ACM TKDD 6(4), 1–21.
9. Narayan, A., Chami, I., Orr, L. & Ré, C. (2022). "Can Foundation Models
   Wrangle Your Data?" PVLDB 16(4), 738–746.
10. Pushkarna, M., Zaldivar, A. & Kjartansson, O. (2022). "Data Cards:
    Purposeful and Transparent Dataset Documentation for Responsible AI."
    ACM FAccT 2022.
11. Quinlan, J. R. (1993). C4.5: Programs for Machine Learning. Morgan Kaufmann.
12. Roberts, M. et al. (2021). "Common pitfalls and recommendations for using
    machine learning to detect and prognosticate for COVID-19 using chest
    radiographs and CT scans." Nature Machine Intelligence 3, 199–217.
    → Give me the full author list or the standard "et al." form for NMI.
13. Rosset, S., Perlich, C., Świrszcz, G., Melville, P. & Liu, Y. (2010).
    "Medical data mining: insights from winning two competitions." Data Mining
    and Knowledge Discovery 20(3), 439–468.
14. Schelter, S., Lange, D., Schmidt, P., Celikel, M., Biessmann, F. &
    Grafberger, A. (2018). "Automating Large-Scale Data Quality Verification."
    PVLDB 11(12), 1781–1794.
15. Sculley, D., Holt, G., Golovin, D., Davydov, E., Phillips, T., Ebner, D.,
    Chaudhary, V., Young, M., Crespo, J.-F. & Dennison, D. (2015). "Hidden
    Technical Debt in Machine Learning Systems." NeurIPS 2015.
16. Varoquaux, G. & Cheplygina, V. (2022). "Machine learning for medical
    imaging: methodological failures and recommendations for the future."
    npj Digital Medicine 5, 48.
17. Whalen, S., Schreiber, J., Noble, W. S. & Pollard, K. S. (2021).
    "Navigating the pitfalls of applying machine learning in genomics."
    Nature Reviews Genetics 23, 169–181.
    → Note the year/volume look inconsistent (2021 vs volume 23, which is
      2022). Which is right?

Finally: are there any WELL-KNOWN papers on **feature-level target leakage** —
a column whose value encodes the outcome it is used to predict, as distinct
from train/test contamination — that a reviewer would expect to see cited and
that is missing from this list? I care specifically about prior TAXONOMIES of
target leakage. Name them with citations; say "none found" if none.
