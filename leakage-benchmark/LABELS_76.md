# The 76 labels that took a decision

604 columns are labelled across Strata A and B. 536 of them are
scored legitimate by default (§4.6): no source statement, no
judgement call, and precision is reported as a lower bound because
of it. The remaining 76 each rest on a quotation.

For each: does this quotation license this label? The protocol is
*code the evidence, not the intuition* -- a sentence that reports
only WHEN a value was recorded is TIMING, even where something
deeper seems to be going on.

- **8 withdrawn** by the §4.7 audit, listed first
- **68 leaks**, weakest evidence tier first
- tiers among the leaks: E1 34, E2 6, E3 28


## Withdrawn by the §4.7 audit (8)

Each was a leak in the corpus and is not one now, because its own documentation places the value at or before the prediction point. Disagreeing with a removal changes a corpus count.

### SUPPORT2 · `prg2m`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: physician scores

### SUPPORT2 · `prg6m`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: physician scores

### SUPPORT2 · `surv2m`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: model predictions

### SUPPORT2 · `surv6m`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: model predictions

### SUPPORT2 · `sps`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: composite scores

### SUPPORT2 · `aps`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: composite scores

### STUDENT · `G1`

> Important note: the target attribute G3 has a strong correlation with attributes G2 and G1. This occurs because G3 is the final year grade (issued at the 3rd period), while G1 and G2 correspond to the 1st and 2nd period grades. It is more difficult to predict G3 without G2 and G1, but such prediction is much more useful

- label **LABEL_DERIVED**, mechanism **SURROGATE**, tier **E1**
- target: `G3`
- source: UCI ML Repository 320, Student Performance, dataset summary

### STUDENT · `G2`

> Important note: the target attribute G3 has a strong correlation with attributes G2 and G1. This occurs because G3 is the final year grade (issued at the 3rd period), while G1 and G2 correspond to the 1st and 2nd period grades. It is more difficult to predict G3 without G2 and G1, but such prediction is much more useful

- label **LABEL_DERIVED**, mechanism **SURROGATE**, tier **E1**
- target: `G3`
- source: UCI ML Repository 320, Student Performance, dataset summary


## Leaks at tier E3 (28) — weakest evidence

§6.2's adversarial analysis treats these as the arguable ones and shows the lift margin survives half of them being overturned. If a reader disagrees anywhere, it is most likely here.

### BONEMARROW · `ANCrecovery`

> - Time taken for neutrophil recovery, defined as > 0.5 x 109/L

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: badawy2025
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### BONEMARROW · `PLTrecovery`

> - Time taken for platelet recovery, defined as > 50000/mm3

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: badawy2025
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### BONEMARROW · `aGvHDIIIIV`

> - Development of acute graft versus host disease stage III or IV

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: badawy2025
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### BONEMARROW · `survival_time`

> - Observation period (if alive) or time to event (if dead), in days

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: badawy2025
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### BONEMARROW · `time_to_aGvHD_III_IV`

> - Duration until development of acute graft versus host disease stage III or IV

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: badawy2025
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### COMPAS · `r_charge_degree`

> (no quotation on this record)

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `is_recid`
- source: ProPublica compas-analysis, compas-scores-two-years field list
- note: The r_ prefix marks the degree of the charge in the recidivism event; the field exists because the event happened. Quotation unavailable: the ProPublica repository README was not retrievable from this environment, so this rests on the field naming and the data

### COMPAS · `r_charge_desc`

> (no quotation on this record)

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `is_recid`
- source: ProPublica compas-analysis, compas-scores-two-years field list
- note: The r_ prefix marks the description of the charge in the recidivism event; the field exists because the event happened. Quotation unavailable: the ProPublica repository README was not retrievable from this environment, so this rests on the field naming and the

### COMPAS · `r_days_from_arrest`

> (no quotation on this record)

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `is_recid`
- source: ProPublica compas-analysis, compas-scores-two-years field list
- note: The r_ prefix marks days from arrest in the recidivism event; the field exists because the event happened. Quotation unavailable: the ProPublica repository README was not retrievable from this environment, so this rests on the field naming and the data check, 

### COMPAS · `r_offense_date`

