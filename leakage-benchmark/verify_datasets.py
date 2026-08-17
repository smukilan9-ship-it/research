"""Do the shipped frames still reproduce the corpus the paper reports?

WHY THIS IS A CHECKER AND NOT A NOTE IN THE README

  datasets/ is a copy.  Copies drift: a frame gets re-exported after a loader
  changes, or a file is edited by hand, and nothing says so.  Every other
  artefact in this project is checked against NUMBERS.txt, and there is no
  reason for the data to be the exception -- especially since the data is the
  one artefact where a silent change invalidates every number at once.

  So this reads datasets/ WITHOUT importing the loaders, and asks whether what
  shipped agrees with section 1 of NUMBERS.txt on three things: how many columns
  each dataset contributes, how many of them are positive, and the stratum
  totals.  It also re-hashes each frame against MANIFEST.csv, which is what
  makes "the actual data we used" checkable rather than asserted.

  Not importing the loaders is the point.  A check that rebuilt the frames from
  the same code that exported them would agree with itself by construction and
  tell you nothing.
"""
import os, re, sys, csv, hashlib

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
DATA = HERE + "datasets/"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def numbers_corpus():
    """Per-dataset (cols, pos) and the stratum totals, from NUMBERS section 1."""
    txt = open(HERE + "NUMBERS.txt", errors="replace").read()
    seg = txt[txt.index("1. CORPUS"):txt.index("2. EVIDENCE RECORDS")]
    per = {}
    for m in re.finditer(r"^([A-Z][A-Z0-9]+)\s+(\d+)\s+(\d+)\s", seg, re.M):
        per[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    tot = [(int(a), int(b)) for a, b in
           re.findall(r"^TOTAL\s+(\d+)\s+(\d+)", seg, re.M)]
    return per, tot


def main():
    print("=" * 78)
    print("DATASETS — do the shipped frames match the corpus NUMBERS.txt reports?")
    print("=" * 78)
    if not os.path.isdir(DATA):
        print("  datasets/ not present"); return 1

    per, tot = numbers_corpus()
    man = list(csv.DictReader(open(DATA + "MANIFEST.csv")))
    bad = 0

    print(f"  {'dataset':<13}{'str':>4}{'cols':>7}{'pos':>5}{'rows':>9}"
          f"{'sha256':>10}   vs NUMBERS.txt")
    for r in man:
        name = r["dataset"]
        cols, pos = int(r["columns"]), int(r["positives"])
        want = per.get(name)
        path = DATA + name + "/data.csv.gz"

        if not os.path.exists(path):
            print(f"  {name:<13}  FRAME MISSING"); bad += 1; continue
        digest_ok = sha(path) == r["sha256"]

        if want is None:
            verdict, ok = "not in NUMBERS §1", False
        elif (cols, pos) == want:
            verdict, ok = "ok", True
        else:
            verdict, ok = f"MISMATCH — NUMBERS says {want[0]} cols {want[1]} pos", False
        if not ok or not digest_ok:
            bad += 1
        print(f"  {name:<13}{r['stratum']:>4}{cols:>7}{pos:>5}{int(r['rows']):>9}"
              f"{'ok' if digest_ok else 'ALTERED':>10}   {verdict}")

    for label, idx, want in (("Stratum A", "A", tot[0] if tot else None),
                             ("Stratum B", "B", tot[1] if len(tot) > 1 else None)):
        got_c = sum(int(r["columns"]) for r in man if r["stratum"] == idx)
        got_p = sum(int(r["positives"]) for r in man if r["stratum"] == idx)
        ok = want == (got_c, got_p)
        bad += 0 if ok else 1
        print(f"\n  {label} total: {got_c} columns, {got_p} positives"
              f"{'' if ok else f'   MISMATCH — NUMBERS says {want}'}")

    c = sum(int(r["columns"]) for r in man)
    p = sum(int(r["positives"]) for r in man)
    print(f"  COMBINED: {len(man)} datasets, {c} columns, {p} positives")
    combined_ok = f"{len(man)} datasets, {c} columns, {p} positives" in \
        open(HERE + "NUMBERS.txt", errors="replace").read()
    if not combined_ok:
        print("  MISMATCH — NUMBERS.txt does not state this combined line")
        bad += 1

    bad += check_mechanisms()

    print(f"\n  {bad} problem(s).")
    if not bad:
        print("  The shipped frames reproduce the corpus the paper reports,")
        print("  and every file hashes to what MANIFEST.csv recorded.")
    return 1 if bad else 0


def check_mechanisms():
    """Do the schemas' ground-truth tables agree with the corpus subtypes?

    WHY THIS CHECK EXISTS

      Column counts, positive counts and SHA256s all passed while 28 of the
      corpus's 68 positives carried the WRONG MECHANISM in their shipped
      schema.  `export_datasets.py` resolved subtypes through `subtypes.py`,
      which covers Stratum A only, and wrote `or 'CONTESTED'` when that
      returned nothing -- so every Stratum-B positive shipped as CONTESTED.
      `NUMBERS.txt` records **two** CONTESTED in the whole corpus.

      Nothing caught it because a mechanism is not a count and not a hash, and
      because `verify_paper.py` warns about exactly this trap in a comment that
      the exporter did not read: "Stratum B's subtype codes live in
      explicit_specs, not subtypes.py."

      It matters because §6.2 -- the definitional finding, the paper's most
      interesting result -- rests entirely on the subtype partition. A reader
      taking `datasets/` as the artefact of record would compute different
      subtype recalls than the paper reports.
    """
    print("\n  --- schema ground-truth mechanisms vs the corpus")
    try:
        import verify_paper as V
    except Exception as e:
        # A check that cannot run is a FAILED check, not a passed one.  The
        # first version of this returned 0 here and printed "SKIPPED", so a
        # missing numpy turned a real 2-problem result into a clean exit --
        # the checker reporting success precisely when it had stopped looking.
        # That is the defect `prose_pins.py` was written to prevent one layer
        # down ("a missing pattern is a FAILURE, not a skip"), reproduced here.
        print(f"  CANNOT RUN — verify_paper will not import: {str(e)[:70]}")
        print("  Reporting this as a FAILURE. The mechanisms are unchecked, "
              "which is not\n  the same as correct. Install the scientific "
              "stack and re-run.")
        return 1
    bad = 0
    for name in sorted(manifest_names()):
        p = f"{HERE}datasets/{name}/schema.md"
        if not os.path.isfile(p):
            continue
        txt = open(p, errors="replace").read()
        shipped = dict(re.findall(r"^\|\s*`([^`]+)`\s*\|\s*([A-Z]+)\s*\|",
                                  txt.split("## Ground truth", 1)[-1], re.M))
        wrong = {c: (got, V.subtype(name, c)) for c, got in shipped.items()
                 if V.subtype(name, c) and got != V.subtype(name, c)}
        if wrong:
            bad += 1
            ex = list(wrong.items())[:2]
            print(f"  {name:<12}{len(wrong):>3} of {len(shipped)} mechanisms "
                  f"disagree with the corpus, e.g. "
                  + "; ".join(f"`{c}` shipped {g}, corpus says {w}"
                              for c, (g, w) in ex))
        else:
            print(f"  {name:<12}{len(shipped):>3} mechanism(s) ok")
    if bad:
        print(f"  -> regenerate with `python3 export_datasets.py` "
              f"(needs the upstream tables).")
    return bad


def manifest_names():
    import csv as _csv
    with open(HERE + "datasets/MANIFEST.csv", newline="") as fh:
        return [r["dataset"] for r in _csv.DictReader(fh)]


if __name__ == "__main__":
    sys.exit(main())
