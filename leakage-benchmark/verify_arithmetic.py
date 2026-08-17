"""Every stated difference, ratio and percentage in the paper, recomputed.

WHY A SEPARATE CHECKER

  verify_tables.py asks "does this row match its source row in NUMBERS.txt".
  claim_audit asks "does this decimal appear somewhere in NUMBERS.txt".  Neither
  asks the question that actually goes wrong in prose:

      the paper says X, and Y, and that the difference is Z.
      Is Z equal to X - Y?

  A subtraction is written by hand, survives every regeneration of the
  underlying numbers, and is invisible to a checker that only matches decimals
  — because X, Y and Z all appear in NUMBERS.txt individually.  When the
  underlying numbers move, the arithmetic silently stops holding.  That is how
  a ΔF1 of 0.643 outlived the 0.3575 it was computed from.

WHAT IT CHECKS

    1  "A → B" / "A -> B" followed by a stated delta       B - A
    2  "ΔF1 = D" / "dF1 D" against the nearest arm pair     keep - drop
    3  decrement tables: | model | mean | C1 | C6 | ...     real - alias
    4  "N in D — P%"  and  "N of D = P%"                    N/D
    5  "X/Y  Z%" subtype cells                              X/Y
    6  "from A to B" phrasings with an explicit difference  B - A

  Tolerance is one unit in the last decimal place quoted, so 0.632 vs 0.6324 is
  fine and 0.632 vs 0.643 is not.

WHAT A CLEAN RUN MEANS

  Only that every arithmetic relation this script recognises holds.  It cannot
  tell you a number is the RIGHT number — verify_tables does that — and it does
  not see relations stated in words without digits.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
# Optional manuscript override: the 12-page PAPER_SHORT.md is built from
# the same NUMBERS.txt and must pass the same checks.
TARGET = sys.argv[1] if len(sys.argv) > 1 else "PAPER.md"
DOCS = [TARGET, "APPENDIX.md"]


def tol(*quoted):
    """One unit in the last decimal place of the most precise value quoted."""
    dp = max((len(q.split(".")[1]) if "." in q else 0) for q in quoted)
    return 10 ** (-dp) * 1.01


def check(label, lhs, rhs, quoted, ctx, out):
    ok = abs(lhs - rhs) <= tol(*quoted)
    out.append((ok, label, lhs, rhs, ctx))
    return ok


def scan(path):
    body = open(HERE + path, errors="replace").read()
    lines = body.splitlines()
    out = []

    # Normalise before matching: the paper uses U+2212 MINUS, bold markers
    # around numbers, and narrow spaces.  The first version of this checker
    # matched none of the delta statements at all and reported "0 inconsistent"
    # over 274 relations — a clean bill of health from a check that was not
    # looking at anything.  A checker that cannot fail is worse than no checker.
    def norm(t):
        return (t.replace("\u2212", "-").replace("\u2013", "-")
                 .replace("**", "").replace("\u00a0", " "))
    lines = [norm(l) for l in lines]

    # --- 1. "A -> B" with a stated delta within three lines -----------------
    arrow = re.compile(r"(?<![\d.])(\d\.\d{2,4})\s*(?:\u2192|->|to)\s*(\d\.\d{2,4})")
    delta = re.compile(r"(?:\u0394|d)F1\s*(?:=|of|is)?\s*([+-]?\d\.\d{2,4})|"
                       r"\bdrop of\s*([+-]?\d\.\d{2,4})|"
                       r"\bdecrement[^.]{0,24}?([+-]\d\.\d{2,4})|"
                       r"\bgain is\s*([+-]?\d\.\d{2,4})|"
                       r"\bloses\s*([+-]?\d\.\d{2,4})")
    for i, ln in enumerate(lines):
        for m in arrow.finditer(ln):
            a, b = m.group(1), m.group(2)
            # same line only.  Searching a 3-line window paired an arrow with
            # a delta belonging to a different sentence and reported a failure
            # for a relation that was never claimed.
            dm = delta.search(ln)
            if not dm:
                continue
            d = next(g for g in dm.groups() if g)
            got, want = float(d), float(b) - float(a)
            if not d.startswith(("+", "-")):
                want = abs(want)
            check(f"{path}:{i+1} arrow-delta", got, want, (a, b, d),
                  ln.strip()[:88], out)

    # --- 2. "keep-all X, oracle Y, dF1 Z" in any order on one line ----------
    ko = re.compile(r"keep-all[^\d]{0,12}(\d\.\d{2,4})[^\d]{0,24}oracle[^\d]{0,12}"
                    r"(\d\.\d{2,4})[^\d]{0,28}?([+-]\d\.\d{2,4})", re.I)
    for i, ln in enumerate(lines):
        for m in ko.finditer(ln):
            k, o, d = m.groups()
            check(f"{path}:{i+1} keep-minus-oracle", float(d),
                  float(k) - float(o), (k, o, d), ln.strip()[:88], out)

    # --- 3. any table row holding two F1s and an explicit signed delta ------
    # The orientation of a delta column is a property of the table, not of the
    # syntax: a C1|C6|dF1 row means C6-C1, while a keep|drop|dF1 row means
    # keep-drop.  The checker cannot know which from the row alone, so it
    # accepts EITHER and only reports a row where NEITHER orientation holds.
    # Assuming one direction produced six false alarms on a table that was
    # arithmetically fine.
    row = re.compile(r"\|\s*(\d\.\d{2,4})\s*\|\s*(\d\.\d{2,4})\s*\|\s*"
                     r"([+-]\d\.\d{2,4})\s*\|")
    for i, ln in enumerate(lines):
        for m in row.finditer(ln):
            a, b, d = m.groups()
            fwd, rev = float(a) - float(b), float(b) - float(a)
            best = fwd if abs(float(d) - fwd) <= abs(float(d) - rev) else rev
            check(f"{path}:{i+1} row-delta", float(d), best, (a, b, d),
                  ln.strip()[:88], out)

    # --- 4. "N in D — P%" and "N of D = P%" ---------------------------------
    # Two-digit denominators and the parenthesised form, which prose uses.
    # NOTE this does NOT catch the failure mode it was written for.  The paper
    # carried "8 of 64 positives (12.5%)" against a corpus that had moved to
    # 8 of 56; 8/64 IS 12.5%, so the pair is internally consistent and no
    # arithmetic check can see it.  A stale-but-consistent quantity is a
    # SOURCING error, not an arithmetic one -- prose_pins.py is what catches it.
    rate = re.compile(r"(\d[\d,]*)\s*(?:in|of|/)\s*([\d,]{2,})[^.()%]{0,28}?"
                      r"[—\-–=:(]?\s*(\d+\.\d+)\s*%")
    for i, ln in enumerate(lines):
        for m in rate.finditer(ln):
            n, d, p = m.groups()
            n_, d_ = int(n.replace(",", "")), int(d.replace(",", ""))
            if d_ == 0:
                continue
            check(f"{path}:{i+1} rate", float(p), 100.0 * n_ / d_,
                  (p,), ln.strip()[:88], out)

    # --- 5. "X/Y  Z%" subtype cells ----------------------------------------
    frac = re.compile(r"(?<![\d/])(\d{1,3})\s*/\s*(\d{1,3})\s*=?\s*(\d{1,3})\s*%")
    for i, ln in enumerate(lines):
        for m in frac.finditer(ln):
            x, y, z = (int(g) for g in m.groups())
            if y == 0 or x > y:
                continue
            check(f"{path}:{i+1} fraction", float(z), 100.0 * x / y,
                  ("1",), ln.strip()[:88], out)
    return out


def main():
    allout = []
    for d in DOCS:
        if os.path.exists(HERE + d):
            allout += scan(d)
    bad = [r for r in allout if not r[0]]
    kinds = {}
    for ok, lab, *_ in allout:
        k = lab.split()[-1]
        kinds.setdefault(k, [0, 0])
        kinds[k][0] += 1
        kinds[k][1] += 0 if ok else 1
    print("=" * 78)
    print("ARITHMETIC AUDIT — every stated difference, ratio and percentage")
    print("=" * 78)
    for k, (n, f) in sorted(kinds.items()):
        print(f"  {k:<20}{n:>5} checked{('   ' + str(f) + ' FAILED') if f else ''}")
    print(f"\n  {len(allout)} relations checked, {len(bad)} inconsistent")
    for ok, lab, lhs, rhs, ctx in bad:
        print(f"\n  FAIL {lab}\n       stated {lhs}  recomputed {rhs:.4f}\n       {ctx}")
    if not bad:
        print("\n  Every arithmetic relation this script recognises holds.")
        print("  It does not certify that the inputs are the right numbers —")
        print("  verify_tables.py checks those against NUMBERS.txt.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
