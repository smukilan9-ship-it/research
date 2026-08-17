# TITANIC — schema

**Stratum A.** 9 columns, 2 documented positives, 1,309 rows.

- **Target**: `survived`
- **Prediction point**: at the moment of boarding
- **Source**: Vanderbilt Biostatistics titanic3 (1,309 rows)
- **Licence**: public

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
pclass, sex, age, sibsp, parch, fare, embarked, boat, body
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `boat` | CONSEQUENCE |
| `body` | CONSEQUENCE |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
