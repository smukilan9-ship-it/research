"""Three-way check on SUBMISSION.md: the file, the literals, and reality.

WHY THIS EXISTS

  SUBMISSION.md is the cover sheet.  It tells a reviewer what the submission
  contains and what each checker covers, and until now NOTHING READ IT.  Every
  other deliverable is pinned to a checker; this one described the checkers and
  was itself unchecked, which is the one place a stale number is most embarrassing.

  It had drifted, exactly as you would predict:

      "11 sections, 22.8k words"    the paper had grown to 24.2k
      "Then eleven checkers"        the list below it had thirteen entries
      "prose_pins.py    28 pins"    prose_pins.py reports 30
      "verify_section8.py 75 claims" verify_section8.py reports 76

  None of these change a result.  All four make the cover sheet wrong about
  the thing a reviewer would check first, and the paper's own thesis is that a
  number whose provenance you cannot state is a number you cannot defend.

HOW IT CHECKS

  Three ways, because two is not enough:

    1. the literal is PRESENT in SUBMISSION.md   -- catches the prose drifting
       away from this checker
    2. the value RECOMPUTES from the artefact    -- catches reality drifting
       away from the prose
    3. for the three checkers that publish a count, the count is taken by
       RUNNING them and requiring their own summary line verbatim -- not by
       reading a number out of a file that could be stale in the same way

  There is no regex anywhere in this file.  Every check is an exact substring
  containment, a directory listing, or an integer comparison.  A pattern that
  matches nothing looks identical to a pattern that matches everything, and
  this repository has already been bitten by that twice.

WORD-COUNT ROUNDING

  SUBMISSION.md states word counts to mixed precision -- "24.2k", "7.2k",
  "46k" -- and the true counts are 24267, 7267, 45987.  The first two are
  truncated at one decimal, the third is rounded at zero.  Rather than pick
  one rule and force the prose to it, this accepts EITHER truncation or
  round-half-up at the precision the figure is stated to, and says so here so
  the tolerance is declared rather than discovered.
"""

import os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SUB  = os.path.join(ROOT, "SUBMISSION.md")

with open(SUB, encoding="utf-8") as fh:
    TEXT = fh.read()

FAILURES = []
CHECKED  = 0


def ok(label, detail=""):
    global CHECKED
    CHECKED += 1
    print(f"  ok       {label:<44} {detail}")


def bad(label, detail):
    global CHECKED
    CHECKED += 1
    FAILURES.append((label, detail))
    print(f"  FAIL     {label:<44} {detail}")


def stated(label, literal):
    """1. the literal must appear in SUBMISSION.md."""
    if literal in TEXT:
        return True
    bad(label, f"SUBMISSION.md does not contain {literal!r}")
    return False


