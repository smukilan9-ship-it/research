# Samples — the workflow vs a single prompt, on the same test cases

Every case below is scored on the **same columns**: only those answered
under the single prompt *and* all four workflow passes. One population,
two methods. Verdicts and quoted reasons are real cached model outputs.

- **Single prompt** = one call, P1's query alone (`schema + target →
  which columns could not honestly be known?`).
- **Workflow** = four differently-worded passes, merged by counting
  agreements: 4/4 → auto-drop, 1–3 → human review, 0 → keep.

---

## Case 1: `MI` — predicting `ZSN`

*The clean win. A single prompt raises 9 false alarms on a 122-column table; the workflow auto-drops all 11 real leaks with none.*

**Prediction point (human input):** at admission to intensive care, before any in-hospital complication is observed  
**Model:** `claude-opus-5-max` · **Columns:** 122 · **Documented leaks:** 11

| | flagged | correct | false alarms | leaks missed |
|---|---|---|---|---|
| **Single prompt** | 20 | 11 | **9** | **0** |
| **Workflow — auto-drop** | 11 | 11 | 0 | — |
| **Workflow — to review** | 17 | 0 | 17 | — |
| **Workflow — kept** | 0 | — | — | **0** |

| column | truth | single prompt | P1 | P2 | P3 | P4 | workflow says |
|---|---|---|---|---|---|---|---|
| `FIBR_PREDS` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `PREDS_TAH` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `JELUD_TAH` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `FIBR_JELUD` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `A_V_BLOK` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `OTEK_LANC` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `RAZRIV` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `DRESSLER` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `REC_IM` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `P_IM_STEN` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `LET_IS` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `R_AB_1_n` | legitimate | 🚩 flagged | 🚩 | 🚩 | · | 🚩 | **review** |
| `R_AB_2_n` | legitimate | 🚩 flagged | 🚩 | 🚩 | · | 🚩 | **review** |
| `R_AB_3_n` | legitimate | 🚩 flagged | 🚩 | 🚩 | · | 🚩 | **review** |

*(14 further flagged columns omitted for length.)*

**Why `R_AB_1_n` went to a human** — the passes disagreed, in the model's own words:

- **P1 bare** → FLAGGED — *“Relapse of pain in the first hospital hours, recorded after the admission prediction point.”*
- **P2 timing** → FLAGGED — *“Pain relapse during the first hospital hours has not yet occurred at admission.”*
- **P3 derivation** → allowed — *“Pain relapse in the first hospital hours, fixed early in the stay.”*
- **P4 reworded** → FLAGGED — *“Pain relapse during the first hospital hours, known only after an admission-time prediction.”*

Ground truth: this column **is not** a documented leak. A single prompt returns one of these four answers and no indication that the other three exist.

---

## Case 2: `STEEL` — predicting `Other_Faults`

*Recall rescue, and note HOW. A single prompt misses all six sibling fault columns silently. The workflow does not catch them outright either — it escalates all six to a human instead of dropping them on the floor.*

**Prediction point (human input):** when the plate is inspected, before a fault type is assigned  
**Model:** `nvidia/nemotron-3-super-120b-a12b::high` · **Columns:** 33 · **Documented leaks:** 6

| | flagged | correct | false alarms | leaks missed |
|---|---|---|---|---|
| **Single prompt** | 0 | 0 | **0** | **6** |
| **Workflow — auto-drop** | 0 | 0 | 0 | — |
| **Workflow — to review** | 6 | 6 | 0 | — |
| **Workflow — kept** | 0 | — | — | **0** |

| column | truth | single prompt | P1 | P2 | P3 | P4 | workflow says |
|---|---|---|---|---|---|---|---|
| `Pastry` | **LEAK** | · allowed | · | · | · | 🚩 | **review** |
| `Z_Scratch` | **LEAK** | · allowed | · | · | · | 🚩 | **review** |
| `K_Scratch` | **LEAK** | · allowed | · | · | · | 🚩 | **review** |
| `Stains` | **LEAK** | · allowed | · | · | · | 🚩 | **review** |
| `Dirtiness` | **LEAK** | · allowed | · | · | · | 🚩 | **review** |
| `Bumps` | **LEAK** | · allowed | · | · | · | 🚩 | **review** |

**Why `Pastry` went to a human** — the passes disagreed, in the model's own words:

- **P1 bare** → allowed — *“Feature likely derived from image data available at prediction time.”*
- **P2 timing** → allowed — *“Insufficient information to determine if known at inspection time.”*
- **P3 derivation** → allowed — *“Measured from steel plate image before fault classification, thus known at prediction time.”*
- **P4 reworded** → FLAGGED — *“Indicates a specific fault type, unknown at prediction time.”*

Ground truth: this column **is** a documented leak. A single prompt returns one of these four answers and no indication that the other three exist.

---

## Case 3: `SUPPORT2` — predicting `death`

*The cost, shown rather than hidden. Auto-drop is perfectly precise, and the price is 11 columns in review of which 8 are false alarms.*

**Prediction point (human input):** on study day 3, before any subsequent outcome is observed  
**Model:** `nvidia/nemotron-3-super-120b-a12b::high` · **Columns:** 46 · **Documented leaks:** 9

| | flagged | correct | false alarms | leaks missed |
|---|---|---|---|---|
| **Single prompt** | 14 | 8 | **6** | **1** |
| **Workflow — auto-drop** | 6 | 6 | 0 | — |
| **Workflow — to review** | 11 | 3 | 8 | — |
| **Workflow — kept** | 0 | — | — | **0** |

| column | truth | single prompt | P1 | P2 | P3 | P4 | workflow says |
|---|---|---|---|---|---|---|---|
| `hospdead` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `slos` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `d.time` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `charges` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `totcst` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `totmcst` | **LEAK** | 🚩 flagged | 🚩 | 🚩 | 🚩 | 🚩 | **auto-drop** |
| `avtisst` | **LEAK** | 🚩 flagged | 🚩 | · | 🚩 | 🚩 | **review** |
| `dnrday` | **LEAK** | 🚩 flagged | 🚩 | · | 🚩 | 🚩 | **review** |
| `dnr` | **LEAK** | · allowed | · | · | 🚩 | 🚩 | **review** |
| `surv2m` | legitimate | 🚩 flagged | 🚩 | 🚩 | · | 🚩 | **review** |
| `surv6m` | legitimate | 🚩 flagged | 🚩 | 🚩 | · | 🚩 | **review** |
| `prg2m` | legitimate | 🚩 flagged | 🚩 | 🚩 | · | 🚩 | **review** |
| `prg6m` | legitimate | 🚩 flagged | 🚩 | 🚩 | · | 🚩 | **review** |
| `adlsc` | legitimate | 🚩 flagged | 🚩 | · | 🚩 | 🚩 | **review** |

*(3 further flagged columns omitted for length.)*

**Why `avtisst` went to a human** — the passes disagreed, in the model's own words:

- **P1 bare** → FLAGGED — *“Average daily cost unknown until stay ends.”*
- **P2 timing** → allowed — *“Insufficient information to determine timing relative to day 3.”*
- **P3 derivation** → FLAGGED — *“Average daily severity score requires data over the hospital stay.”*
- **P4 reworded** → FLAGGED — *“Average cost requires cost data accumulated over stay.”*

Ground truth: this column **is** a documented leak. A single prompt returns one of these four answers and no indication that the other three exist.

---

## Case 4: `STUDENT` — predicting `G3`

*A table with NO leaks, where the only correct behaviour is silence. The single prompt raises three false alarms; the workflow auto-drops nothing and routes all three to review.*

**Prediction point (human input):** before the third-period final grade is issued  
**Model:** `claude-opus-5-max` · **Columns:** 32 · **Documented leaks:** 0

| | flagged | correct | false alarms | leaks missed |
|---|---|---|---|---|
| **Single prompt** | 3 | 0 | **3** | **0** |
| **Workflow — auto-drop** | 0 | 0 | 0 | — |
| **Workflow — to review** | 3 | 0 | 3 | — |
| **Workflow — kept** | 0 | — | — | **0** |

| column | truth | single prompt | P1 | P2 | P3 | P4 | workflow says |
|---|---|---|---|---|---|---|---|
| `absences` | legitimate | 🚩 flagged | 🚩 | · | 🚩 | 🚩 | **review** |
| `G1` | legitimate | 🚩 flagged | 🚩 | · | 🚩 | 🚩 | **review** |
| `G2` | legitimate | 🚩 flagged | 🚩 | · | 🚩 | 🚩 | **review** |

**Why `absences` went to a human** — the passes disagreed, in the model's own words:

- **P1 bare** → FLAGGED — *“Absence count accumulates across the whole school year, so its recorded total is only final at the same moment G3 is.”*
- **P2 timing** → allowed — *“The measurement window is unspecified: if it is the full-year total it keeps accruing past the prediction point, but it could be an as-of-date count.”*
- **P3 derivation** → FLAGGED — *“Total school absences accumulate over the same school year as the final grade, so the count is not final at an early prediction point.”*
- **P4 reworded** → FLAGGED — *“Full-year absence count only reaches its final value when the year ends, alongside G3.”*

Ground truth: this column **is not** a documented leak. A single prompt returns one of these four answers and no indication that the other three exist.

---

## What the cases show together

1. **The workflow's win is precision, not recall.** Requiring four
   differently-worded passes to agree raises precision from 0.729 to
   0.839 across the full 2,548-judgment population.
2. **The union workflow is a trap.** Flagging on *any* pass reaches 0.936
   recall and drops precision to 0.583 — worse F1 than the single prompt
   it was supposed to improve on.
3. **The routing is the product.** A single call returns a flat list. The
   workflow returns three lists, and the middle one is the only place a
   human's time is worth spending.

Full numbers: `python3 workflow_eval.py`.
