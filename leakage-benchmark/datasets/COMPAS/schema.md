# COMPAS — schema

**Stratum A.** 15 columns, 4 documented positives, 6,172 rows.

- **Target**: `two_year_recid`
- **Prediction point**: at the COMPAS screening date, before any subsequent arrest
- **Source**: ProPublica, compas-scores-two-years.csv
- **Licence**: public

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
sex, age, age_cat, race, juv_fel_count, juv_misd_count, juv_other_count, priors_count, c_charge_degree, c_charge_desc, days_b_screening_arrest, r_charge_degree, r_days_from_arrest, r_offense_date, r_charge_desc
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `r_charge_degree` | CONSEQUENCE |
| `r_days_from_arrest` | CONSEQUENCE |
| `r_offense_date` | CONSEQUENCE |
| `r_charge_desc` | CONSEQUENCE |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
