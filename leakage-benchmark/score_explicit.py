"""Score the explicit-source transfer set.

SEPARATE SCORER, ON PURPOSE
  score.py pools over ALLSETS and carries a hard-coded B3 constant fitted on
  that corpus.  Feeding three new datasets into it would change a denominator
  every existing table depends on, and would compare models against a baseline
  threshold that was never fitted here.  Both are the kind of silent
  cross-contamination that has already cost this project two rounds of
  rework, so the explicit set is scored on its own and reported on its own.

COVERAGE IS REPORTED, NOT ASSUMED
  MI has 122 columns and CRIME 144.  A model that answers for 40 of them and
  stops has not scored 1.000 on the ones it reached -- it has failed the task.
  Cells below the coverage floor are marked and excluded from the pooled
  number, and the count of excluded cells is printed rather than hidden.
"""
import json, os, glob, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
from salvage import parse
import explicit_specs as ES

FLOOR = 0.90     # fraction of columns a cell must answer for to count


def cells():
    bundles = {ES.SPECS[k]["name"]: ES.build(k) for k in ES.SPECS}
    newest = {}
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if r["dataset"] not in bundles or r.get("paraphrase"):
            continue
        k = (r["model"], r["dataset"], r["condition"], r.get("seed"))
        if k not in newest or r.get("ts", "") > newest[k].get("ts", ""):
            newest[k] = r
    out = []
    for (m, ds, cond, seed), r in newest.items():
        d, _ = parse(r.get("raw", ""))
        if not d:
            out.append(dict(model=m, dataset=ds, cond=cond, seed=seed,
                            cov=0.0, tp=0, fp=0, fn=0, ok=False))
            continue
        b = bundles[ds]
        got = {c["name"]: c.get("verdict") for c in d["columns"]
               if isinstance(c, dict) and c.get("name")}
        answered = [c for c in b["truth"] if c in got]
        cov = len(answered) / len(b["truth"])
        tp = fp = fn = 0
        for c, is_pos in b["truth"].items():
            flagged = got.get(c) == "UNAVAILABLE"
            if is_pos and flagged:
                tp += 1
            elif is_pos:
                fn += 1
            elif flagged:
                fp += 1
        out.append(dict(model=m, dataset=ds, cond=cond, seed=seed, cov=cov,
                        tp=tp, fp=fp, fn=fn, ok=cov >= FLOOR,
                        missed=[c for c, p in b["truth"].items()
                                if p and got.get(c) != "UNAVAILABLE"],
                        subtypes=b["subtypes"]))
    return out, bundles


