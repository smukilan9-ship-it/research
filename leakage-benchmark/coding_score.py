"""Score independent codings against the corpus, and against each other.

    python3 coding_score.py coding_alice.txt coding_bob.txt ...

WHAT IT REPORTS AND WHY EACH ONE

  raw agreement       the number a reader intuits.  Reported first because it
                      is the one people actually understand, and because with
                      skewed marginals it will look far better than kappa and
                      a reader deserves to see both and know why they differ.

  Cohen's kappa       two raters.  Agreement above what their own marginal
                      habits would produce by chance.

  Fleiss' kappa       three or more raters.  Cohen's does not generalise past
                      two; using it on a panel is simply the wrong statistic.

  per-category        which boundary is doing the damage.  A single kappa over
                      four categories hides the fact that TIMING may be clean
                      while REASON/CONSEQUENCE is a coin flip -- and those two
                      hold 52 of the 68 items, so they dominate the total.

  CONTESTED collapsed kappa recomputed with CONTESTED folded into whichever
                      category the coder's second choice implies is impossible
                      to recover, so it is simply DROPPED here.  With n=2 the
                      category cannot support a reliability estimate and one
                      disagreement swings it wildly.  Reported separately, not
                      substituted for the headline.

  binary agreement    "does the quote license inadmissibility at all".  The
                      binary is quotation-licensed and should reproduce close
                      to perfectly.  If it does NOT, that is a far larger
                      finding than any subtype kappa, and it is reported first
                      in the summary for that reason.

  E3 sensitivity      the six records with no quotation are the weakest
                      evidence in the corpus.  Agreement is reported with and
                      without them; if it only holds when they are dropped,
                      the paper must say so.

WHAT THIS SCRIPT WILL NOT DO

  It will not tell you which coder was right.  Reliability is not validity.
  A panel that agrees has shown the codebook is learnable, not that the
  partition carves the phenomenon correctly, and the paper must say so in
  those words.
"""
import os, re, sys, json, math, collections, itertools

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
CATS = ["REASON", "CONSEQUENCE", "TIMING", "CONTESTED"]
ALIAS = {"R": "REASON", "C": "CONSEQUENCE", "T": "TIMING", "X": "CONTESTED",
         "CONS": "CONSEQUENCE", "CONT": "CONTESTED"}


