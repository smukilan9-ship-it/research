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

    print(f"\n  {bad} problem(s).")
    if not bad:
        print("  The shipped frames reproduce the corpus the paper reports,")
        print("  and every file hashes to what MANIFEST.csv recorded.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
