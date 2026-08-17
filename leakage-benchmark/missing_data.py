"""Which raw data files are absent, and what each one is.

WHY THIS EXISTS RATHER THAN A FETCH SCRIPT

  MANIFEST.md originally told the reader to run `fetch_uci.py` and
  `fetch_stratc.py`.  Neither exists.  The instruction was written from memory
  of how the data *should* be restored rather than from the repository, which is
  the precise failure mode this project is about -- a plausible claim that
  nobody checked against the artefact.

  So this script does the part that can be verified: it reads the loaders in
  harness.py, reports which of their files are missing, and prints the recorded
  provenance for each.  It does NOT invent download URLs.  Several of these
  tables are behind click-through licences (Kaggle competition data, the Lending
  Club dump) and a script that guessed at their locations would fail silently at
  best and fetch the wrong revision at worst -- and a *different revision* of one
  of these tables is not the same corpus.

  Provenance for every dataset, including the exact file and its date where the
  archive versions its downloads, is in APPENDIX.md and PROTOCOL.md.
"""
import os, re, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"

# Where each loose CSV came from.  Recorded here because the loader knows the
# filename and nothing else, and a filename is not provenance.
SOURCE = {
    "diabetic.csv": "UCI 296, Diabetes 130-US hospitals 1999-2008",
    "loan.csv": "Lending Club accepted loans, via Kaggle (wordsforthewise)",
    "compas.csv": "ProPublica COMPAS analysis, compas-scores-two-years.csv",
    "ai4i2.csv": "UCI 601, AI4I 2020 Predictive Maintenance",
    "titanic3.csv": "Vanderbilt Biostatistics titanic3, the 1,309-row version",
    "e818b7de-cumulative_2026.08.08_07.34.36.csv":
        "NASA Exoplanet Archive, Kepler Objects of Interest cumulative table, "
        "downloaded 2026-08-08 (the archive re-issues this table; the date in "
        "the filename is load-bearing)",
}


def loader_files():
    """Every data file harness.py opens, read out of the source itself."""
    src = open(HERE + "harness.py", errors="replace").read()
    out = []
    for m in re.finditer(r'read_csv\(\s*(?:HERE|U)\s*\+\s*"([^"]+)"', src):
        out.append(m.group(1))
    return sorted(set(out))


def main():
    print("=" * 78)
    print("RAW DATA — what is missing from this checkout")
    print("=" * 78)
    print("  Excluded from git deliberately: these are byte-identical to what")
    print("  their archives serve, and redistributing them would triple the")
    print("  repository. See MANIFEST.md.\n")

    missing = 0
    for f in loader_files():
        for base in ("", "uci/"):
            if os.path.exists(HERE + base + f):
                state, mark = "present", "ok  "
                break
        else:
            state, mark = "MISSING", "--  "
            missing += 1
        print(f"  {mark}{f:<52}{state}")
        if state == "MISSING":
            print(f"      {SOURCE.get(f, 'provenance: see APPENDIX.md')}")

    ndir = 0
    for d in ("uci", "memcheck_csv", "stratc_data"):
        if not os.path.isdir(HERE + d):
            ndir += 1
            print(f"  --  {d + '/':<52}MISSING (directory)")
    if os.path.isdir(HERE + "ucimeta"):
        n = len(glob.glob(HERE + "ucimeta/*.json"))
        print(f"\n  ucimeta/ holds {n} UCI records including the id and name of")
        print(f"  every dataset the sweep touched, so uci/ can be refetched from")
        print(f"  the archive API without guessing which tables were used.")

    print(f"\n  {missing} loader file(s) and {ndir} directory(ies) absent.")
    if missing or ndir:
        print("  The five paper checkers do not need any of them -- they read")
        print("  NUMBERS.txt and responses/, both committed.  What needs raw")
        print("  data is verify_paper.py itself, and the baseline and downstream")
        print("  scripts it calls.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
