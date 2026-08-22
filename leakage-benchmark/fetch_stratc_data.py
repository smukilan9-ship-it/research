"""Restore stratc_data/ — the two Stratum C tables the artefact cannot carry.

WHY THIS FILE EXISTS

  §6.4's downstream arm scores three records.  One of them, cirrhosis, reads
  uci/878/data.csv and ships with the artefact.  The other two do not, and for
  a while nothing said so: stratc_specs pointed at stratc_data/, the directory
  was never committed and was never gitignored either, and STRATC_DOWNSTREAM.txt
  -- a frozen text file -- was the only record of what they scored.  That is
  exactly the position this paper criticises elsewhere: a number whose
  provenance you cannot re-derive.

  Klaverjas2018 is 164 MB and does not belong in a git history.  So the artefact
  carries what it can carry -- the URL, the SHA256, and this script -- and a
  reader restores the bytes in one command:

      python3 fetch_stratc_data.py
      python3 stratc_downstream.py > STRATC_DOWNSTREAM.txt

  bikesharing.csv is 1.1 MB and IS committed, so that arm needs nothing.

  The hashes below are of the files this paper's numbers were computed from.
  If an upstream copy changes, the check fails loudly rather than silently
  rescoring the paper.
"""
import hashlib, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
DEST = HERE + "stratc_data/"

FILES = [
    dict(name="Klaverjas2018.arff",
         url="https://openml.org/data/v1/download/20649164/Klaverjas2018.arff",
         sha256="8302e51857b7d56ec3e87bea5237d08b67819b57ef2d8464baede6410bb6bcea",
         bytes=164141737,
         note="OpenML dataset 41228; converted to klaverjas2018.csv below"),
    dict(name="bikesharing.csv",
         url="https://huggingface.co/datasets/t22000t/bike-sharing-tabular/"
             "resolve/main/hour.csv",
         sha256="e03de4ee4ef4dc376ac6e04bf829673c6269e8eba5c60fa121640fa2f829504f",
         bytes=1156736,
         note="committed with the artefact; fetched only if absent"),
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def arff_to_csv(src, dst):
    """Minimal ARFF reader: @attribute names, then rows, quoting preserved."""
    import csv, io, re
    cols, n, indata = [], 0, False
    with open(src, errors="replace") as fh, open(dst, "w", newline="") as out:
        w = csv.writer(out)
        for line in fh:
            s = line.strip()
            if not indata:
                if s.lower().startswith("@attribute"):
                    m = re.match(r"@attribute\s+(?:'([^']+)'|\"([^\"]+)\"|(\S+))",
                                 s, re.I)
                    cols.append(next(g for g in m.groups() if g))
                elif s.lower().startswith("@data"):
                    indata = True
                    w.writerow(cols)
            elif s and not s.startswith("%"):
                w.writerow(next(csv.reader(io.StringIO(s))))
                n += 1
    return len(cols), n


def main():
    os.makedirs(DEST, exist_ok=True)
    bad = 0
    for f in FILES:
        p = DEST + f["name"]
        if not os.path.exists(p):
            print(f"  fetching {f['name']}  ({f['bytes']:,} bytes)")
            urllib.request.urlretrieve(f["url"], p)
        got = sha(p)
        if got == f["sha256"]:
            print(f"  ok    {f['name']:<24} sha256 matches")
        else:
            print(f"  FAIL  {f['name']:<24} sha256 {got[:16]}… "
                  f"expected {f['sha256'][:16]}…")
            print(f"        The upstream copy has changed. The paper's numbers "
                  f"were computed from the expected one.")
            bad += 1

    arff = DEST + "Klaverjas2018.arff"
    csvp = DEST + "klaverjas2018.csv"
    if os.path.exists(arff) and not os.path.exists(csvp):
        full = DEST + "_klaverjas_full.csv"
        c, n = arff_to_csv(arff, full)
        print(f"  converted {c} columns, {n:,} rows")
        # stratc_specs records the sampling because every downstream number on
        # this dataset depends on it: "a fixed 100,000-row subsample at seed 0".
        # No script in the artefact performed it, so it is reconstructed here --
        # and the reconstruction is CHECKED, not assumed: with this subsample
        # the arm returns keep-all 0.8910, oracle 0.8945, delta -0.0035, which
        # is the frozen record to three decimals.  A different sampling would
        # not land there.
        import pandas as pd
        pd.read_csv(full).sample(n=100000, random_state=0).to_csv(csvp,
                                                                 index=False)
        os.remove(full)
        print(f"  subsampled 100,000 rows at seed 0 -> klaverjas2018.csv")
    print()
    if bad:
        print(f"  {bad} checksum failure(s).")
        return 1
    print("  stratc_data/ is restored; stratc_downstream.py can now run all "
          "three arms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
