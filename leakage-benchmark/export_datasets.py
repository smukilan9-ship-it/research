"""Export the exact frame each dataset resolved to, plus what the models saw.

WHY THE FRAME AND NOT THE SOURCE FILE

  "The dataset the models saw" is ambiguous in a way that matters here, and this
  script resolves the ambiguity by shipping both halves separately.

  The models never saw values.  At C1 -- the primary condition, and the one the
  headline rests on -- a model receives COLUMN NAMES AND A TARGET, nothing else.
  Only C4 shows five sample rows, and C4 is the ablation.  So the thing the
  models literally saw is `schema.md`, and it is small enough to read.

  The frame is what everything ELSE rests on: the ground truth, the downstream
  forests, the baselines, every F1 in the paper.  It is NOT the source file --
  loaders drop dead columns, coerce types, and select the corpus columns -- so
  shipping the upstream CSV would ship something that reproduces none of the
  numbers.  A reader who wants to check a downstream delta needs this frame, and
  a reader who wants to re-run a model needs the schema.

WHY A CHECKSUM MANIFEST

  One of these tables is re-issued by its archive under the same filename: NASA
  regenerates the KOI cumulative table, and "the same dataset" fetched next year
  is a different corpus with the same name.  A SHA256 per frame is what makes
  "the actual dataset we used" a checkable claim instead of a hopeful one.

WHAT IS DELIBERATELY NOT DEDUPLICATED

  DIABETES appears in the corpus as one dataset; harness.py also carries a
  `diabetes_pure` loader used elsewhere.  Only the corpus bundle is exported,
  because that is the one the paper scores.
"""
import os, sys, json, hashlib, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import pandas as pd
import runner as RN, harness as H
# NOT `from subtypes import subtype`.  That map covers STRATUM A ONLY, and
# resolving a Stratum-B column through it returns None -- which this file then
# wrote out as `CONTESTED`, turning "I do not know" into a confident wrong
# answer for 28 of the corpus's 68 positives.  `verify_paper.subtype` is the
# resolver that consults BOTH: explicit_specs (or the evidence records) for
# Stratum B, subtypes.py for Stratum A.  It is the same function every table
# in the paper is computed with, which is the point.
from verify_paper import subtype

OUT = HERE + "datasets/"

# Provenance and redistribution status, recorded per dataset because a reader
# who wants to reuse one needs to know where it came from, and because two of
# them carry terms we should not silently paper over.
PROV = {
    "KOI": ("NASA Exoplanet Archive, Kepler Objects of Interest cumulative "
            "table, retrieved 2026-08-08", "public domain (NASA)"),
    "DIABETES": ("UCI 296 — Diabetes 130-US hospitals for years 1999-2008",
                 "CC BY 4.0"),
    "LC": ("Lending Club accepted loans, via Kaggle (wordsforthewise)",
           "CHECK BEFORE REDISTRIBUTING — Kaggle terms"),
    "COMPAS": ("ProPublica, compas-scores-two-years.csv", "public"),
    "AI4I": ("UCI 601 — AI4I 2020 Predictive Maintenance", "CC BY 4.0"),
    "TITANIC": ("Vanderbilt Biostatistics titanic3 (1,309 rows)", "public"),
    "BANK": ("UCI 222 — Bank Marketing", "CC BY 4.0"),
    "SUPPORT2": ("UCI 880 — SUPPORT2", "CC BY 4.0"),
    "BONEMARROW": ("UCI 565 — Bone marrow transplant: children", "CC BY 4.0"),
    "HEARTFAIL": ("UCI 519 — Heart failure clinical records", "CC BY 4.0"),
    "STEEL": ("UCI 198 — Steel Plates Faults", "CC BY 4.0"),
    "ECHO": ("UCI 38 — Echocardiogram", "CC BY 4.0"),
    "MI": ("UCI 579 — Myocardial infarction complications", "CC BY 4.0"),
    "CRIME": ("UCI 211 — Communities and Crime Unnormalized", "CC BY 4.0"),
    "STUDENT": ("UCI 320 — Student Performance", "CC BY 4.0"),
}


