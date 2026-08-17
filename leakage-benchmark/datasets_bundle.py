"""Build a spec bundle from `datasets/` when the upstream loader files are absent.

WHY THIS IS A FALLBACK AND NOT A REPLACEMENT

  The canonical path is `runner.spec_bundle` -> `harness`/`newdata`/
  `explicit_specs`, which read the upstream archive files.  That path is
  authoritative and stays authoritative: it is the code every number in the
  paper was computed by.

  But those upstream files are deliberately not committed (`MANIFEST.md`), and
  UCI no longer serves several of them in their original layout -- the modern
  `static/public/<id>/data.csv` endpoint returns a NORMALISED frame that does
  not reproduce the corpus.  Measured, not assumed: ECHO overlaps 6 of its 15
  column names, because its loader reads a headerless file and supplies the
  names itself.  Fetching from there would silently build a different corpus,
  which is precisely what `MANIFEST.md` warns about.

  `datasets/` closes that gap.  Its own README defines each `data.csv.gz` as
  "the frame the bundle resolved to -- post-preprocessing, corpus columns only,
  plus the target", and `verify_datasets.py` checks all fifteen against
  `NUMBERS.txt` and a per-file SHA256.  So the export IS the resolved bundle,
  and rebuilding a bundle from it is a restoration rather than a substitution.

WHAT THIS NEEDS TO PRODUCE, AND WHAT IT DOES NOT

  A prompt at C1/C2/C6/C9 -- the conditions the paper's claims rest on -- needs
  the column names, the target and (for C2) the prediction point.  All three are
  in the export.  It does NOT reconstruct:

    description   used only by C3/C5.  Left empty, and `runner.py` already
                  SKIPS C3 loudly rather than silently duplicating C2 when a
                  description is missing.
    sample rows   used only by C4, the ablation.  Read from data.csv.gz on
                  demand, so C4 works too.

SELF-CHECKING, BECAUSE A SILENT FALLBACK IS THE DANGEROUS KIND

  Every bundle built here is checked against `datasets/MANIFEST.csv` -- column
  count, positive count, target name -- and raises rather than returning a
  bundle that disagrees.  A restoration that quietly differed from the corpus
  would be worse than no restoration, because the run would look fine and the
  cells would not be comparable with the 1,812 already cached.
"""
import csv, gzip, os, re

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
DATA = HERE + "datasets/"


def available():
    """True if the export is present and usable."""
    return os.path.isfile(DATA + "MANIFEST.csv")


def manifest():
    """dataset -> row, from datasets/MANIFEST.csv."""
    with open(DATA + "MANIFEST.csv", newline="") as fh:
        return {r["dataset"]: r for r in csv.DictReader(fh)}


def _schema(name):
    return open(DATA + name + "/schema.md", errors="replace").read()


def _prediction_point(txt):
    m = re.search(r"^\-\s+\*\*Prediction point\*\*:\s*(.+?)\s*$", txt, re.M)
    return m.group(1).strip() if m else ""


def _positives(txt):
    """Columns in the schema's ground-truth table, with their mechanism.

    The table is the export's statement of which columns are coded positive.
    Parsed rather than inferred from the frame, because 'legitimate by default'
    means a column's ABSENCE from this table is the ground truth for it.
    """
    out = {}
    body = txt.split("## Ground truth", 1)
    if len(body) < 2:
        return out
    for m in re.finditer(r"^\|\s*`([^`]+)`\s*\|\s*([A-Z]+)\s*\|", body[1], re.M):
        out[m.group(1)] = m.group(2)
    return out


# Record-file dataset_id -> corpus name.  The record files predate the corpus
# naming convention; verify_paper.py carries the same map and it is repeated
# here rather than imported, because verify_paper imports THIS module in its
# own fallback and the cycle would not resolve.
_ID2NAME = {"uci579_myocardial_infarction": "MI",
            "uci211_communities_crime_unnorm": "CRIME",
            "uci320_student_performance": "STUDENT"}


