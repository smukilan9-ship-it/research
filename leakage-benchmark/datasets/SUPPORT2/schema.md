# SUPPORT2 — schema

**Stratum A.** 47 columns, 9 documented positives, 9,105 rows.

- **Target**: `death`
- **Prediction point**: on study day 3, before any subsequent outcome is observed
- **Source**: UCI 880 — SUPPORT2
- **Licence**: CC BY 4.0

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
id, age, sex, hospdead, slos, d.time, dzgroup, dzclass, num.co, edu, income, scoma, charges, totcst, totmcst, avtisst, race, sps, aps, surv2m, surv6m, hday, diabetes, dementia, ca, prg2m, prg6m, dnr, dnrday, meanbp, wblc, hrt, resp, temp, pafi, alb, bili, crea, sod, ph, glucose, bun, urine, adlp, adls, sfdm2, adlsc
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `hospdead` | CONSEQUENCE |
| `slos` | CONSEQUENCE |
| `d.time` | CONSEQUENCE |
| `charges` | CONSEQUENCE |
| `totcst` | CONSEQUENCE |
| `totmcst` | CONSEQUENCE |
| `avtisst` | CONSEQUENCE |
| `dnr` | CONSEQUENCE |
| `dnrday` | CONSEQUENCE |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