def frame(key, bundle):
    """The dataframe the bundle was built from, by the same path the bundle took."""
    if key in RN.EXPLICIT:
        import explicit_specs as ES
        m = ES.SPECS[key]
        df = pd.read_csv(f"{HERE}uci/{m['uci']}/data.csv")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    if key in RN.EXPANSION or key in RN.TRANSFER:
        import newdata as ND
        return ND.NEW[key]()["df"]
    return H.LOADERS[key]()["df"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_schema(d, b, df, cols, tgt, stratum):
    """What a model actually received, in the order it received it."""
    pos = [c for c in cols if b["truth"].get(c)]
    L = []
    L.append(f"# {b['name']} — schema\n")
    L.append(f"**Stratum {stratum}.** {len(cols)} columns, {len(pos)} documented "
             f"positive{'s' if len(pos) != 1 else ''}, {len(df):,} rows.\n")
    L.append(f"- **Target**: `{tgt}`")
    L.append(f"- **Prediction point**: {b.get('prediction_point') or '(not set)'}")
    src, lic = PROV.get(b["name"], ("(unrecorded)", "(unrecorded)"))
    L.append(f"- **Source**: {src}")
    L.append(f"- **Licence**: {lic}\n")
    L.append("## What the model saw\n")
    L.append("At **C1**, the primary condition: the column names below and the "
             "target, in this order. No values, no descriptions, no row counts. "
             "Column order is shuffled per seed; this is the canonical order.\n")
    L.append("```")
    L.append(", ".join(str(c) for c in cols))
    L.append("```\n")
    L.append("At **C4** only, five sample rows are added — that condition is the "
             "ablation, not the headline.\n")
    L.append("## Ground truth\n")
    if pos:
        L.append("| column | mechanism |")
        L.append("|---|---|")
        for c in pos:
            st = subtype(b["name"], c)
            if not st:
                # Never invent a mechanism.  `or 'CONTESTED'` sat here and
                # relabelled every unresolved column as the corpus's rarest
                # category -- NUMBERS.txt holds two CONTESTED in total, and
                # this shipped thirty.  An unknown code is a bug in the
                # resolver, and a bug must stop the export rather than be
                # written into an artefact a reader will trust.
                raise RuntimeError(
                    f"{b['name']}.{c}: no subtype resolved. Do not guess -- "
                    f"check that verify_paper.subtype() can see this "
                    f"stratum's codes.")
            L.append(f"| `{c}` | {st} |")
    else:
        L.append("No documented positives. This dataset is in the corpus "
                 "precisely because a transfer set of only-positive tables "
                 "would be a different test.")
    L.append("\nEvery other column is coded **legitimate by default** — no "
             "admissible record was found for it. Precision is therefore a "
             "lower bound: a model flagging something real but undocumented is "
             "scored wrong. Quotations licensing each positive are in "
             "`../APPENDIX.md`.\n")
    open(d + "schema.md", "w").write("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    keys = [(k, "A") for k in RN.ALLSETS] + [(k, "B") for k in RN.EXPLICIT]
    for key, stratum in keys:
        b = RN.spec_bundle(key)
        name = b["name"]
        df = frame(key, b)
        tgt = b["target"]
        cols = [c for c in b["columns"] if c in df.columns]
        missing = [c for c in b["columns"] if c not in df.columns]
        keep = cols + ([tgt] if tgt in df.columns and tgt not in cols else [])
        sub = df[keep]

        d = OUT + name + "/"
        os.makedirs(d, exist_ok=True)
        path = d + "data.csv.gz"
        sub.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})
        write_schema(d, b, sub, cols, tgt, stratum)

        npos = sum(1 for c in cols if b["truth"].get(c))
        rows.append(dict(dataset=name, stratum=stratum, rows=len(sub),
                         columns=len(cols), positives=npos, target=tgt,
                         sha256=sha(path),
                         bytes=os.path.getsize(path)))
        flag = f"  MISSING FROM FRAME: {missing}" if missing else ""
        print(f"  {name:<12}{stratum}  {len(sub):>7} x {len(cols):>3}  "
              f"{npos:>2} pos  {os.path.getsize(path)/1048576:>6.2f} MB{flag}")

    man = pd.DataFrame(rows)
    man.to_csv(OUT + "MANIFEST.csv", index=False)
    print(f"\n  {len(man)} datasets, {man.columns.sum() if False else man['columns'].sum()} "
          f"columns, {man['positives'].sum()} positives, "
          f"{man['bytes'].sum()/1048576:.1f} MB total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