> (no quotation on this record)

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `is_recid`
- source: ProPublica compas-analysis, compas-scores-two-years field list
- note: The r_ prefix marks the date of the offence in the recidivism event; the field exists because the event happened. Quotation unavailable: the ProPublica repository README was not retrievable from this environment, so this rests on the field naming and the data 

### ECHO · `still_alive`

> Class attribute 0—the patient is dead at end of survival period 1—the patient is still alive

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: bulbul2024
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### HEARTFAIL · `time`

> Time period of follow-up 4–285 Days 13

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: qadri2024
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### STEEL · `Bumps`

> In this dataset, faults in steel plates are classified into 7 types, including Pastry, Zscratch, Kscratch, Stains, Dirtiness, Bumps and Other.

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: chou2021
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### STEEL · `Dirtiness`

> In this dataset, faults in steel plates are classified into 7 types, including Pastry, Zscratch, Kscratch, Stains, Dirtiness, Bumps and Other.

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: chou2021
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### STEEL · `K_Scratch`

> In this dataset, faults in steel plates are classified into 7 types, including Pastry, Zscratch, Kscratch, Stains, Dirtiness, Bumps and Other.

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: chou2021
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### STEEL · `Pastry`

> In this dataset, faults in steel plates are classified into 7 types, including Pastry, Zscratch, Kscratch, Stains, Dirtiness, Bumps and Other.

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: chou2021
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### STEEL · `Stains`

> In this dataset, faults in steel plates are classified into 7 types, including Pastry, Zscratch, Kscratch, Stains, Dirtiness, Bumps and Other.

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: chou2021
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### STEEL · `Z_Scratch`

> In this dataset, faults in steel plates are classified into 7 types, including Pastry, Zscratch, Kscratch, Stains, Dirtiness, Bumps and Other.

- label **LABEL_DERIVED**, mechanism **-**, tier **E3**
- source: chou2021
- note: admitted by adjudicate_new.py; quote is the column's own dictionary description

### SUPPORT2 · `avtisst`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: average TISS score

### SUPPORT2 · `charges`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: hospital charges

### SUPPORT2 · `d.time`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: death time

### SUPPORT2 · `dnr`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: DNR status

### SUPPORT2 · `dnrday`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: DNR order dates

### SUPPORT2 · `hospdead`

> we removed hospital death indicators, existing composite severity-of-illness scores, and subjective physician survival estimates

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Zhuang et al., Expert-Driven Survival Machines (arXiv:2606.14608), App. A.1.1
- note: named in paper as: hospital death indicators

### SUPPORT2 · `slos`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: total length of stay

### SUPPORT2 · `totcst`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: hospital charges

### SUPPORT2 · `totmcst`

> we rigorously excluded surrogate outcomes and administrative features containing future information

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `death`
- source: Adaptive-CaRe (arXiv:2602.06611), sec. results, SUPPORT2 preprocessing
- note: named in paper as: hospital charges

### TITANIC · `boat`

> (no quotation on this record)

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `survived`
- source: titanic3 data dictionary (Harrell, Vanderbilt biostatistics data repository)
- note: A lifeboat number exists for a passenger because that passenger was rescued. Quotation unavailable: the dictionary was not retrievable from this environment, so this rests on the column name and the data check.

### TITANIC · `body`

> (no quotation on this record)

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E3**
- target: `survived`
- source: titanic3 data dictionary (Harrell, Vanderbilt biostatistics data repository)
- note: A body identification number exists only for recovered dead. Quotation unavailable, as for boat.


## Leaks at tiers E1 and E2 (40)

Stronger evidence: a quotation naming the column, or a documented relationship checked against the values.

### BANK · `duration`

> this input should only be included for benchmark purposes and should be discarded if the intention is to have a realistic predictive model

- label **LABEL_DERIVED**, mechanism **TIMING**, tier **E2**
- target: `y`
- source: UCI ML Repository, Bank Marketing (DOI 10.24432/C5K306); variables table, entry 'duration'
- note: intro paper: Moro, Cortez & Rita, Decision Support Systems 2014, doi 10.1016/j.dss.2014.03.001

### DIABETES · `discharge_disposition_id`

