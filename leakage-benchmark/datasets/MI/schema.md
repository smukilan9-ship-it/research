# MI — schema

**Stratum B.** 122 columns, 11 documented positives, 1,700 rows.

- **Target**: `ZSN`
- **Prediction point**: at admission to intensive care, before any in-hospital complication is observed
- **Source**: UCI 579 — Myocardial infarction complications
- **Licence**: CC BY 4.0

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
AGE, SEX, INF_ANAM, STENOK_AN, FK_STENOK, IBS_POST, IBS_NASL, GB, SIM_GIPERT, DLIT_AG, ZSN_A, nr_11, nr_01, nr_02, nr_03, nr_04, nr_07, nr_08, np_01, np_04, np_05, np_07, np_08, np_09, np_10, endocr_01, endocr_02, endocr_03, zab_leg_01, zab_leg_02, zab_leg_03, zab_leg_04, zab_leg_06, S_AD_KBRIG, D_AD_KBRIG, S_AD_ORIT, D_AD_ORIT, O_L_POST, K_SH_POST, MP_TP_POST, SVT_POST, GT_POST, FIB_G_POST, ant_im, lat_im, inf_im, post_im, IM_PG_P, ritm_ecg_p_01, ritm_ecg_p_02, ritm_ecg_p_04, ritm_ecg_p_06, ritm_ecg_p_07, ritm_ecg_p_08, n_r_ecg_p_01, n_r_ecg_p_02, n_r_ecg_p_03, n_r_ecg_p_04, n_r_ecg_p_05, n_r_ecg_p_06, n_r_ecg_p_08, n_r_ecg_p_09, n_r_ecg_p_10, n_p_ecg_p_01, n_p_ecg_p_03, n_p_ecg_p_04, n_p_ecg_p_05, n_p_ecg_p_06, n_p_ecg_p_07, n_p_ecg_p_08, n_p_ecg_p_09, n_p_ecg_p_10, n_p_ecg_p_11, n_p_ecg_p_12, fibr_ter_01, fibr_ter_02, fibr_ter_03, fibr_ter_05, fibr_ter_06, fibr_ter_07, fibr_ter_08, GIPO_K, K_BLOOD, GIPER_NA, NA_BLOOD, ALT_BLOOD, AST_BLOOD, KFK_BLOOD, L_BLOOD, ROE, TIME_B_S, R_AB_1_n, R_AB_2_n, R_AB_3_n, NA_KB, NOT_NA_KB, LID_KB, NITR_S, NA_R_1_n, NA_R_2_n, NA_R_3_n, NOT_NA_1_n, NOT_NA_2_n, NOT_NA_3_n, LID_S_n, B_BLOK_S_n, ANT_CA_S_n, GEPAR_S_n, ASP_S_n, TIKL_S_n, TRENT_S_n, FIBR_PREDS, PREDS_TAH, JELUD_TAH, FIBR_JELUD, A_V_BLOK, OTEK_LANC, RAZRIV, DRESSLER, REC_IM, P_IM_STEN, LET_IS
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `FIBR_PREDS` | CONTESTED |
| `PREDS_TAH` | CONTESTED |
| `JELUD_TAH` | CONTESTED |
| `FIBR_JELUD` | CONTESTED |
| `A_V_BLOK` | CONTESTED |
| `OTEK_LANC` | CONTESTED |
| `RAZRIV` | CONTESTED |
| `DRESSLER` | CONTESTED |
| `REC_IM` | CONTESTED |
| `P_IM_STEN` | CONTESTED |
| `LET_IS` | CONTESTED |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
