"""Uncertainty on the headline comparisons: cluster bootstrap and McNemar.

WHY THE OBVIOUS INTERVAL WOULD BE WRONG

  Every F1 in this paper is pooled over columns, and columns are not
  independent observations.  CRIME contributes 144 columns and 17 positives,
  and 9 of those 17 rest on ONE sentence about data vintage; STEEL's six
  sibling faults are one derivation stated once.  A column-level bootstrap
  treats those as 17 and 6 independent draws and returns an interval far too
  narrow -- it would answer "how variable is this if I resample columns",
  which nobody is asking, instead of "how variable is this if I had drawn a
  different set of datasets", which is the question a reader has.

  So the resampling unit here is the DATASET, with all of its columns and
  seeds carried along.  With 12 Stratum-A datasets that produces wide
  intervals.  The width is the result, not a defect of the method: a 12-cluster
  corpus cannot support narrow intervals, and reporting narrow ones would mean
  having chosen the wrong unit.

WHY McNEMAR AND NOT A t-TEST

  C1 and C6 are scored on the SAME columns.  The information about which is
  better lives entirely in the columns where they disagree; the ones they both
  get right or both get wrong say nothing.  McNemar tabulates exactly those
  disagreements -- b = C1 right / C6 wrong, c = C1 wrong / C6 right -- and
  asks whether the split is lopsided beyond chance.  We use the exact binomial
  form (two-sided, p = 0.5 on b out of b + c) rather than the chi-square
  approximation, because several cells here have b + c under 25 where the
  approximation is not trustworthy.

  McNemar tests the per-column DECISIONS, not F1.  F1 is not a per-item
  quantity and cannot be fed to a paired item test; that is what the bootstrap
  is for.  The two answer different questions and are both reported:
  McNemar says "is the change in per-column correctness real", the bootstrap
  says "how far could this F1 difference move if the corpus were redrawn".

MATCHING

  Both tests use only (dataset, seed) pairs answered under BOTH conditions.
  An unmatched comparison is how the paraphrase arm once produced a 0.000
  recall that was an accounting error rather than a finding.
"""
import os, sys, math, random, collections
import verify_paper as V
import runner as RN

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
B_ITER = 2000
SEED = 20260816          # fixed: the interval must be reproducible


# ------------------------------------------------------------------ decisions
def decisions(model, bundles, conds=(1, 6)):
    """[(dataset, seed, column, y, {cond: flagged})] over matched cells."""
    cells = V.cells_for(model)
    keysets = []
    for c in conds:
        keysets.append({(d, s) for (d, cc, s) in cells if cc == c and d in bundles})
    matched = set.intersection(*keysets)
    rows = []
    for (d, s) in sorted(matched):
        b = bundles[d]
        got = {c: cells[(d, c, s)] for c in conds}
        # same join guard verify_paper uses: a cell whose verdict keys do not
        # meet the truth keys scores 0 recall and is a bug, not a result.
        if any(g and not (set(g) & set(b["truth"])) for g in got.values()):
            continue
        for col, pos in b["truth"].items():
            rows.append((d, s, col, bool(pos),
                         {c: got[c].get(col, {}).get("verdict") == "UNAVAILABLE"
                          for c in conds}))
    return rows


def f1_of(rows, cond):
    tp = sum(1 for r in rows if r[3] and r[4][cond])
    fp = sum(1 for r in rows if not r[3] and r[4][cond])
    fn = sum(1 for r in rows if r[3] and not r[4][cond])
    if tp + fn == 0:
        return float("nan")
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn)
    return 2 * p * r / (p + r) if p + r else 0.0


# ------------------------------------------------------------------- McNemar
def binom_two_sided(b, n):
    """Exact two-sided binomial p-value at p=0.5, by the method of small p's."""
    if n == 0:
        return 1.0
    def pmf(k):
        return math.comb(n, k) * 0.5 ** n
    obs = pmf(b)
    return min(1.0, sum(pmf(k) for k in range(n + 1) if pmf(k) <= obs + 1e-12))


def mcnemar(rows, c_a, c_b):
    """b = A right / B wrong, c = A wrong / B right, over the same columns."""
    b = c = 0
    for _, _, _, y, fl in rows:
        ok_a, ok_b = fl[c_a] == y, fl[c_b] == y
        if ok_a and not ok_b:
            b += 1
        elif ok_b and not ok_a:
            c += 1
    return b, c, binom_two_sided(min(b, c), b + c)