> Integer identifier corresponding to 29 distinct values, for example, discharged to home, expired, and not available

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E2**
- target: `readmitted`
- source: UCI ML Repository 296, Diabetes 130-US hospitals, variables[discharge_disposition_id]
- note: MIXED column: 'expired' and hospice levels record the outcome, 'discharged to home' vs 'to a skilled nursing facility' is legitimately predictive. The spec diabetes_pure isolates the terminal indicator so the mechanism can be measured alone.

### KOI · `koi_fpflag_co`

> # COLUMN koi_fpflag_co:  Centroid Offset False Positive Flag

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E2**
- target: `koi_disposition`
- source: NASA Exoplanet Archive, Kepler Objects of Interest cumulative table, column definition block
- note: The flags are the vetting decisions that produce the disposition, so they are inputs to the label, not measurements of the object.

### KOI · `koi_fpflag_ec`

> # COLUMN koi_fpflag_ec:  Ephemeris Match Indicates Contamination False Positive Flag

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E2**
- target: `koi_disposition`
- source: NASA Exoplanet Archive, Kepler Objects of Interest cumulative table, column definition block
- note: The flags are the vetting decisions that produce the disposition, so they are inputs to the label, not measurements of the object.

### KOI · `koi_fpflag_nt`

> # COLUMN koi_fpflag_nt:  Not Transit-Like False Positive Flag

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E2**
- target: `koi_disposition`
- source: NASA Exoplanet Archive, Kepler Objects of Interest cumulative table, column definition block
- note: The flags are the vetting decisions that produce the disposition, so they are inputs to the label, not measurements of the object.

### KOI · `koi_fpflag_ss`

> # COLUMN koi_fpflag_ss:  Stellar Eclipse False Positive Flag

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E2**
- target: `koi_disposition`
- source: NASA Exoplanet Archive, Kepler Objects of Interest cumulative table, column definition block
- note: The flags are the vetting decisions that produce the disposition, so they are inputs to the label, not measurements of the object.

### AI4I · `HDF`

> If at least one of the above failure modes is true, the process fails and the 'machine failure' label is set to 1.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `Machine failure`
- source: UCI ML Repository 601, AI4I 2020 Predictive Maintenance Dataset, additional_info.variable_info
- note: Found by hand while re-fetching the 29 UCI records that failed to download; the frozen sieve does not match this construction. RNF is named by the same sentence and is NOT coded, because the data contradict it (1 of 19 RNF rows has the target set).

### AI4I · `OSF`

> If at least one of the above failure modes is true, the process fails and the 'machine failure' label is set to 1.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `Machine failure`
- source: UCI ML Repository 601, AI4I 2020 Predictive Maintenance Dataset, additional_info.variable_info
- note: Found by hand while re-fetching the 29 UCI records that failed to download; the frozen sieve does not match this construction. RNF is named by the same sentence and is NOT coded, because the data contradict it (1 of 19 RNF rows has the target set).

### AI4I · `PWF`

> If at least one of the above failure modes is true, the process fails and the 'machine failure' label is set to 1.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `Machine failure`
- source: UCI ML Repository 601, AI4I 2020 Predictive Maintenance Dataset, additional_info.variable_info
- note: Found by hand while re-fetching the 29 UCI records that failed to download; the frozen sieve does not match this construction. RNF is named by the same sentence and is NOT coded, because the data contradict it (1 of 19 RNF rows has the target set).

### AI4I · `TWF`

> If at least one of the above failure modes is true, the process fails and the 'machine failure' label is set to 1.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `Machine failure`
- source: UCI ML Repository 601, AI4I 2020 Predictive Maintenance Dataset, additional_info.variable_info
- note: Found by hand while re-fetching the 29 UCI records that failed to download; the frozen sieve does not match this construction. RNF is named by the same sentence and is NOT coded, because the data contradict it (1 of 19 RNF rows has the target set).

### CRIME · `arsons`

> Data combines socio-economic data from the '90 Census, law enforcement data from the 1990 Law Enforcement Management and Admin Stats survey, and crime data from the 1995 FBI UCR

- label **LABEL_DERIVED**, mechanism **TIMING**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `arsonsPerPop`

> Data combines socio-economic data from the '90 Census, law enforcement data from the 1990 Law Enforcement Management and Admin Stats survey, and crime data from the 1995 FBI UCR

