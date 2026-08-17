"""Loaders for the ten expansion datasets, plus their real column lists.

The column list is not a convenience here -- it is what makes the paper's
evidence admissible.  PROTOCOL I5 requires that the column names in the
distributed file match the names in the evidence source.  The dictionary sieve
(harvest_dict.py) matched arbitrary word pairs and pulled author surnames out
of reference lists; anchoring it on THESE lists is the fix.

Nothing in this file assigns a label.  Which columns are label-derived is
decided by evidence in adjudicate_new.py, never here and never by us.
"""
import io, os, re, zipfile
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
UCI = HERE + "uci/"


def _names_file_cols(path, n_expected=None):
    """Parse a UCI .names file for an attribute list."""
    txt = open(path, errors="replace").read()
    cols = re.findall(r"^\s*\d+\)?\.?\s+([A-Za-z][\w\-\. ]{1,40}?)\s*[:\-]", txt, re.M)
    return [c.strip().replace(" ", "_").lower() for c in cols]


def load_bank():
    df = pd.read_csv(UCI + "222/bank/bank-full.csv", sep=";")
    return dict(name="BANK", file="uci/222/bank/bank-full.csv", df=df,
                target="y", columns=[c for c in df.columns if c != "y"])


def load_support2():
    df = pd.read_csv(UCI + "880/data.csv")
    tgt = "hospdead" if "hospdead" in df.columns else "death"
    return dict(name="SUPPORT2", file="uci/880/data.csv", df=df,
                target=tgt, columns=[c for c in df.columns if c != tgt])


def load_heartfailure():
    df = pd.read_csv(UCI + "519/heart_failure_clinical_records_dataset.csv")
    return dict(name="HEARTFAIL", file="uci/519/...csv", df=df,
                target="DEATH_EVENT",
                columns=[c for c in df.columns if c != "DEATH_EVENT"])


ECHO_COLS = ["survival", "still_alive", "age_at_heart_attack", "pericardial_effusion",
             "fractional_shortening", "epss", "lvdd", "wall_motion_score",
             "wall_motion_index", "mult", "name", "group", "alive_at_1"]


def load_echo():
    df = pd.read_csv(UCI + "38/echocardiogram.data", header=None,
                     names=ECHO_COLS, na_values="?", on_bad_lines="skip")
    return dict(name="ECHO", file="uci/38/echocardiogram.data", df=df,
                target="alive_at_1",
                columns=[c for c in ECHO_COLS if c not in ("alive_at_1", "name", "group")])


def load_bonemarrow():
    txt = open(UCI + "565/bone-marrow.arff", errors="replace").read()
    cols = [m.group(1) for m in re.finditer(r"@attribute\s+'?([\w\-]+)'?", txt, re.I)]
    body = txt.split("@data", 1)[1].strip().splitlines()
    rows = [l.split(",") for l in body if l.strip() and not l.startswith("%")]
    df = pd.DataFrame(rows, columns=cols).replace("?", np.nan)
    for c in df.columns:
        conv = pd.to_numeric(df[c], errors="coerce")
        # keep the numeric cast only if it did not destroy the column;
        # errors="ignore" was removed in pandas 2.x
        if conv.notna().sum() >= df[c].notna().sum():
            df[c] = conv
    return dict(name="BONEMARROW", file="uci/565/bone-marrow.arff", df=df,
                target="survival_status",
                columns=[c for c in cols if c != "survival_status"])


WPBC_COLS = (["id", "outcome", "time"] +
             [f"{s}_{i}" for s in ("mean", "se", "worst")
              for i in ("radius", "texture", "perimeter", "area", "smoothness",
                        "compactness", "concavity", "concave_points", "symmetry",
                        "fractal_dim")] + ["tumor_size", "lymph_status"])


def load_wpbc():
    df = pd.read_csv(UCI + "16/wpbc.data", header=None, names=WPBC_COLS, na_values="?")
    return dict(name="WPBC", file="uci/16/wpbc.data", df=df, target="outcome",
                columns=[c for c in WPBC_COLS if c not in ("outcome", "id")])


def load_credit():
    df = pd.read_excel(UCI + "350/default of credit card clients.xls", header=1)
    df.columns = [str(c).strip() for c in df.columns]
    tgt = [c for c in df.columns if "default" in c.lower()][0]
    return dict(name="CREDIT", file="uci/350/...xls", df=df, target=tgt,
                columns=[c for c in df.columns if c not in (tgt, "ID")])


def load_actg():
    df = pd.read_csv(UCI + "890/data.csv")
    tgt = "cid" if "cid" in df.columns else df.columns[-1]
    return dict(name="ACTG175", file="uci/890/data.csv", df=df, target=tgt,
                columns=[c for c in df.columns if c not in (tgt, "pidnum")])