def read_answers(path):
    """item -> (category, licensed, unsure).  Tolerant of spacing and case."""
    out = {}
    for ln in open(path, errors="replace"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        m = re.match(r"^(\d+)\s*[.):]?\s+([A-Za-z]+)\s*(?:[,\s]\s*([YyNn]))?"
                     r"\s*(\?)?\s*$", ln)
        if not m:
            print(f"  ! unparsed line in {os.path.basename(path)}: {ln!r}")
            continue
        n, cat, lic, unsure = m.groups()
        cat = cat.upper()
        cat = ALIAS.get(cat, cat)
        if cat not in CATS:
            print(f"  ! unknown category {cat!r} on item {n} "
                  f"in {os.path.basename(path)}")
            continue
        out[int(n)] = (cat, (lic or "Y").upper() == "Y", bool(unsure))
    return out


def cohen(a, b):
    """Cohen's kappa on two equal-length label sequences."""
    n = len(a)
    if not n:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def fleiss(table):
    """Fleiss' kappa.  `table[i][cat]` = how many raters chose cat for item i."""
    n_items = len(table)
    if not n_items:
        return float("nan")
    n_raters = sum(table[0].values())
    if n_raters < 2:
        return float("nan")
    cats = sorted({c for row in table for c in row})
    p_j = {c: sum(row.get(c, 0) for row in table) / (n_items * n_raters)
           for c in cats}
    P_i = [(sum(v * v for v in row.values()) - n_raters)
           / (n_raters * (n_raters - 1)) for row in table]
    P_bar = sum(P_i) / n_items
    Pe = sum(v * v for v in p_j.values())
    return (P_bar - Pe) / (1 - Pe) if Pe < 1 else float("nan")


def band(k):
    if k != k:
        return "undefined"
    for lim, name in ((0.0, "poor"), (0.20, "slight"), (0.40, "fair"),
                      (0.60, "moderate"), (0.80, "substantial")):
        if k <= lim:
            return name
    return "almost perfect"


def main(paths):
    key = json.load(open(HERE + "coding_key.json"))
    n = len(key)
    coders = {}
    for p in paths:
        name = re.sub(r"^coding_|\.txt$", "", os.path.basename(p))
        coders[name] = read_answers(HERE + os.path.basename(p)
                                    if not os.path.exists(p) else p)

    print("=" * 78)
    print("INTER-CODER RELIABILITY — subtype partition")
    print("=" * 78)
    print(f"  {n} items;  {len(coders)} independent coder(s) plus the corpus\n")

    missing = {c: [i for i in range(1, n + 1) if i not in a]
               for c, a in coders.items()}
    for c, miss in missing.items():
        if miss:
            print(f"  ! {c} did not answer {len(miss)} items: "
                  f"{miss[:12]}{' ...' if len(miss) > 12 else ''}")
    done = [i for i in range(1, n + 1)
            if all(i in a for a in coders.values())]
    if len(done) < n:
        print(f"  scoring the {len(done)} items every coder answered\n")

    e3 = {i for i, k in enumerate(key, 1) if k["tier"] == "E3"}
    noq = {i for i, k in enumerate(key, 1) if not k.get("has_quote", True)}
    orig = {i: k["subtype"] for i, k in enumerate(key, 1)}

    def report(label, items):
        if not items:
            return
        print("-" * 78)
        print(f"{label}   ({len(items)} items)")
        print("-" * 78)
        names = ["corpus"] + list(coders)
        seqs = {"corpus": [orig[i] for i in items]}
        for c, a in coders.items():
            seqs[c] = [a[i][0] for i in items]

        print("  pairwise:")
        for x, y in itertools.combinations(names, 2):
            po = sum(p == q for p, q in zip(seqs[x], seqs[y])) / len(items)
            k = cohen(seqs[x], seqs[y])
            print(f"    {x:<10} vs {y:<10} raw {po:6.1%}   "
                  f"Cohen's k {k:6.3f}  ({band(k)})")

        if len(names) > 2:
            tab = [collections.Counter(seqs[nm][j] for nm in names)
                   for j in range(len(items))]
            k = fleiss(tab)
            unan = sum(1 for t in tab if max(t.values()) == len(names))
            print(f"\n  all {len(names)} raters:  Fleiss' k {k:.3f}  ({band(k)})"
                  f";  unanimous on {unan}/{len(items)} = {unan/len(items):.1%}")

        print("\n  per-category agreement with the corpus:")
        for cat in CATS:
            idx = [j for j, i in enumerate(items) if orig[i] == cat]
            if not idx:
                continue
            for c in coders:
                hit = sum(1 for j in idx if seqs[c][j] == cat)
                print(f"    {cat:<12} n={len(idx):<3} {c:<10} "
                      f"{hit}/{len(idx)} = {hit/len(idx):5.1%}")

        print("\n  where the corpus and a coder part company:")
        shown = 0
        for j, i in enumerate(items):
            dis = {c: seqs[c][j] for c in coders if seqs[c][j] != orig[i]}
            if not dis:
                continue
            shown += 1
            k = key[i - 1]
            flags = "".join(" ?" if coders[c][i][2] else "" for c in dis)
            where = f"{k['dataset']}.{k['column']}"
            print(f"    #{i:<3} {where[:34]:<36}"
                  f"corpus {orig[i]:<12} -> "
                  f"{', '.join(f'{c}: {v}' for c, v in dis.items())}{flags}")
        if not shown:
            print("    none")
        print()

    report("ALL ITEMS", done)
    report(f"EXCLUDING the {len(noq)} records with no quotation at all",
           [i for i in done if i not in noq])
    report(f"E1+E2 ONLY — excluding all {len(e3)} tier-E3 records "
           f"(the referee's cut)", [i for i in done if i not in e3])
    report("EXCLUDING CONTESTED (n=2, too few to estimate)",
           [i for i in done if orig[i] != "CONTESTED"])

    print("=" * 78)
    print("BINARY CHECK — does the quotation license inadmissibility at all")
    print("=" * 78)
    print("  The corpus says yes for every item, by construction: these are its")
    print("  positives.  A coder saying N is disputing the label itself, which")
    print("  is a heavier disagreement than any subtype swap.\n")
    for c, a in coders.items():
        no = [i for i in done if not a[i][1]]
        print(f"  {c:<10} licensed {len(done)-len(no)}/{len(done)} = "
              f"{(len(done)-len(no))/len(done):.1%}")
        for i in no:
            k = key[i - 1]
            print(f"      disputes  #{i:<3} {k['dataset']}.{k['column']}"
                  f"   (corpus: {orig[i]}, tier {k['tier']})")
    unsure = {c: [i for i in done if a[i][2]] for c, a in coders.items()}
    for c, u in unsure.items():
        if u:
            print(f"\n  {c} flagged {len(u)} items unsure: {u}")

    print("\n" + "=" * 78)
    print("  Reliability is not validity.  A panel that agrees has shown the")
    print("  codebook is learnable and stable, NOT that the partition carves")
    print("  the phenomenon correctly.  The paper must say so in those words.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("usage: python3 coding_score.py coding_<name>.txt [more...]")
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
