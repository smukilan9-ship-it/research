"""The mechanism partition's structural properties, re-checked from the corpus.

WHY THIS EXISTS

  §2.2 claims the taxonomy is defensible the way Kapoor and Narayanan's is:
  induced from cases and EXHAUSTIVE over them, so a reader can attack it by
  producing a case that fits nowhere.  That claim is only worth making if it
  is checked, and it is the kind of claim that decays silently -- one new
  positive with no mechanism, or a mechanism quietly renamed, and the sentence
  in §2.2 becomes false while every other checker still passes.

WHAT IT CHECKS

  1. EXHAUSTIVE      every positive in Strata A and B carries a mechanism;
                     no residual, nothing unassigned
  2. CLOSED          no mechanism appears that §2.2 does not define
  3. CONTESTED IS RARE  it is an admission, not a bin: the paper says "twice",
                     so twice is what must be there
  4. COUNTS MATCH    the per-mechanism counts §2.2 states are the counts the
                     corpus has
  5. STRATUM E       its 120 injected positives are 40/40/40 by construction,
                     since that is what makes the definitional finding
                     independent of any coder

    python3 verify_taxonomy.py
"""
import collections
import sys

sys.path.insert(0, "."); sys.path.insert(0, "synth")
import runner as RN                                          # noqa: E402
import verify_paper as V                                     # noqa: E402
import export as EX                                          # noqa: E402

DEFINED = {"REASON", "CONSEQUENCE", "TIMING", "UPSTREAM", "CONTESTED"}
STATED = {"CONSEQUENCE": 30, "REASON": 22, "TIMING": 14, "CONTESTED": 2}
FAIL = []


def main():
    per = collections.Counter()
    unassigned, undefined = [], []
    for k in RN.ALLSETS + RN.EXPLICIT:
        try:
            b = RN.spec_bundle(k)
        except Exception:
            continue
        for c, pos in b["truth"].items():
            if not pos:
                continue
            st = V.subtype(b["name"], c)
            per[st or "NONE"] += 1
            if st in (None, "NONE", "UNCODED"):
                unassigned.append(f"{b['name']}.{c}")
            elif st not in DEFINED:
                undefined.append(f"{b['name']}.{c} -> {st}")

    print("=" * 74)
    print("TAXONOMY — the partition's structural properties")
    print("=" * 74)
    total = sum(per.values())
    print(f"  {total} positives in Strata A and B\n")
    for k, v in per.most_common():
        print(f"    {k:<14}{v:>4}   {100*v/total:5.1f}%")

    if unassigned:
        FAIL.append(f"NOT EXHAUSTIVE — {len(unassigned)} positive(s) carry no "
                    f"mechanism: {', '.join(unassigned[:6])}")
    if undefined:
        FAIL.append(f"NOT CLOSED — mechanism(s) §2.2 does not define: "
                    f"{', '.join(undefined[:6])}")
    for k, want in STATED.items():
        if per[k] != want:
            FAIL.append(f"§2.2 states {want} {k}; the corpus has {per[k]}")
    if per["CONTESTED"] > 4:
        FAIL.append(f"CONTESTED used {per['CONTESTED']} times — §2.2 calls it an "
                    f"admission rather than a bin, and that stops being true "
                    f"if it absorbs disagreement")

    # Stratum E: the finding's independence from any coder rests on this
    syn = collections.Counter()
    for n in EX.names():
        for st in EX.bundle(n, want_sample=False)["subtype"].values():
            if st:
                syn[st] += 1
    print(f"\n  Stratum E, assigned by generating rule rather than by reading:")
    for k, v in sorted(syn.items()):
        print(f"    {k:<14}{v:>4}")
    for k in ("REASON", "CONSEQUENCE", "TIMING"):
        if syn[k] != 40:
            FAIL.append(f"Stratum E has {syn[k]} {k}, not the 40 the plan fixed")
    gen, coded = sum(syn.values()), total
    share = 100 * gen / (gen + coded)
    print(f"\n  {gen} of {gen+coded} subtype-labelled positives need no coder "
          f"({share:.0f}%)")

    # This is the number that answers "what if the coder was wrong?", so the
    # PAPER must state the value the CORPUS has.  It was computed here and
    # printed, and nothing compared it to the prose -- which meant the corpus
    # could move and PAPER.md would go on claiming 120 of 188 forever.
    #
    # The paper states it TWICE, in S6.2 and again in S9, and both must move
    # together.  Checked by exact substring on whitespace-flattened text: no
    # regex, because a pattern that matches nothing is indistinguishable from
    # one that matches everything and this repository has been bitten by that.
    flat = " ".join(open("PAPER.md", encoding="utf-8").read().split())
    core = f"{gen} of the {gen+coded} subtype-labelled positives in this paper,"
    n = flat.count(core)
    if n != 2:
        FAIL.append(f"PAPER.md states '{core}' {n} time(s); S6.2 and S9 must "
                    f"BOTH state it, and both must match the corpus")
    for form, where in ((f"**{share:.0f}%**", "S6.2"),
                        (f"{share:.0f}%, need no coder at all", "S9")):
        if form not in flat:
            FAIL.append(f"{where} does not state the share as '{form}' — the "
                        f"corpus gives {share:.0f}%")

    print()
    for f in FAIL:
        print(f"  FAIL  {f}")
    if not FAIL:
        print("  Exhaustive, closed, and the counts §2.2 states are the counts")
        print("  the corpus has.  CONTESTED is used twice, on the two follow-up")
        print("  durations, which is where the ambiguity should fall.")
    print(f"\n  {len(FAIL)} failure(s).")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
