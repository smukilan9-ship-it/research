# LC — schema

**Stratum A.** 29 columns, 2 documented positives, 39,717 rows.

- **Target**: `loan_status`
- **Prediction point**: at loan origination, before any repayment behaviour is observed
- **Source**: Lending Club accepted loans, via Kaggle (wordsforthewise)
- **Licence**: CHECK BEFORE REDISTRIBUTING — Kaggle terms

## What the model saw

At **C1**, the primary condition: the column names below and the target, in this order. No values, no descriptions, no row counts. Column order is shuffled per seed; this is the canonical order.

```
loan_amnt, funded_amnt, funded_amnt_inv, term, int_rate, installment, grade, sub_grade, emp_length, home_ownership, annual_inc, verification_status, issue_d, purpose, addr_state, dti, delinq_2yrs, earliest_cr_line, inq_last_6mths, mths_since_last_delinq, mths_since_last_record, open_acc, pub_rec, revol_bal, revol_util, total_acc, pub_rec_bankruptcies, recoveries, collection_recovery_fee
```

At **C4** only, five sample rows are added — that condition is the ablation, not the headline.

## Ground truth

| column | mechanism |
|---|---|
| `recoveries` | CONSEQUENCE |
| `collection_recovery_fee` | CONSEQUENCE |

Every other column is coded **legitimate by default** — no admissible record was found for it. Precision is therefore a lower bound: a model flagging something real but undocumented is scored wrong. Quotations licensing each positive are in `../APPENDIX.md`.
