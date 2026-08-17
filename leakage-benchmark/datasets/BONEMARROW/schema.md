# BONEMARROW — schema

**Stratum A.** 36 columns, 5 documented positives, 187 rows.

- **Target**: `survival_status`
- **Prediction point**: at transplantation, before any post-transplant outcome
- **Source**: UCI 565 — Bone marrow transplant: children
- **Licence**: CC BY 4.0

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
Recipientgender, Stemcellsource, Donorage, Donorage35, IIIV, Gendermatch, DonorABO, RecipientABO, RecipientRh, ABOmatch, CMVstatus, DonorCMV, RecipientCMV, Disease, Riskgroup, Txpostrelapse, Diseasegroup, HLAmatch, HLAmismatch, Antigen, Alel, HLAgrI, Recipientage, Recipientage10, Recipientageint, Relapse, aGvHDIIIIV, extcGvHD, CD34kgx10d6, CD3dCD34, CD3dkgx10d8, Rbodymass, ANCrecovery, PLTrecovery, time_to_aGvHD_III_IV, survival_time
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `aGvHDIIIIV` | TIMING |
| `ANCrecovery` | TIMING |
| `PLTrecovery` | TIMING |
| `time_to_aGvHD_III_IV` | TIMING |
| `survival_time` | CONTESTED |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
