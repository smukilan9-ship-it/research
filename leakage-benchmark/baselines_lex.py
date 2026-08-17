"""B1-tuned -- the keyword-over-column-names baseline, made to work.

WHY THIS BASELINE AND NOT ANOTHER

  B3 is a statistical screen: it reads values and knows nothing about names.
  The models read names and know nothing about values.  A reader is therefore
  entitled to the obvious middle: how much of the models' performance is
  available to a regular expression over the column names alone?

  The question has teeth because S6.3 reports that 19-61% of leaking column
  names are recallable from a partial schema.  If names alone carry the signal,
  the models could be pattern-matching a vocabulary rather than reasoning about
  a target -- and the honest way to find out is to build the pattern-matcher.

TWO VARIANTS, AND THE DIFFERENCE BETWEEN THEM IS THE POINT

  B1          the S4.3 sieve vocabulary, unchanged, applied to names instead of
              descriptions.  Nothing about this corpus informed it: it was
              written to screen data-dictionary PROSE before any model was run.
              This is the baseline already in section 5, and this file
              reproduces its numbers as a check on itself.

  B1-tuned    B1 plus name patterns added by looking at what actually
              leaks here -- days_to_*, *_outcome, body, discharge_*, and the
              rest below.  Fitted to the answers, exactly like B3's swept
              threshold, and reported as an UPPER bound for the same reason.
              A baseline nobody tried to make work is a strawman.

  Reporting only the tuned one would overstate what a keyword rule achieves in
  the wild; reporting only the frozen one would understate it.  Both, per
  stratum, and the gap between them is itself a result.

STRATA ARE SCORED SEPARATELY, AND STRATUM B IS OUT OF SAMPLE

  Every pattern in TUNED_EXTRA was chosen by looking at columns that leak in
  STRATUM A -- koi_fpflag, body, discharge, the fault siblings.  None came from
  Stratum B.  So the tuned rule is fitted on A and TESTED on B, and its Stratum
  B score is an honest out-of-sample number rather than a second fit.

  The expectation going in was that a keyword rule would do BETTER on B, since
  S6.1 argues Stratum B is lexically easy.  It does not; it scores zero.  The
  two senses of "lexical" come apart: B's positives are easy to recognise from
  ordinary technical English, and share no vocabulary a regex can carry from
  one dataset to the next.  Pooling the strata would have hidden that inside an
  average.
"""
import os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN
from screen import MARKERS
from subtypes import subtype

# The frozen instrument, applied to a surface it was not written for.  Column
# names are snake_case and abbreviated, so word boundaries are relaxed to
# separator boundaries -- that is a translation of the same patterns, not an
# extension of them.
FROZEN = re.compile("|".join(m.replace(r"\b", r"(?:\b|_)") for m in MARKERS),
                    re.I)

# Added with hindsight.  Every one of these was chosen by looking at columns
# this corpus codes positive, which is what makes the result an upper bound.
TUNED_EXTRA = [
    r"days?_to_", r"_outcome$", r"^outcome", r"^body$", r"^discharge",
    r"_flag$", r"^koi_fpflag", r"fpflag", r"_status$", r"^status",
    r"total_", r"_total$", r"^is_", r"_id$",
    r"recover", r"settle", r"charge_?off", r"writeoff",
    r"death|died|mort|expire|surviv|alive",
    r"readmi", r"relapse", r"cured|healed",
    r"^n_days$", r"_days$", r"duration", r"time_to",
    r"result", r"score$", r"grade$", r"class$", r"label$", r"target$",
    r"fault|failure|_fail",
    r"casual|registered",
]
TUNED = re.compile("|".join(m.replace(r"\b", r"(?:\b|_)")
                            for m in MARKERS + TUNED_EXTRA), re.I)


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score(bundles, pat):
    tp = fp = fn = 0
    misses, falses = [], []
    for name, b in sorted(bundles.items()):
        for col, pos in sorted(b["truth"].items()):
            hit = bool(pat.search(str(col)))
            if pos and hit:
                tp += 1
            elif pos and not hit:
                fn += 1
                misses.append((name, col))
            elif hit and not pos:
                fp += 1
                falses.append((name, col))
    return dict(tp=tp, fp=fp, fn=fn, prf=prf(tp, fp, fn),
                misses=misses, falses=falses)


def main():
    a, b = {}, {}
    for k in RN.ALLSETS:
        s = RN.spec_bundle(k)
        a[s["name"]] = s
    for k in RN.EXPLICIT:
        s = RN.spec_bundle(k)
        if s["name"] not in a:
            b[s["name"]] = s

    print("=" * 84)
    print("B1 / B1-tuned — KEYWORD DETECTOR OVER COLUMN NAMES")
    print("=" * 84)
    print(f"  frozen vocabulary: {len(MARKERS)} patterns, written for "
          f"dictionary prose in §4.3")
    print(f"  tuned vocabulary:  + {len(TUNED_EXTRA)} name patterns chosen by "
          f"looking at this corpus\n")

    print(f"  {'stratum':<12}{'variant':<12}{'P':>8}{'R':>8}{'F1':>8}"
          f"{'tp':>5}{'fp':>5}{'fn':>5}   n columns")
    res = {}
    for label, bundles in (("A", a), ("B", b)):
        ncol = sum(len(x["truth"]) for x in bundles.values())
        for vname, pat in (("B1", FROZEN), ("B1-tuned", TUNED)):
            r = score(bundles, pat)
            res[(label, vname)] = r
            p, rc, f = r["prf"]
            print(f"  {'Stratum ' + label:<12}{vname:<12}{p:>8.3f}{rc:>8.3f}"
                  f"{f:>8.3f}{r['tp']:>5}{r['fp']:>5}{r['fn']:>5}   {ncol}")

    print("\n  --- what the tuned rule misses on Stratum A, by subtype")
    ms = collections.Counter(subtype(d, c) or "?"
                             for d, c in res[("A", "B1-tuned")]["misses"])
    for st, n in ms.most_common():
        print(f"    {st:<14}{n}")

    print("\n  --- a sample of the tuned rule's false positives on Stratum A")
    for d, c in res[("A", "B1-tuned")]["falses"][:12]:
        print(f"    {d:<12}{c}")
    nf = len(res[("A", "B1-tuned")]["falses"])
    if nf > 12:
        print(f"    ... and {nf - 12} more")

    fa = res[("A", "B1-tuned")]["prf"][2]
    fb = res[("B", "B1-tuned")]["prf"][2]
    print(f"\n  Tuned F1: Stratum A {fa:.3f}, Stratum B {fb:.3f}, "
          f"difference {fb - fa:+.3f}.")
    print("  The rule was fitted on Stratum A and scores zero on Stratum B,")
    print("  where the frontier model at C1 is exact.  Leaking column names")
    print("  share no vocabulary that carries from one dataset to the next,")
    print("  which is the sense in which reading a name is not matching it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
