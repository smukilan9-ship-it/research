# ECHO — schema

**Stratum A.** 12 columns, 1 documented positive, 131 rows.

- **Target**: `alive_at_1`
- **Prediction point**: at the echocardiogram, before the one-year mark
- **Source**: UCI 38 — Echocardiogram
- **Licence**: CC BY 4.0

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
survival, still_alive, age_at_heart_attack, pericardial_effusion, fractional_shortening, epss, lvdd, wall_motion_score, wall_motion_index, mult, name, group
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `still_alive` | CONSEQUENCE |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
