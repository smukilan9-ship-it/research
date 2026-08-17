"""Dataset-level study: does this table contain ANY label-derived column?

WHY A SEPARATE STUDY
  The main benchmark asks a per-column question and grounds every label in a
  quotable source.  That is expensive: 50 PDFs bought 46 positives across 12
  datasets, and 8 further datasets yielded none.  A dataset-level judgment --
  "would a careful analyst find at least one leak here?" -- is far cheaper to
  produce, so one expert can label 20 datasets in an afternoon.  It also answers
  the question a practitioner actually asks first: *is it worth auditing this
  dataset at all?*

  It is a DIFFERENT evidence standard and must be reported separately.  The main
  corpus rests on documentation (PROTOCOL 4 tiers E1-E4); this rests on a named
  expert's judgment.  Merging them would silently relax the standard the whole
  paper is built on.

DESIGN CONSTRAINTS THIS FILE ENFORCES
  * The set must contain plausible NEGATIVES.  A panel where every dataset leaks
    makes the task degenerate -- a model that always answers "yes" scores 100%
    and we learn nothing.  Roughly half the panel is chosen as likely-clean.
  * The coder labels BLIND, before seeing any model output, and records a
    reason plus the specific column(s) if any.  The reason is what makes a
    disagreement adjudicable later.
  * Datasets already used to develop the C6/C7 prompts are marked, so the
    held-out subset can be reported separately.

WHAT IS NOT CLAIMED
  A single coder gives no reliability estimate.  Cohen's kappa needs a second
  coder on at least a subset; until then this is one expert's opinion, however
  careful, and the paper must say so.
"""
import csv, json, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
UCI = HERE + "uci/"
OUT = HERE + "dataset_level_sheet.csv"

# (uci_id, name, target column or "", why it is on the panel, in_development?)
# `expect` is the ANALYST'S PRIOR used only to balance the panel.  It is NOT a
# label and is deliberately kept out of the sheet the coder sees.
PANEL = [
    # --- already loaded, zero documented evidence (attrition set) ----------
    (193, "Cardiotocography",              "NSP",      "leaky?",  False),
    (383, "Cervical Cancer Risk Factors",  "Biopsy",   "leaky?",  False),
    (579, "Myocardial Infarction Compl.",  "ZSN",      "leaky?",  False),
    (16,  "Breast Cancer Wisc. Prognostic","outcome",  "leaky?",  False),
    (350, "Default of Credit Card Clients","",         "leaky?",  False),
    (82,  "Post-Operative Patient",        "decision", "leaky?",  False),
    (890, "AIDS Clinical Trials ACTG175",  "cid",      "leaky?",  False),
    # --- likely to contain a leak, not used in development ------------------
    (47,  "Horse Colic",                   "",         "leaky?",  False),
    (46,  "Hepatitis",                     "",         "leaky?",  False),
    (45,  "Heart Disease (Cleveland)",     "",         "leaky?",  False),
    (174, "Parkinsons",                    "",         "leaky?",  False),
    # --- likely clean: measurement-only tables ------------------------------
    (53,  "Iris",                          "",         "clean?",  False),
    (109, "Wine",                          "",         "clean?",  False),
    (1,   "Abalone",                       "",         "clean?",  False),
    (19,  "Car Evaluation",                "",         "clean?",  False),
    (73,  "Mushroom",                      "",         "clean?",  False),
    (94,  "Spambase",                      "",         "clean?",  False),
    (52,  "Ionosphere",                    "",         "clean?",  False),
    (42,  "Glass Identification",          "",         "clean?",  False),
    (267, "Banknote Authentication",       "",         "clean?",  False),
]


# three panel datasets ship as .xls or headerless .data, not data.csv; they
# already have loaders in newdata.py, so reuse those rather than reimplement
NEWDATA_KEY = {16: "wpbc", 350: "credit", 82: "postop"}


def columns_of(uid):
    if uid in NEWDATA_KEY:
        try:
            import newdata as ND
            s = ND.NEW[NEWDATA_KEY[uid]]()
            return [str(c).strip() for c in s["df"].columns], None
        except Exception as e:
            return None, f"loader failed: {type(e).__name__}"
    p = f"{UCI}{uid}/data.csv"
    if not os.path.exists(p):
        return None, None
    try:
        df = pd.read_csv(p, nrows=200)
    except Exception as e:
        return None, f"unreadable: {type(e).__name__}"
    return [str(c).strip() for c in df.columns], None


def main():
    rows, missing = [], []
    for uid, name, target, _prior, indev in PANEL:
        cols, err = columns_of(uid)
        if cols is None:
            missing.append((uid, name, err or "not downloaded"))
            continue
        # anonymised column names cannot be provenance-judged (PROTOCOL I2)
        import re as _re
        placeholder = _re.compile(r"^(attribute|attr|var|col|feature|[avxf])\s*_?\d+$", _re.I)
        n_anon = sum(1 for c in cols
                     if placeholder.match(c) or (len(c) <= 3 and c[:1].isalpha()))
        anon = n_anon > len(cols) * 0.6
        rows.append(dict(
            uci_id=uid, dataset=name, n_columns=len(cols),
            suggested_target=target,
            columns=" | ".join(cols),
            anonymised_names="YES - excluded by I2" if anon else "no",
            used_in_prompt_development="yes" if indev else "no",
            # ---- the coder fills these three in, blind --------------------
            has_label_derived="",
            which_columns="",
            reason=""))
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    npos = sum(1 for r in rows if r["anonymised_names"] == "no")
    print(f"{len(rows)} datasets written to {OUT}")
    print(f"  {npos} judgeable, {len(rows)-npos} flagged as anonymised (I2)")
    if missing:
        print(f"\n  {len(missing)} not available:")
        for uid, name, why in missing:
            print(f"    {uid:<5}{name:<34}{why}")
    print(f"\n{'dataset':<34}{'cols':>5}   first columns")
    for r in rows:
        print(f"  {r['dataset']:<32}{r['n_columns']:>5}   "
              f"{r['columns'][:88]}")


if __name__ == "__main__":
    main()
