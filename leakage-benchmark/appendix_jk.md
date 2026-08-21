## Appendix J. Larsen & Becker's seven types, mapped

Larsen and Becker (2021, ch. 24 of *Automated Machine Learning for Business*,
OUP) define target leakage expansively — a leak has occurred whenever "the model
performance metrics are better than what is possible in a real-world scenario
due to the inclusion of illegitimate features" — and note explicitly that this
"goes beyond the conventional description, which focuses only on features that
are not available at the time of prediction".

That conventional description is their type 1. It is the object of this paper.

| their type | their example | our treatment |
|---|---|---|
| **1. feature not available at prediction time** | blood-sugar level from the patient's *next* visit, in a 30-day readmission model | **the object of this paper.** §2.2's four mechanisms partition it by *why* the value is unavailable: REASON, CONSEQUENCE, TIMING, UPSTREAM |
| 2. evaluation cases precede training cases in time | exercise data where January resolutions leak backwards | procedural; §2.3 excludes it — it is a property of the split, not of a column |
| 3. feature available, but the case never occurs in deployment | patients who expired during the visit are never released, so never scored | deployment-population validity; the column is legitimate at the prediction point |
| 4. feature outside the model's use case | discharge-to-SNF rows removed, so a one-hot option never exists | problem framing |
| 5. feature interacts with target operationalisation | a 30-day readmission cutoff that gives some patients less time to return | measurement artefact in the target, not a feature–target relation |
| 6. target values obtained from outside sources | Titanic survivor lists looked up; the IJCNN 2011 Flickr challenge | *external leakage* in Kaufman et al.'s (2012) term; §2.3 excludes it |
| 7. subjects knew their own target status | surveying gym-goers about tomorrow's attendance | same-method bias |

Six of the seven concern the validity of an evaluation or a study design. Only
type 1 is a claim about a **column's relationship to a target at a stated
prediction point**, which is the only form an automated detector can act on from
documentation alone — and the form for which no annotated corpus existed.

Their chapter is pedagogical, with a hands-on exercise; it proposes no benchmark,
no evaluation and no detector, and it is not in competition with this work. It
does establish that the object was named and partitioned before us, which §2.2
now says.

---

## Appendix K. Kaggle datasets excluded as re-uploads

The Kaggle sweep excludes datasets detected as re-uploads of Stratum A/B, on the
ground that a hit on a re-hosted UCI table is the corpus finding itself rather
than an independent observation. At the complete sweep this is **61 sentences
across 41 datasets**.

Audited by hand against titles and attributions, the filter is **19/41 correct**
(≈48% precise, computed on the 40 present when the audit was run). It catches
verbatim re-uploads reliably — every dataset matching BANK on 12 or 13 of 13
columns is titled some variant of *"Bank Marketing"* — and mis-fires in two ways
that share a cause: a rule firing on a corpus table's **target name plus any two
columns** (SUPPORT2's target is `death`, so *US Death Rates* and *Global suicide
data* were excluded), and a **four-column overlap floor** that BANK's ordinary
English column names (`duration`, `month`, `day`, `previous`) clear by accident.
Both fail on exactly the corpus tables whose vocabulary is least distinctive.

The thresholds are **not retuned**. By the time the audit was run we knew which
datasets each threshold admits — including one we would have liked to keep — and
moving a threshold at that point is choosing a filter by its output. The rate is
reported instead, and the effect is that the "real and new" population is
**undercounted**, which makes §4.3's scarcity an underestimate rather than an
overestimate.

One bug was fixed, because it is not a threshold: the source-name test compared
by plain substring, so `compas` matched the word *"encompass"*. Correcting it to
a token-boundary comparison moved exactly three datasets and changed no other
number.

The full list follows, ordered by the corpus table each was attributed to.

