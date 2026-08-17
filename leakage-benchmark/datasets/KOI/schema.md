# KOI — schema

**Stratum A.** 40 columns, 4 documented positives, 9,563 rows.

- **Target**: `koi_disposition`
- **Prediction point**: when the object is first vetted, before any disposition is assigned
- **Source**: NASA Exoplanet Archive, Kepler Objects of Interest cumulative table, retrieved 2026-08-08
- **Licence**: public domain (NASA)

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
koi_period, koi_period_err1, koi_period_err2, koi_time0bk, koi_time0bk_err1, koi_time0bk_err2, koi_impact, koi_impact_err1, koi_impact_err2, koi_duration, koi_duration_err1, koi_duration_err2, koi_depth, koi_depth_err1, koi_depth_err2, koi_prad, koi_prad_err1, koi_prad_err2, koi_teq, koi_insol, koi_insol_err1, koi_insol_err2, koi_model_snr, koi_tce_plnt_num, koi_steff, koi_steff_err1, koi_steff_err2, koi_slogg, koi_slogg_err1, koi_slogg_err2, koi_srad, koi_srad_err1, koi_srad_err2, ra, dec, koi_kepmag, koi_fpflag_nt, koi_fpflag_ss, koi_fpflag_co, koi_fpflag_ec
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `koi_fpflag_nt` | REASON |
| `koi_fpflag_ss` | REASON |
| `koi_fpflag_co` | REASON |
| `koi_fpflag_ec` | REASON |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