- label **LABEL_DERIVED**, mechanism **TIMING**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `assaultPerPop`

> The per capita violent crimes variable was calculated using population and the sum of crime variables considered violent crimes in the United States: murder, rape, robbery, and assault.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `assaults`

> The per capita violent crimes variable was calculated using population and the sum of crime variables considered violent crimes in the United States: murder, rape, robbery, and assault.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `autoTheft`

> Data combines socio-economic data from the '90 Census, law enforcement data from the 1990 Law Enforcement Management and Admin Stats survey, and crime data from the 1995 FBI UCR

- label **LABEL_DERIVED**, mechanism **TIMING**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `autoTheftPerPop`

> Data combines socio-economic data from the '90 Census, law enforcement data from the 1990 Law Enforcement Management and Admin Stats survey, and crime data from the 1995 FBI UCR

- label **LABEL_DERIVED**, mechanism **TIMING**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `burglPerPop`

> Data combines socio-economic data from the '90 Census, law enforcement data from the 1990 Law Enforcement Management and Admin Stats survey, and crime data from the 1995 FBI UCR

- label **LABEL_DERIVED**, mechanism **TIMING**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `burglaries`

> Data combines socio-economic data from the '90 Census, law enforcement data from the 1990 Law Enforcement Management and Admin Stats survey, and crime data from the 1995 FBI UCR

- label **LABEL_DERIVED**, mechanism **TIMING**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `larcPerPop`

> Data combines socio-economic data from the '90 Census, law enforcement data from the 1990 Law Enforcement Management and Admin Stats survey, and crime data from the 1995 FBI UCR

- label **LABEL_DERIVED**, mechanism **TIMING**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `larcenies`

> Data combines socio-economic data from the '90 Census, law enforcement data from the 1990 Law Enforcement Management and Admin Stats survey, and crime data from the 1995 FBI UCR

- label **LABEL_DERIVED**, mechanism **TIMING**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `murdPerPop`

> The per capita violent crimes variable was calculated using population and the sum of crime variables considered violent crimes in the United States: murder, rape, robbery, and assault.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `murders`

> The per capita violent crimes variable was calculated using population and the sum of crime variables considered violent crimes in the United States: murder, rape, robbery, and assault.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `nonViolPerPop`

> Data combines socio-economic data from the '90 Census, law enforcement data from the 1990 Law Enforcement Management and Admin Stats survey, and crime data from the 1995 FBI UCR

- label **LABEL_DERIVED**, mechanism **TIMING**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `rapes`

> The per capita violent crimes variable was calculated using population and the sum of crime variables considered violent crimes in the United States: murder, rape, robbery, and assault.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `rapesPerPop`

> The per capita violent crimes variable was calculated using population and the sum of crime variables considered violent crimes in the United States: murder, rape, robbery, and assault.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `robbbPerPop`

> The per capita violent crimes variable was calculated using population and the sum of crime variables considered violent crimes in the United States: murder, rape, robbery, and assault.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### CRIME · `robberies`

> The per capita violent crimes variable was calculated using population and the sum of crime variables considered violent crimes in the United States: murder, rape, robbery, and assault.

- label **LABEL_DERIVED**, mechanism **REASON**, tier **E1**
- target: `violentPerPop`
- source: UCI ML Repository 211, Communities and Crime Unnormalized, dataset summary

### LC · `collection_recovery_fee`

> post charge off collection fee

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- source: LendingClub LCDataDictionary.csv

### LC · `recoveries`

> post charge off gross recovery

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- source: LendingClub LCDataDictionary.csv

### MI · `A_V_BLOK`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

### MI · `DRESSLER`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

### MI · `FIBR_JELUD`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

### MI · `FIBR_PREDS`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

### MI · `JELUD_TAH`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

### MI · `LET_IS`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

### MI · `OTEK_LANC`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

### MI · `PREDS_TAH`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

### MI · `P_IM_STEN`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

### MI · `RAZRIV`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

### MI · `REC_IM`

> Complications and outcomes of myocardial infarction:

- label **LABEL_DERIVED**, mechanism **CONSEQUENCE**, tier **E1**
- target: `ZSN`
- source: UCI ML Repository 579, Myocardial infarction complications, attribute documentation

