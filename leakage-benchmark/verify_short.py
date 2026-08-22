"""PAPER_SHORT.md has no checker.  This is it.

WHY IT NEEDED ONE

  PAPER_SHORT.md is a condensed version of PAPER.md.  Five scripts mention it —
  every one of them only in a comment.  Nothing checked it, so it could drift
  from the long paper silently, and it had: after section 8 was written, the
  short version still carried the unqualified form of contribution (2), so the
  two manuscripts disagreed about the paper's second claim.

WHAT IT CHECKS

  1. Every number the short paper states is the number the long paper states.
     Quantities are listed BY HAND below, not scraped, for the reason
     verify_section8.py gives: a regex that stops matching reports nothing.
  2. Claims present in one manuscript and absent from the other, for the
     handful of load-bearing sentences where divergence would be a
     contradiction rather than an abridgement.
  3. Section numbering references inside PAPER_SHORT.md resolve to sections
     PAPER_SHORT.md actually has.

  An abridged paper SHOULD omit things.  This checks agreement, never
  coverage: a fact absent from the short version is fine, a fact present with a
  different value is not.

    python3 verify_short.py
"""
import re
import sys

LONG_RAW = open("PAPER.md").read()
SHORT_RAW = open("PAPER_SHORT.md").read()
# Search whitespace-FLATTENED copies.  The first version of this file searched
# the raw text, and `upper-bound baseline at 0.630` wraps across a line in both
# manuscripts, so the pattern matched nothing and the check passed silently --
# the precise failure this project keeps meeting.  A mutation test caught it.
LONG = re.sub(r"\s+", " ", LONG_RAW)
SHORT = re.sub(r"\s+", " ", SHORT_RAW)
NUM = open("NUMBERS.txt").read()
try:
    NUME = open("NUMBERS_E.txt").read()
except FileNotFoundError:
    NUME = ""

FAIL = []


def both(label, needle_short, needle_long):
    """A load-bearing sentence must agree across the two manuscripts."""
    a, b = needle_short in SHORT, needle_long in LONG
    if a != b:
        FAIL.append(f"{label}: short={a} long={b} — the manuscripts disagree")


def shared_number(label, pattern, source_value):
    """A number stated in BOTH manuscripts must be the same in both.

    A pattern that matches NEITHER manuscript is a dead check and is reported
    as a failure, not passed over: silence must never read as agreement.
    """
    ms = re.search(pattern, SHORT)
    ml = re.search(pattern, LONG)
    if ms is None and ml is None:
        FAIL.append(f"{label}: pattern matches neither manuscript — the check "
                    f"is dead; fix the pattern rather than leaving it silent")
    if ms and ml and ms.group(1) != ml.group(1):
        FAIL.append(f"{label}: short={ms.group(1)} long={ml.group(1)}")
    for tag, m in (("short", ms), ("long", ml)):
        if m and source_value is not None and m.group(1) != source_value:
            FAIL.append(f"{label} ({tag}): states {m.group(1)}, source says {source_value}")


def main():
    # ---- headline detection figures ---------------------------------------
    b3 = re.search(r"B3 \|correlation\|\s+P [\d.]+\s+R [\d.]+\s+F1 ([\d.]+)", NUM).group(1)
    shared_number("B3 upper bound", r"upper-bound baseline at ([\d.]+)", b3)
    shared_number("best F1", r"Best F1 ([\d.]+)\s*\n?against", "0.929")
    shared_number("downstream ceiling", r"honest ceiling to within ([\d.]+) F1", "0.024")

    # ---- the contributions must be ordered the same way in both -----------
    # This guard began life enforcing that contribution (2) carried the scope
    # "on public and on unseen data alike", because an unqualified version once
    # claimed more than the evidence showed.  The reorder made that scoping
    # structural instead: contribution (2) IS the unseen-data claim now, so the
    # thing worth guarding is that the two manuscripts still agree on which
    # contribution is which -- and that neither has drifted back to leading
    # with the benchmark, which is the order the abstract does not use.
    for name, txt in (("PAPER.md", LONG), ("PAPER_SHORT.md", SHORT)):
        if "Evidence that models detect what correlation cannot.**" in txt:
            FAIL.append(f"{name} carries the UNQUALIFIED contribution (2)")
        i1 = txt.find("**(1) The failure is definitional.**")
        i2 = txt.find("**(2) It is not explained by memorisation.**")
        if i1 < 0 or i2 < 0 or i1 > i2:
            FAIL.append(f"{name}: contributions (1) and (2) are not the "
                        f"definitional finding then the memorisation control, "
                        f"in that order")
        elif txt.find("**(1) A benchmark.**") >= 0:
            FAIL.append(f"{name} still leads its contributions with the "
                        f"benchmark; the abstract leads with the finding")
        else:
            print(f"  ok    {name:<16} contributions ordered finding, "
                  f"memorisation, benchmark")

    # ---- Stratum E figures, where the short paper states them -------------
    if NUME:
        d1 = re.search(r"D1 mean ([+-][\d.]+)", NUME).group(1).lstrip("+")
        d2 = re.search(r"D2 mean ([+-][\d.]+)", NUME).group(1).lstrip("+")
        c1 = re.search(r"exceed at C1: (\d+) of", NUME).group(1)
        c6 = re.search(r"exceed at C6: (\d+) of", NUME).group(1)
        bs = re.search(r"best synth C6 ([\d.]+)", NUME).group(1)
        # NUMBERS_E section 6 was rewritten when the difference-on-component
        # regression was withdrawn; this reads the statistic that REPLACED it.
        rr = re.search(r"C1  corr\(real, synthetic\) Pearson \+?([\d.]+)",
                       NUME).group(1)
        for label, pat, val in (
                ("Stratum E D1", r"C1 deficit is \*\*\+([\d.]+)\*\*", d1),
                ("Stratum E D2", r"repair is \*\*\+([\d.]+)\*\*", d2),
                ("Stratum E exceed C1", r"(\d+) of 16 models beat it at C1", c1),
                ("Stratum E exceed C6", r"and (\d+) of 16 at C6", c6),
                ("Stratum E best F1", r"best F1 falls 0\.929 → ([\d.]+)", bs),
                ("Stratum E corr(public, unseen)",
                 r"corr\(public, unseen\) = \+?([\d.]+)", rr),
        ):
            m = re.search(pat, SHORT)
            if m and m.group(1) != val:
                FAIL.append(f"{label}: PAPER_SHORT says {m.group(1)}, NUMBERS_E says {val}")
            if m is None:
                FAIL.append(f"{label}: stated in neither form this checker knows — "
                            f"if the sentence was reworded, update this pattern "
                            f"rather than deleting the check")

    # ---- section cross-references must resolve ----------------------------
    have = set(re.findall(r"^## (\d+)\.", SHORT_RAW, re.M))
    for ref in set(re.findall(r"§(\d+)", re.sub(r"\[N[^\]]*\]", "", SHORT_RAW))):
        if ref not in have:
            FAIL.append(f"PAPER_SHORT references §{ref}, which it does not contain")

    print("=" * 74)
    print("PAPER_SHORT.md — agreement with PAPER.md and the NUMBERS files")
    print("=" * 74)
    for f in FAIL:
        print(f"  FAIL  {f}")
    if not FAIL:
        print("  Every shared quantity agrees, contribution (2) is scoped in both,")
        print("  the Stratum E figures match NUMBERS_E.txt, and every section")
        print("  cross-reference resolves.")
    print(f"\n  {len(FAIL)} failure(s).")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