def f1(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return (2 * p * r / (p + r) if p + r else 0.0), p, r


def vote(cs, bundles, k=2):
    """Majority vote over seeds, which is the obvious response to a 0.312 F1
    spread caused by column order alone.  It costs k calls instead of one and
    needs no new evidence, so it is worth knowing whether it helps before
    anything more elaborate is proposed."""
    per = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for c in cs:
        if not c["ok"]:
            continue
        b = bundles[c["dataset"]]
        for col in b["truth"]:
            per[(c["model"], c["cond"], c["dataset"])][col][1] += 1
            if col not in c.get("missed", []) and b["truth"][col]:
                per[(c["model"], c["cond"], c["dataset"])][col][0] += 1
    return per


def main_vote():
    """Re-derive flags per (model, cond, dataset, column) and majority-vote."""
    bundles = {ES.SPECS[k]["name"]: ES.build(k) for k in ES.SPECS}
    votes = collections.defaultdict(lambda: [0, 0])
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if r["dataset"] not in bundles or r.get("paraphrase"):
            continue
        d, _ = parse(r.get("raw", ""))
        if not d:
            continue
        for c in d["columns"]:
            if isinstance(c, dict) and c.get("name"):
                k = (r["model"], r["condition"], r["dataset"], c["name"])
                votes[k][1] += 1
                if c.get("verdict") == "UNAVAILABLE":
                    votes[k][0] += 1
    agg = collections.defaultdict(lambda: [0, 0, 0])
    nseed = collections.defaultdict(int)
    for (m, cond, ds, col), (u, n) in votes.items():
        b = bundles.get(ds)
        if not b or col not in b["truth"]:
            continue
        nseed[(m, cond)] = max(nseed[(m, cond)], n)
        flagged = u * 2 > n
        a = agg[(m, cond)]
        if b["truth"][col] and flagged:
            a[0] += 1
        elif b["truth"][col]:
            a[2] += 1
        elif flagged:
            a[1] += 1
    print(f"\nmajority vote over seeds (one verdict per column, not per cell)")
    print(f"{'model':<22}{'cond':>5}{'seeds':>7}{'F1':>8}{'prec':>8}{'rec':>8}")
    for (m, cond), (tp, fp, fn) in sorted(agg.items()):
        F, p, r = f1(tp, fp, fn)
        print(f"{m[:21]:<22}{('C'+str(cond)):>5}{nseed[(m,cond)]:>7}"
              f"{F:>8.3f}{p:>8.3f}{r:>8.3f}")


def main():
    cs, bundles = cells()
    bad = [c for c in cs if not c["ok"]]
    good = [c for c in cs if c["ok"]]
    print(f"explicit-source transfer set -- {len(bundles)} datasets, "
          f"{sum(sum(b['truth'].values()) for b in bundles.values())} positives, "
          f"{sum(len(b['truth']) for b in bundles.values())} columns")
    print(f"{len(cs)} cells, {len(bad)} below the {FLOOR:.0%} coverage floor "
          f"(excluded)\n")

    agg = collections.defaultdict(lambda: [0, 0, 0, 0])
    for c in good:
        a = agg[(c["model"], c["cond"])]
        a[0] += c["tp"]; a[1] += c["fp"]; a[2] += c["fn"]; a[3] += 1
    print(f"{'model':<22}{'cond':>5}{'cells':>6}{'F1':>8}{'prec':>8}{'rec':>8}"
          f"{'tp':>5}{'fp':>5}{'fn':>5}")
    for (m, cond), (tp, fp, fn, n) in sorted(agg.items()):
        F, p, r = f1(tp, fp, fn)
        print(f"{m[:21]:<22}{('C'+str(cond)):>5}{n:>6}{F:>8.3f}{p:>8.3f}"
              f"{r:>8.3f}{tp:>5}{fp:>5}{fn:>5}")

    print(f"\nper dataset")
    per = collections.defaultdict(lambda: [0, 0, 0, 0])
    for c in good:
        a = per[(c["model"], c["cond"], c["dataset"])]
        a[0] += c["tp"]; a[1] += c["fp"]; a[2] += c["fn"]; a[3] += 1
    print(f"{'model':<22}{'cond':>5}{'dataset':>10}{'cells':>6}{'F1':>8}"
          f"{'prec':>8}{'rec':>8}")
    for (m, cond, ds), (tp, fp, fn, n) in sorted(per.items()):
        F, p, r = f1(tp, fp, fn)
        print(f"{m[:21]:<22}{('C'+str(cond)):>5}{ds:>10}{n:>6}{F:>8.3f}"
              f"{p:>8.3f}{r:>8.3f}")

    print(f"\nrecall by subtype (the claim the taxonomy makes)")
    st = collections.defaultdict(lambda: [0, 0])
    for c in good:
        for col, sub in c["subtypes"].items():
            st[(c["model"], c["cond"], sub)][1] += 1
            if col not in c["missed"]:
                st[(c["model"], c["cond"], sub)][0] += 1
    subs = sorted({k[2] for k in st})
    print(f"{'model':<22}{'cond':>5}" + "".join(f"{s[:11]:>16}" for s in subs))
    for m, cond in sorted({(k[0], k[1]) for k in st}):
        row = ""
        for s in subs:
            h, t = st[(m, cond, s)]
            row += f"{(f'{h}/{t}'):>10}{(f'{h/t:.0%}' if t else '-'):>6}"
        print(f"{m[:21]:<22}{('C'+str(cond)):>5}{row}")

    if bad:
        print(f"\nexcluded cells (coverage below floor)")
        for c in sorted(bad, key=lambda c: (c["model"], c["dataset"], c["cond"])):
            print(f"  {c['model'][:26]:<28}{c['dataset']:<9}C{c['cond']} "
                  f"s{c['seed']}  cov={c['cov']:.0%}")


if __name__ == "__main__":
    main()
    main_vote()