# ------------------------------------------------------- cluster bootstrap
def boot_delta(rows, c_a, c_b, iters=B_ITER, seed=SEED):
    """95% percentile CI for F1(c_b) - F1(c_a), resampling DATASETS."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r[0]].append(r)
    ds = sorted(by)
    if len(ds) < 2:
        return None
    rng = random.Random(seed)
    out = []
    for _ in range(iters):
        draw = [d for d in (rng.choice(ds) for _ in ds)]
        rs = [r for d in draw for r in by[d]]
        a, b = f1_of(rs, c_a), f1_of(rs, c_b)
        if not (math.isnan(a) or math.isnan(b)):
            out.append(b - a)
    if not out:
        return None
    out.sort()
    lo = out[int(0.025 * len(out))]
    hi = out[min(len(out) - 1, int(0.975 * len(out)))]
    return lo, hi, len(ds)


def report(main_b=None):
    if main_b is None:
        main_b = {}
        for k in RN.ALLSETS:
            bb = RN.spec_bundle(k)
            main_b[bb["name"]] = bb
    print("Cluster bootstrap resamples DATASETS (not columns), 2,000 draws, "
          "seed 20260816.")
    print("McNemar is the exact two-sided binomial on discordant per-column "
          "decisions.\n")
    print(f"  {'model':<34}{'F1 C1':>7}{'F1 C6':>7}{'dF1':>8}"
          f"{'95% CI (datasets resampled)':>30}{'b':>6}{'c':>6}{'p':>9}{'Holm':>9}")
    n_comp = 0
    collected = []
    for m in V.MODELS:
        rows = decisions(m, main_b)
        if not rows:
            continue
        n_comp += 1
        a, b_ = f1_of(rows, 1), f1_of(rows, 6)
        if math.isnan(a) or math.isnan(b_):
            continue
        ci = boot_delta(rows, 1, 6)
        bb, cc, p = mcnemar(rows, 1, 6)
        cis = f"[{ci[0]:+.3f}, {ci[1]:+.3f}]  n={ci[2]}" if ci else "--"
        collected.append([m, a, b_, cis, bb, cc, p])

    # HOLM-BONFERRONI over the whole family.  The footnote below used to say
    # the p-values were "uncorrected for the N comparisons" and leave it there,
    # which names a multiplicity problem without acting on it.  Step-down Holm
    # is reported ALONGSIDE the raw value so a reader can see both, and the
    # count that survives correction is stated rather than left to be worked
    # out from the column.
    order = sorted(range(len(collected)), key=lambda i: collected[i][6])
    k = len(order)
    running = 0.0
    holm = {}
    for rank, i in enumerate(order):
        adj = min(1.0, (k - rank) * collected[i][6])
        running = max(running, adj)          # step-down monotonicity
        holm[i] = running
    for i, (m, a, b_, cis, bb, cc, p) in enumerate(collected):
        star = "" if p >= 0.05 else ("  *" if p >= 0.01 else "  **")
        hstar = "" if holm[i] >= 0.05 else ("  *" if holm[i] >= 0.01 else "  **")
        print(f"  {m[:32]:<34}{a:>7.3f}{b_:>7.3f}{b_-a:>+8.3f}{cis:>30}"
              f"{bb:>6}{cc:>6}{p:>9.4f}{star:<4}{holm[i]:>7.4f}{hstar}")

    raw_sig = sum(1 for r in collected if r[6] < 0.05)
    holm_sig = sum(1 for i in holm if holm[i] < 0.05)
    print(f"\n  significant at raw alpha=0.05: {raw_sig} of {k}")
    print(f"  significant after Holm-Bonferroni: {holm_sig} of {k}")
    dropped = [collected[i][0] for i in range(k)
               if collected[i][6] < 0.05 <= holm[i]]
    if dropped:
        print(f"  do NOT survive correction: {', '.join(x[:30] for x in dropped)}")
    print("\n  b = correct at C1 and wrong at C6;  c = wrong at C1 and correct "
          "at C6.")
    # COUNTED, not hardcoded.  This said "the ten comparisons" while the
    # roster held ten models, and a roster change would have left it asserting
    # a multiple-testing burden the table no longer has -- understating it,
    # which is the direction that flatters the result.
    print(f"  * p<0.05, ** p<0.01, two-sided.  The `p` column is RAW; the "
          f"`Holm` column is\n  step-down Holm-Bonferroni over all {n_comp} "
          f"comparisons and is the one to read.")
    print("  A CI that spans zero and a significant McNemar are NOT in "
          "conflict: McNemar asks\n  whether per-column decisions moved, the "
          "interval asks whether the F1 gap would\n  survive a different draw "
          "of datasets.  With 12 clusters the second is a hard test.")
    return 0


def main():
    print("=" * 92)
    print("UNCERTAINTY ON THE C1 -> C6 CHANGE")
    print("=" * 92)
    return report()


if __name__ == "__main__":
    sys.exit(main())