def load_polish():
    df = pd.read_csv(UCI + "365/data.csv")
    tgt = "class" if "class" in df.columns else df.columns[-1]
    return dict(name="POLISH", file="uci/365/data.csv", df=df, target=tgt,
                columns=[c for c in df.columns if c != tgt])


POSTOP_COLS = ["l_core", "l_surf", "l_o2", "l_bp", "surf_stbl", "core_stbl",
               "bp_stbl", "comfort", "decision"]


def load_postop():
    df = pd.read_csv(UCI + "82/post-operative.data", header=None,
                     names=POSTOP_COLS, na_values="?", on_bad_lines="skip")
    return dict(name="POSTOP", file="uci/82/post-operative.data", df=df,
                target="decision",
                columns=[c for c in POSTOP_COLS if c != "decision"])


CTG_TARGET = "NSP"


def load_ctg():
    """Cardiotocography (UCI 193).  Target NSP = fetal state (1 normal,
    2 suspect, 3 pathologic).  CLASS is the FHR morphologic pattern the
    obstetricians assigned; the manifest's selection note suspects it is why a
    record is labelled suspect or pathologic.  Whether that is true is decided
    by the papers, not here."""
    df = pd.read_csv(UCI + "193/data.csv")
    df.columns = [c.strip() for c in df.columns]
    return dict(name="CTG", file="uci/193/data.csv", df=df, target=CTG_TARGET,
                columns=[c for c in df.columns if c != CTG_TARGET])


def load_cervical():
    """Cervical Cancer Risk Factors (UCI 383).  Target Biopsy.  Hinselmann,
    Schiller and Citology are the other three screening tests."""
    df = pd.read_csv(UCI + "383/data.csv")
    df.columns = [c.strip() for c in df.columns]
    return dict(name="CERVICAL", file="uci/383/data.csv", df=df, target="Biopsy",
                columns=[c for c in df.columns if c != "Biopsy"])


def load_steel():
    """Steel Plates Faults (UCI 198).  Target Other_Faults, which is defined as
    none of the six named fault modes -- structurally the same shape as AI4I."""
    df = pd.read_csv(UCI + "198/data.csv")
    df.columns = [c.strip() for c in df.columns]
    return dict(name="STEEL", file="uci/198/data.csv", df=df, target="Other_Faults",
                columns=[c for c in df.columns if c != "Other_Faults"])


def load_mi():
    """Myocardial Infarction Complications (UCI 579).  Twelve outcome columns;
    LET_IS (lethal outcome cause) is the manifest's suspected reason column.
    Target is ZSN (chronic heart failure) so that LET_IS is a feature rather
    than the label -- PROTOCOL 2's (column, target) relativity in practice."""
    df = pd.read_csv(UCI + "579/data.csv")
    df.columns = [c.strip() for c in df.columns]
    tgt = "ZSN"
    drop = {tgt, "ID"}
    return dict(name="MI", file="uci/579/data.csv", df=df, target=tgt,
                columns=[c for c in df.columns if c not in drop])


NEW = dict(bank=load_bank, support2=load_support2, heartfail=load_heartfailure,
           echo=load_echo, bonemarrow=load_bonemarrow, wpbc=load_wpbc,
           credit=load_credit, actg175=load_actg, polish=load_polish,
           postop=load_postop, ctg=load_ctg, cervical=load_cervical,
           steel=load_steel, mi=load_mi)

# maps the PDF filename slug to the loader key, so evidence joins to data
SLUG = {
    "bankmarketing": "bank",
    "heartfailureclinicalrecords": "heartfail",
    "echocardiogram": "echo",
    "bonemarrowtransplantchildren": "bonemarrow",
    "breastcancerwisconsinprognostic": "wpbc",
    "defaultofcreditcardclients": "credit",
    "aidsclinicaltrialsactg175": "actg175",
    "polishcompaniesbankruptcy": "polish",
    "postoperativepatient": "postop",
    "diabetes130ushospitals": None,      # already in the benchmark
    # ---- transfer-test batch: REASON-subtype datasets, never inspected ----
    "cardiotocography": "ctg",
    "cervicalcancerrisk": "cervical",
    "steelplatesfaults": "steel",
    "myocardialinfarction": "mi",
}


if __name__ == "__main__":
    ok = 0
    for k, fn in NEW.items():
        try:
            s = fn()
            n = len(s["df"])
            print(f"  {s['name']:<12}{n:>8} rows{len(s['columns']):>5} cols   "
                  f"target={s['target']:<18}{', '.join(s['columns'][:5])}...")
            ok += 1
        except Exception as e:
            print(f"  {k:<12}LOAD FAILED: {type(e).__name__}: {str(e)[:90]}")
    print(f"\n{ok}/{len(NEW)} datasets load")
