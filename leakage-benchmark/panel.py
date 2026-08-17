"""Build the dataset-level labelling panel from WELL-KNOWN datasets.

The first panel was 20 arbitrary UCI sets and was rightly rejected: a coder
cannot judge provenance in a table whose domain they have no feel for.  This
one is chosen so the judgment is actually makeable from the column list plus a
one-line description of what a row is and what is being predicted.

Selection rule, stated so it can be criticised:
  * heavily used, recognisable datasets first -- the ones that appear in
    tutorials, benchmarks and course material, so a reader knows them
  * a documented or widely-discussed leak that is INFERABLE from the column
    names, not one that needs the archive's codebook
  * clean datasets at the end, unlabelled as such in the sheet, so the binary
    task is not degenerate

`why_known` is context for the coder, NOT a hint about which column leaks.  It
says what one row is and what is predicted -- exactly what the LLM is given at
condition C1.  Giving the coder less than the model gets would make the
comparison unfair in the wrong direction.
"""
import csv, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
UCI = HERE + "uci/"
OUT = HERE + "panel_sheet.csv"

# (key, name, source, target, one-line description of a row + what is predicted)
PANEL = [
    ("titanic", "Titanic (passenger manifest)", "local", "survived",
     "one row = one passenger on the 1912 voyage; predict whether they survived"),
    ("uci222", "Bank Marketing", "uci/222", "y",
     "one row = one customer contacted in a phone campaign; predict whether they subscribed to a term deposit"),
    ("uci320", "Student Performance (maths)", "uci/320", "G3",
     "one row = one pupil across a school year; predict the final-period grade G3"),
    ("diabetes", "Diabetes 130-US Hospitals", "local", "readmitted",
     "one row = one hospital admission; predict readmission within 30 days of discharge"),
    ("uci519", "Heart Failure Clinical Records", "uci/519", "DEATH_EVENT",
     "one row = one heart-failure patient at a clinical assessment; predict death during the study"),
    ("ai4i", "AI4I 2020 Predictive Maintenance", "local", "Machine failure",
     "one row = one machine-hour of operation; predict whether the machine failed"),
    ("uci468", "Online Shoppers Purchasing Intention", "uci/468", "Revenue",
     "one row = one web session; predict whether the session ended in a purchase"),
    ("uci198", "Steel Plates Faults", "uci/198", "Other_Faults",
     "one row = one inspected steel plate; predict whether its defect is of the residual 'other' type"),
    ("uci38", "Echocardiogram", "uci/38", "alive_at_1",
     "one row = one patient after a heart attack; predict survival to one year"),
    ("uci383", "Cervical Cancer (Risk Factors)", "uci/383", "Biopsy",
     "one row = one patient screened for cervical cancer; predict the biopsy result"),
    ("uci880", "SUPPORT2 (critical care)", "uci/880", "death",
     "one row = one seriously ill hospitalised adult, assessed on study day 3; predict death"),
    ("uci565", "Bone Marrow Transplant: Children", "uci/565", "survival_status",
     "one row = one paediatric stem-cell transplant; predict survival status"),
    ("uci16", "Breast Cancer Wisconsin (Prognostic)", "uci/16", "outcome",
     "one row = one breast cancer case after surgery; predict recurrence vs non-recurrence"),
    ("compas", "COMPAS Recidivism", "local", "two_year_recid",
     "one row = one defendant at a pretrial risk screening; predict re-arrest within two years"),
    ("lc", "Lending Club Loans", "local", "loan_status",
     "one row = one issued consumer loan; predict whether it was repaid or charged off"),
    ("uci579", "Myocardial Infarction Complications", "uci/579", "ZSN",
     "one row = one myocardial infarction admission; predict chronic heart failure as a complication"),
    # ---- from here on, chosen as likely-clean; NOT marked as such in the sheet
    ("uci53", "Iris", "uci/53", "class",
     "one row = one iris flower with four measurements; predict the species"),
    ("uci109", "Wine", "uci/109", "class",
     "one row = one wine sample with chemical assay results; predict the cultivar"),
    ("uci267", "Banknote Authentication", "uci/267", "class",
     "one row = one banknote image with wavelet statistics; predict genuine vs forged"),
    ("uci1", "Abalone", "uci/1", "Rings",
     "one row = one abalone with physical measurements; predict age in rings"),
    ("uci73", "Mushroom", "uci/73", "poisonous",
     "one row = one mushroom described by cap, gill and stalk features; predict edible vs poisonous"),
    ("uci144", "German Credit (Statlog)", "uci/144", "class",
     "one row = one credit applicant at application time; predict good vs bad credit risk"),
]

LOCAL = {"titanic", "diabetes", "ai4i", "compas", "lc"}


def columns_of(key, src):
    if key in LOCAL:
        import harness as H
        s = H.LOADERS[key]()
        return [str(c) for c in s["df"].columns], None
    uid = src.split("/")[1]
    p = f"{UCI}{uid}/data.csv"
    if not os.path.exists(p):
        # some ship as .data/.arff/.xls; newdata.py already handles those
        import newdata as ND
        alt = {"16": "wpbc", "38": "echo", "198": "steel", "383": "cervical",
               "565": "bonemarrow", "579": "mi", "880": "support2", "222": "bank",
               "519": "heartfail"}
        if uid in alt:
            try:
                return [str(c) for c in ND.NEW[alt[uid]]()["df"].columns], None
            except Exception as e:
                return None, f"loader failed: {type(e).__name__}"
        return None, "not downloaded"
    try:
        return [str(c).strip() for c in pd.read_csv(p, nrows=50).columns], None
    except Exception as e:
        return None, f"unreadable: {type(e).__name__}"


def main():
    sys.path.insert(0, HERE)
    rows, bad = [], []
    for key, name, src, target, desc in PANEL:
        cols, err = columns_of(key, src)
        if cols is None:
            bad.append((name, err))
            continue
        rows.append(dict(
            dataset=name, source=src, n_columns=len(cols),
            target=target, what_a_row_is=desc,
            columns=" | ".join(c for c in cols if c != target),
            # coder fills these three, blind
            has_label_derived="", which_columns="", reason=""))
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} datasets -> {OUT}")
    for n, e in bad:
        print(f"  SKIPPED {n}: {e}")
    print(f"\n{'dataset':<38}{'cols':>5}  target")
    for r in rows:
        print(f"  {r['dataset']:<36}{r['n_columns']:>5}  {r['target']}")


if __name__ == "__main__":
    main()
