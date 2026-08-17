# CRIME — schema

**Stratum B.** 144 columns, 17 documented positives, 2,215 rows.

- **Target**: `violentPerPop`
- **Prediction point**: from the 1990 census and 1990 LEMAS survey, before the 1995 crime figures are published
- **Source**: UCI 211 — Communities and Crime Unnormalized
- **Licence**: CC BY 4.0

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
State, countyCode, communityCode, pop, perHoush, pctBlack, pctWhite, pctAsian, pctHisp, pct12-21, pct12-29, pct16-24, pct65up, persUrban, pctUrban, medIncome, pctWwage, pctWfarm, pctWdiv, pctWsocsec, pctPubAsst, pctRetire, medFamIncome, perCapInc, whitePerCap, blackPerCap, NAperCap, asianPerCap, otherPerCap, hispPerCap, persPoverty, pctPoverty, pctLowEdu, pctNotHSgrad, pctCollGrad, pctUnemploy, pctEmploy, pctEmployMfg, pctEmployProfServ, pctOccupManu, pctOccupMgmt, pctMaleDivorc, pctMaleNevMar, pctFemDivorc, pctAllDivorc, persPerFam, pct2Par, pctKids2Par, pctKids-4w2Par, pct12-17w2Par, pctWorkMom-6, pctWorkMom-18, kidsBornNevrMarr, pctKidsBornNevrMarr, numForeignBorn, pctFgnImmig-3, pctFgnImmig-5, pctFgnImmig-8, pctFgnImmig-10, pctImmig-3, pctImmig-5, pctImmig-8, pctImmig-10, pctSpeakOnlyEng, pctNotSpeakEng, pctLargHousFam, pctLargHous, persPerOccupHous, persPerOwnOccup, persPerRenterOccup, pctPersOwnOccup, pctPopDenseHous, pctSmallHousUnits, medNumBedrm, houseVacant, pctHousOccup, pctHousOwnerOccup, pctVacantBoarded, pctVacant6up, medYrHousBuilt, pctHousWOphone, pctHousWOplumb, ownHousLowQ, ownHousMed, ownHousUperQ, ownHousQrange, rentLowQ, rentMed, rentUpperQ, rentQrange, medGrossRent, medRentpctHousInc, medOwnCostpct, medOwnCostPctWO, persEmergShelt, persHomeless, pctForeignBorn, pctBornStateResid, pctSameHouse-5, pctSameCounty-5, pctSameState-5, numPolice, policePerPop, policeField, policeFieldPerPop, policeCalls, policCallPerPop, policCallPerOffic, policePerPop2, racialMatch, pctPolicWhite, pctPolicBlack, pctPolicHisp, pctPolicAsian, pctPolicMinority, officDrugUnits, numDiffDrugsSeiz, policAveOT, landArea, popDensity, pctUsePubTrans, policCarsAvail, policOperBudget, pctPolicPatrol, gangUnit, pctOfficDrugUnit, policBudgetPerPop, murders, murdPerPop, rapes, rapesPerPop, robberies, robbbPerPop, assaults, assaultPerPop, burglaries, burglPerPop, larcenies, larcPerPop, autoTheft, autoTheftPerPop, arsons, arsonsPerPop, nonViolPerPop
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `murders` | CONTESTED |
| `murdPerPop` | CONTESTED |
| `rapes` | CONTESTED |
| `rapesPerPop` | CONTESTED |
| `robberies` | CONTESTED |
| `robbbPerPop` | CONTESTED |
| `assaults` | CONTESTED |
| `assaultPerPop` | CONTESTED |
| `burglaries` | CONTESTED |
| `burglPerPop` | CONTESTED |
| `larcenies` | CONTESTED |
| `larcPerPop` | CONTESTED |
| `autoTheft` | CONTESTED |
| `autoTheftPerPop` | CONTESTED |
| `arsons` | CONTESTED |
| `arsonsPerPop` | CONTESTED |
| `nonViolPerPop` | CONTESTED |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
