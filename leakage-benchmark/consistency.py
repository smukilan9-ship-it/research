"""Do the deliverables agree with each other, and with the artefacts?

WHY

  The numbers in this project live in three places at once: an artefact on disk
  (kaggle_sieve.out, kaggle_anchor.log, memcheck_all.json), a working record
  (STRATUM_C.md, MEMCHECK_FINDINGS.md), and a paper-ready draft
  (STRATUM_C_SECTION.md, SECTION7_DRAFT.md, the scorecard).  A sweep
  finishes, two of the three get updated, and the third keeps a number nobody
  notices is stale.

  That already happened once in a worse form: a smoke test overwrote
  openml_candidates.jsonl with a 1-dataset fixture and the paper's figure became
  "2 across 1 datasets".  It was caught by diffing NUMBERS.txt, not by reading.
  This is the cheap standing version of that check.

WHAT IT DOES NOT DO

  It does not know what is correct.  It extracts the current value from the
  artefact, then looks for CONTRADICTING values in the prose -- a figure that
  should have moved and did not.  A clean run means "no stale number I know how
  to look for", never "the documents are right".
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
# Optional manuscript override: the 12-page PAPER_SHORT.md is built from
# the same NUMBERS.txt and must pass the same checks.
TARGET = sys.argv[1] if len(sys.argv) > 1 else "PAPER.md"
DOCS = [TARGET, "APPENDIX.md",
        "STRATUM_C.md", "STRATUM_C_SECTION.md",
        "WORKING_scorecard_superseded.md",
        "MEMCHECK_FINDINGS.md", "SECTION7_DRAFT.md", "MIRROR_PRECISION.md",
        "PENDING_PAPER_EDITS.md", "OVERNIGHT_SUMMARY.md", "SECTION3_DRAFT.md"]

# read() returns "" for a missing file, so a renamed deliverable would drop out
# of the sweep silently and this script would still print a clean run.  Name
# them here instead.
MISSING = [d for d in DOCS if not os.path.exists(HERE + d)]


def read(p):
    return open(HERE + p, errors="replace").read() if os.path.exists(HERE + p) else ""


def kaggle_truth():
    """Current Kaggle sweep figures, straight from the two logs."""
    out = {}
    s = read("kaggle_sieve.out")
    for key, pat in (("enriched", r"denominators are the ([\d,]+) datasets"),
                     ("sentences", r"^(\d+) surviving sentences"),
                     ("trigger_ds", r"surviving sentences across (\d+) datasets"),
                     ("synthetic", r"synthetic \(EXCLUDED\)\s+(\d+)"),
                     ("mirrors", r"re-upload of Stratum A/B\s+(\d+)"),
                     ("real", r"REAL and new\s+(\d+)")):
        m = re.search(pat, s, re.M)
        if m:
            out[key] = int(m.group(1).replace(",", ""))
    a = read("kaggle_anchor.log")
    for key, pat in (("readable", r"(\d+) datasets with a readable header"),
                     ("anchored", r"(\d+) datasets have a surviving sentence that names"),
                     ("rate", r"anchoring rate ([\d.]+)%")):
        m = re.search(pat, a)
        if m:
            out[key] = float(m.group(1)) if key == "rate" else int(m.group(1))
    return out


def memcheck_truth():
    p = HERE + "memcheck_all.json"
    if not os.path.exists(p):
        return {}
    d = json.load(open(p))
    return {m: len(v) for m, v in d.items()}


def main():
    k = kaggle_truth()
    if MISSING:
        print("=" * 74)
        print("DOCUMENTS NAMED IN THIS SCRIPT THAT ARE NOT ON DISK")
        print("=" * 74)
        for d in MISSING:
            print(f"  {d}   <- renamed or deleted; it is NOT being swept")
        print()
    print("=" * 74)
    print("KAGGLE SWEEP — current values from kaggle_sieve.out / kaggle_anchor.log")
    print("=" * 74)
    for key in ("enriched", "sentences", "trigger_ds", "synthetic", "mirrors",
                "real", "readable", "anchored", "rate"):
        if key in k:
            print(f"  {key:<12}{k[key]}")

    # Values that are WRONG now but were right at some earlier sweep size.  Each
    # is listed with the figure it should have become, so a hit is actionable
    # rather than merely alarming.
    stale = [
        (r"6,557", "8,693 enriched"),
        (r"8,006 enriched", "8,693 enriched"),
        (r"7,931|8,281|8,406|8,556", "8,693 enriched"),
        (r"235 datasets", "258 datasets with a surviving sentence"),
        (r"113 real|113 = 1\.41|1\.41%", "130 real and new = 1.50%"),
        (r"2\.94%", "2.97% raw trigger rate"),
        (r"28 of 100|28\.0%\*\*", "30 of 117 readable = 25.6%"),
        (r"21 \(\*\*28\.0", "30 (25.6%)"),
        (r"193 \(1\.31%\)", "258 (2.97%)"),
    ]
    print("\n" + "=" * 74)
    print("STALE-VALUE SCAN across the deliverables")
    print("=" * 74)
    # Some old figures are DELIBERATE: a working record saying "at 6,557
    # enriched, the state was X" is a dated snapshot, not a stale claim, and so
    # is "re-running the sieve over 8,006 datasets moved exactly three".  Those
    # lines carry the marker below.  Without an exemption the scan would report
    # the same three benign hits forever and stop being read, which is the only
    # way a checker like this actually fails.
    ASOF = "[as-of]"
    hits = 0
    for doc in DOCS:
        body = read(doc)
        if not body:
            continue
        lines = body.splitlines()
        for pat, should in stale:
            for m in re.finditer(pat, body):
                line = body[:m.start()].count("\n") + 1
                ctx = lines[line - 1].strip()
                # the marker may sit on the line or the one above it, so a
                # sentence wrapped across two lines can still be exempted
                window = " ".join(lines[max(0, line - 2):line + 1])
                if ASOF in window:
                    continue
                print(f"  {doc}:{line}  /{pat}/  -> should be {should}")
                print(f"      {ctx[:96]}")
                hits += 1
    if not hits:
        print("  no stale Kaggle figure found in any deliverable")

    print("\n" + "=" * 74)
    print("MEMCHECK — datasets per model on disk")
    print("=" * 74)
    mt = memcheck_truth()
    for m, n in sorted(mt.items(), key=lambda kv: -kv[1]):
        flag = "" if n == 15 else "   <- INCOMPLETE"
        print(f"  {n:>3}/15  {m}{flag}")
    print(f"  {len(mt)} of 14 roster models have any memcheck data")

    print("\n" + "=" * 74)
    print("RESPONSE CACHE — integrity")
    print("=" * 74)
    # Added after a container restart: every paper number is scored from these
    # files, so "are they all still readable" is worth one cheap check per pass.
    # A truncated JSON here would surface as a model silently losing cells, and
    # the scorer would report the smaller set without complaint.
    import collections
    per = collections.Counter()
    bad = []
    for f in glob.glob(HERE + "responses/*.json"):
        try:
            per[json.load(open(f)).get("model", "?")] += 1
        except Exception:
            bad.append(os.path.basename(f))
    print(f"  {sum(per.values())} cached cells across {len(per)} models; "
          f"{len(bad)} unreadable")
    for f in bad[:10]:
        print(f"    CORRUPT {f}")
    if bad:
        hits += 1

    print("\nA clean run means no stale figure of a KIND THIS SCRIPT KNOWS "
          "ABOUT.\nIt is not a proof that the documents are correct.")
    return 1 if hits else 0


def sieve_screen_migration():
    """Report the in-progress rename so a half-done one cannot ship.

    "sieve" is being renamed to "screen" section by section, because "screen"
    is the conventional word for what this instrument does and "sieve" was
    used 39 times in PAPER.md without ever being defined.  A rename done in
    pieces is a rename that gets forgotten in pieces, so the remaining count
    is printed on every run.  This does not fail: a paper mid-rename is not
    broken, it is unfinished, and the two states should not look alike.
    """
    import os as _os
    print("\n  sieve -> screen migration (in progress):")
    total = 0
    for f in ("PAPER.md", "PAPER_SHORT.md", "build_appendix.py",
              "REGISTERED_STRATUM_C.md"):
        if not _os.path.exists(HERE + f):
            continue
        n = open(HERE + f, encoding="utf-8", errors="replace").read().lower().count("sieve")
        total += n
        print(f"    {f:<26}{n:>4} remaining")
    if total == 0:
        print("    COMPLETE -- turn this into a failing check.")
    else:
        print(f"    {total} occurrences left; APPENDIX.md follows build_appendix.py.")


if __name__ == "__main__":
    rc = main()
    sieve_screen_migration()
    sys.exit(rc)