| attributed to | Kaggle dataset | title |
|---|---|---|
| AI4I (5/6 column names present) | `abdulbasit551/predictive-maintenance-ai4i-2020-uci` | Predictive Maintenance AI4I 2020 UCI |
| BANK (12/13 column names present) | `aguado/telemarketing-jyb-dataset` | Telemarketing JYB Dataset - UCI |
| BANK (12/13 column names present) | `rashmiranu/banking-dataset-classification` | Banking Dataset Classification |
| BANK (12/13 column names present) | `henriqueyamahata/bank-marketing` | Bank Marketing |
| BANK (12/13 column names present) | `volodymyrgavrysh/bank-marketing-campaigns-dataset` | Bank marketing campaigns dataset | Opening Deposit |
| BANK (12/13 column names present) | `ruthgn/bank-marketing-data-set` | Bank Marketing Data Set |
| BANK (12/13 column names present) | `sahistapatel96/bankadditionalfullcsv` | bank-additional-full.csv |
| BANK (12/13 column names present) | `kidoen/bank-customers-data` | Bank Customers Data |
| BANK (12/13 column names present) | `aaditshukla/bank-marketing-dataset` | Bank Marketing Dataset  |
| BANK (12/13 column names present) | `soylevbeytullah/bank-marketing-shortly` | Bank Marketing Shortly |
| BANK (12/13 column names present) | `nasimetemadi/bank-marketing` | Bank marketing |
| BANK (12/13 column names present) | `singhakash/bank-marketing-dataset` | bank marketing dataset |
| BANK (12/13 column names present) | `muhammedabdelrasoul/bank-marketing` | Bank Marketing Campaign Dataset |
| BANK (13/13 column names present) | `dev523/ml-marathon-dataset-by-azure-developer-community` | ML Marathon Dataset by Azure Developer Community |
| BANK (13/13 column names present) | `arshmankhalid/bank-marketing-ml-ready-dataset` | Bank Marketing ML Ready Dataset |
| BANK (4/13 column names present) | `patricklford/covid-19` | COVID-19 & the virus that causes it: SARS-CoV-2. |
| BANK (4/13 column names present) | `lorentzyeung/price-paid-data-202304` | UK Property Price official data (Monthly Update) |
| BANK (4/13 column names present) | `marekk13/pkp-intercity-delays-dataset` | PKP Intercity delays dataset |
| CIRRHOSIS (target 'status' plus 2 column names present) | `kirbysasuke/covid-19` | COVID-19 Outcomes by Vaccination Status |
| CIRRHOSIS (target 'status' plus 2 column names present) | `mohamedelzeini/the-impacts-of-working-remotely-and-in-an-office` | The Impacts of Working Remotely and in an Office |
| CIRRHOSIS (target 'status' plus 2 column names present) | `thedevastator/a-quick-overview-of-clinical-trials` | Clinical Trials |
| CIRRHOSIS (target 'status' plus 2 column names present) | `tolgaozkul/data-league-26-no-show-dataset` | Data League '26 No-Show Prediction Dataset |
| CIRRHOSIS (target 'status' plus 2 column names present) | `rizwanash/covid-19-outcomes-by-vaccination-status` | COVID-19_Outcomes_by_Vaccination_Status |
| CIRRHOSIS (target 'status' plus 2 column names present) | `mansiaggarwal88/github-ai-repository-intelligence-dataset` | GitHub AI Repository Intelligence Dataset 2026 |
| CIRRHOSIS (target 'status' plus 4 column names present) | `gowtha69/mods-clinical-3c-50k` | MODS-Clinical-3C-50K |
| DIABETES (29/46 column names present) | `alirajaiebaharudin/diabetic-dataset-miniproject` | Readmission of diabetic patient, a case study |
| LC (target 'loan_status' plus 2 column names present) | `arunbhuta/credit-analysis-probability-of-default` | Credit Analysis :: Probability of Default |
| LC (target 'loan_status' plus 4 column names present) | `manishtripathi86/deloitte-hackathon-predict-the-loan-defaulter` | deloitte hackathon predict the loan defaulter |
| STUDENT (13/28 column names present) | `dillonmyrick/high-school-student-performance-and-demographics` | High School Student Performance & Demographics |
| STUDENT (16/28 column names present) | `arshmankhalid/student-data` | Secondary School Student Achievement Data |
| STUDENT (28/28 column names present) | `whenamancodes/student-performance` | Student Performance |
| STUDENT (source name 'student performance' present) | `larsen0966/student-performance-data-set` |  Student Performance Data Set |
| STUDENT (source name 'student performance' present) | `laveshjadon/ai-impact-on-students` | Impact of Ai on Students  |
| STUDENT (source name 'student performance' present) | `lightonphiri/a-multisource-dataset-for-cs1-failure-prediction` | A Multi‑Source Dataset for CS1 Failure Prediction |
| STUDENT (source name 'student performance' present) | `thedevastator/higher-education-predictors-of-student-retention` | Predict students' dropout and academic success |
| STUDENT (target 'g3' plus 3 column names present) | `tejas14/student-final-grade-prediction-multi-lin-reg` | Student Final Grade Prediction-Multi_lin_reg |
| SUPPORT2 (target 'death' plus 2 column names present) | `thedevastator/analysis-of-coronary-artery-disease-risk-factors` | Analysis of Coronary Artery Disease Risk Factors |
| SUPPORT2 (target 'death' plus 2 column names present) | `sathutr/global-suicide-data` | Global suicide data |
| SUPPORT2 (target 'death' plus 3 column names present) | `kylefengkfeng209/the-ethics-of-self-driving-cars-who-dies` | The Ethics of Self-Driving Cars: Who Dies? |
| SUPPORT2 (target 'death' plus 3 column names present) | `melissamonfared/death-rates-united-states` | Death Rates  |
| SUPPORT2 (target 'death' plus 3 column names present) | `thedevastator/identification-of-risk-factors-for-heart-disease` | Identification of Risk Factors for Heart Disease |
