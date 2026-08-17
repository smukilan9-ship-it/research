# AI4I — schema

**Stratum A.** 10 columns, 4 documented positives, 10,000 rows.

- **Target**: `Machine failure`
- **Prediction point**: during operation, before any failure has occurred
- **Source**: UCI 601 — AI4I 2020 Predictive Maintenance
- **Licence**: CC BY 4.0

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
Type, Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min], TWF, HDF, PWF, OSF
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `TWF` | REASON |
| `HDF` | REASON |
| `PWF` | REASON |
| `OSF` | REASON |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