def stratum_b_subtypes():
    """{(dataset, column): mechanism} for Stratum B, from the EVIDENCE RECORDS.

    NOT from `datasets/*/schema.md`, and the difference matters.  The shipped
    schemas label every Stratum-B positive `CONTESTED`, because
    `export_datasets.py` resolves mechanisms through `subtypes.py` -- which
    covers Stratum A only -- and then writes `or 'CONTESTED'` when it gets
    nothing back.  That converts "I do not know" into a confident wrong answer
    for 28 of the corpus's 68 positives.  `NUMBERS.txt` says the whole corpus
    holds **two** CONTESTED; CRIME is REASON 8 + TIMING 9 and MI is
    CONSEQUENCE 11.

    `records_explicit.jsonl` is committed, needs no raw data, and is where the
    codes actually live.  It is the source here for that reason.
    """
    import json
    out = {}
    p = HERE + "records_explicit.jsonl"
    if not os.path.isfile(p):
        return out
    for line in open(p, errors="replace"):
        r = json.loads(line)
        ds = _ID2NAME.get(r.get("dataset_id"), r.get("dataset_id"))
        if r.get("column") and r.get("subtype"):
            out[(ds, r["column"])] = r["subtype"]
    return out


def subtypes(name):
    """{column: mechanism} for one dataset.

    Stratum B is taken from the evidence records (see `stratum_b_subtypes`);
    Stratum A from the schema, where the export is correct because
    `subtypes.py` does cover it.
    """
    b = {c: st for (d, c), st in stratum_b_subtypes().items() if d == name}
    return b or _positives(_schema(name))


def build(name, want_sample=False):
    """A spec bundle for one dataset, from the export.

    `name` is the CORPUS name (KOI, SUPPORT2, CRIME), not the runner's
    lowercase key.
    """
    if not available():
        raise RuntimeError("datasets/ is not present; nothing to restore from")
    man = manifest()
    if name not in man:
        raise RuntimeError(f"{name} is not in datasets/MANIFEST.csv")
    row = man[name]
    target = row["target"]

    with gzip.open(DATA + name + "/data.csv.gz", "rt", errors="replace") as fh:
        rdr = csv.reader(fh)
        header = [c.strip() for c in next(rdr)]
        sample = []
        if want_sample:
            for i, r in enumerate(rdr):
                if i >= 5:
                    break
                sample.append(dict(zip(header, r)))

    # "corpus columns only, plus the target" -- so the feature list is the
    # header minus the target, in the frame's own order.
    columns = [c for c in header if c != target]
    txt = _schema(name)
    pos = _positives(txt)
    truth = {c: (c in pos) for c in columns}

    # ---- the checks that make this a restoration rather than a guess -------
    exp_cols, exp_pos = int(row["columns"]), int(row["positives"])
    if len(columns) != exp_cols:
        raise RuntimeError(
            f"{name}: rebuilt {len(columns)} columns, MANIFEST.csv says "
            f"{exp_cols}. Refusing to return a bundle that disagrees with the "
            f"corpus.")
    if sum(truth.values()) != exp_pos:
        missing = sorted(set(pos) - set(columns))
        raise RuntimeError(
            f"{name}: rebuilt {sum(truth.values())} positives, MANIFEST.csv "
            f"says {exp_pos}."
            + (f" Coded columns absent from the frame: {missing}" if missing
               else ""))
    if target in columns:
        raise RuntimeError(f"{name}: target {target!r} is in the feature list")

    return dict(name=name, columns=columns, truth=truth, target=target,
                prediction_point=_prediction_point(txt), description="",
                sample=sample, restored_from="datasets/")


def main():
    print("=" * 78)
    print("DATASETS -> BUNDLES — can every dataset be restored from the export?")
    print("=" * 78)
    if not available():
        print("  datasets/ not present")
        return 1
    bad = 0
    print(f"  {'dataset':<12}{'cols':>6}{'pos':>5}  {'target':<20}prediction point")
    for name in manifest():
        try:
            b = build(name)
            print(f"  {name:<12}{len(b['columns']):>6}{sum(b['truth'].values()):>5}  "
                  f"{b['target']:<20}{b['prediction_point'][:34]}")
        except Exception as e:
            print(f"  {name:<12}FAILED: {e}")
            bad += 1
    print(f"\n  {bad} failure(s).")
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