def words(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return len(fh.read().split())


def kfig_matches(actual, stated_k, decimals):
    """Accept truncation OR round-half-up at the stated precision."""
    scale = 10 ** decimals
    v = actual / 1000.0
    trunc = int(v * scale) / scale
    rounded = int(v * scale + 0.5) / scale
    return stated_k in (trunc, rounded)


def check_wordcount(path, literal, stated_k, decimals):
    label = f"{path} word count"
    if not stated(label, literal):
        return
    actual = words(path)
    if kfig_matches(actual, stated_k, decimals):
        ok(label, f"{actual:,} words -> {literal}")
    else:
        bad(label, f"SUBMISSION.md says {literal}; {path} has {actual:,} words")


print("\n=== SUBMISSION.md, checked against the artefact it describes ===\n")

# ---------------------------------------------------------------- section 1
check_wordcount("PAPER.md",       "11 sections, 25.7k words", 25.7, 1)
check_wordcount("APPENDIX.md",    "48k words, appendices A–L", 48.0, 0)
check_wordcount("PAPER_SHORT.md", "7.4k-word condensation", 7.4, 1)

# PAPER.md numbered sections
label = "PAPER.md numbered sections"
if stated(label, "11 sections"):
    n = 0
    for line in open(os.path.join(ROOT, "PAPER.md"), encoding="utf-8"):
        if line.startswith("## ") and line[3:4].isdigit():
            n += 1
    ok(label, f"{n} found") if n == 11 else bad(label, f"says 11, found {n}")

# APPENDIX.md letters must run A..L with no gaps
label = "APPENDIX.md appendix letters"
letters = []
for line in open(os.path.join(ROOT, "APPENDIX.md"), encoding="utf-8"):
    s = line.lstrip("#")
    if line.startswith("#") and s.startswith(" Appendix "):
        rest = s[len(" Appendix "):]
        if rest[:1].isalpha():
            letters.append(rest[0])
expect = [chr(c) for c in range(ord("A"), ord("L") + 1)]
if letters == expect:
    ok(label, "A–L, contiguous, 12 appendices")
else:
    bad(label, f"expected A–L, found {''.join(letters) or '(none)'}")

# ---------------------------------------------------------------- section 4
# The checker list: count it, name-check it, and verify the number word.
BLOCK_HEAD = "checkers, all of which must exit zero:"
label = "checker list length"
head = TEXT.find(BLOCK_HEAD)
if head < 0:
    bad(label, "the checker-list heading is missing")
    listed = []
else:
    listed = []
    for line in TEXT[head:].splitlines()[1:]:
        if not line.strip():
            if listed:
                break
            continue
        if not line.startswith("    "):
            break
        first = line.split()[0]
        if first.endswith(".py"):
            listed.append(first)
        else:
            break
    NUMWORD = {11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
           15: "fifteen", 16: "sixteen"}
    word = NUMWORD.get(len(listed), "")
    if word and f"Then {word} checkers" in TEXT:
        ok(label, f"{len(listed)} entries, prose says '{word}'")
    else:
        bad(label, f"{len(listed)} entries listed; prose does not say 'Then {word} checkers'")

label = "every listed checker exists"
missing = [f for f in listed if not os.path.exists(os.path.join(ROOT, f))]
ok(label, f"{len(listed)} files") if not missing else bad(label, f"missing: {missing}")

# ------------------------------------------- counts the checkers themselves publish
def check_by_running(label, script, summary_literal, sub_literal):
    """Run the checker and require ITS OWN summary line, verbatim."""
    if not stated(label, sub_literal):
        return
    r = subprocess.run([sys.executable, script], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        bad(label, f"{script} exited {r.returncode}")
        return
    if summary_literal in r.stdout:
        ok(label, summary_literal.strip())
    else:
        bad(label, f"{script} did not print {summary_literal!r}")


check_by_running("verify_tables.py row count", "verify_tables.py",
                 "TOTAL VERIFIED 119", "119 rows")
check_by_running("prose_pins.py pin count", "prose_pins.py",
                 "31 pins over PAPER.md", "31 pins")
check_by_running("verify_section8.py claim count", "verify_section8.py",
                 "76 of 76 claims verified", "76 claims")
check_by_running("verify_refs.py reference count", "verify_refs.py",
                 "264 references, 0 failure(s)", "264 refs")

# ---------------------------------------------------------------- section 3
label = "responses/ cell count"
if stated(label, "3,344 model cells"):
    n = len([f for f in os.listdir(os.path.join(ROOT, "responses"))
             if f.endswith(".json")])
    ok(label, f"{n:,}") if n == 3344 else bad(label, f"says 3,344, found {n:,}")

label = "datasets/ count"
if stated(label, "all 15 datasets"):
    d = os.path.join(ROOT, "datasets")
    n = len([x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))])
    ok(label, f"{n}") if n == 15 else bad(label, f"says 15, found {n}")

label = "synth/tables/ shape"
if stated(label, "20 Stratum E tables — 113,400 rows"):
    d = os.path.join(ROOT, "synth", "tables")
    dirs = sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)))
    rows = 0
    for t in dirs:
        with open(os.path.join(d, t, "data.csv"), encoding="utf-8") as fh:
            rows += sum(1 for _ in fh) - 1
    if len(dirs) == 20 and rows == 113400:
        ok(label, f"{len(dirs)} tables, {rows:,} rows")
    else:
        bad(label, f"says 20 / 113,400; found {len(dirs)} / {rows:,}")

# --------------------------------------- every file SUBMISSION.md names must exist
EXTS = (".md", ".py", ".txt", ".json", ".png", ".csv")
label = "every file named in SUBMISSION.md exists"
named, missing = [], []
for i, seg in enumerate(TEXT.split("`")):
    if i % 2 == 0:
        continue                      # outside backticks
    s = seg.strip()
    if s.endswith("/") or s.endswith(EXTS):
        if s not in named:
            named.append(s)
            if not os.path.exists(os.path.join(ROOT, s.rstrip("/"))):
                missing.append(s)
if not missing:
    ok(label, f"{len(named)} paths, all present")
else:
    bad(label, f"missing: {missing}")

# ------------------------------------------------- the self-referential one
# SUBMISSION.md states this checker's OWN check count.  That is the one number
# here that cannot be recomputed from the artefact, only from this run -- so it
# is settled as a fixed point: CHECKED, plus one for this check itself.
label = "verify_submission.py self-count"
n_self = CHECKED + 1
if f"{n_self} checks" in TEXT:
    ok(label, f"{n_self} checks")
else:
    bad(label, f"this run performs {n_self} checks; "
               f"SUBMISSION.md does not say '{n_self} checks'")

# ---------------------------------------------------------------- verdict
print()
if FAILURES:
    print(f"  {CHECKED} checks, {len(FAILURES)} failure(s).\n")
    for lab, det in FAILURES:
        print(f"    {lab}: {det}")
    print()
    sys.exit(1)
print(f"  {CHECKED} checks, 0 failure(s).")
print("  SUBMISSION.md describes the artefact that is actually here.\n")
