# STUDENT — schema

**Stratum B.** 32 columns, 0 documented positives, 649 rows.

- **Target**: `G3`
- **Prediction point**: before the third-period final grade is issued
- **Source**: UCI 320 — Student Performance
- **Licence**: CC BY 4.0

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
school, sex, age, address, famsize, Pstatus, Medu, Fedu, Mjob, Fjob, reason, guardian, traveltime, studytime, failures, schoolsup, famsup, paid, activities, nursery, higher, internet, romantic, famrel, freetime, goout, Dalc, Walc, health, absences, G1, G2
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

No documented positives. This dataset is in the corpus precisely because a transfer set of only-positive tables would be a different test.

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
