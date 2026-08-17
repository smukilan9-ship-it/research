# STEEL — schema

**Stratum A.** 33 columns, 6 documented positives, 1,941 rows.

- **Target**: `Other_Faults`
- **Prediction point**: when the plate is inspected, before a fault type is assigned
- **Source**: UCI 198 — Steel Plates Faults
- **Licence**: CC BY 4.0

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
X_Minimum, X_Maximum, Y_Minimum, Y_Maximum, Pixels_Areas, X_Perimeter, Y_Perimeter, Sum_of_Luminosity, Minimum_of_Luminosity, Maximum_of_Luminosity, Length_of_Conveyer, TypeOfSteel_A300, TypeOfSteel_A400, Steel_Plate_Thickness, Edges_Index, Empty_Index, Square_Index, Outside_X_Index, Edges_X_Index, Edges_Y_Index, Outside_Global_Index, LogOfAreas, Log_X_Index, Log_Y_Index, Orientation_Index, Luminosity_Index, SigmoidOfAreas, Pastry, Z_Scratch, K_Scratch, Stains, Dirtiness, Bumps
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `Pastry` | REASON |
| `Z_Scratch` | REASON |
| `K_Scratch` | REASON |
| `Stains` | REASON |
| `Dirtiness` | REASON |
| `Bumps` | REASON |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
