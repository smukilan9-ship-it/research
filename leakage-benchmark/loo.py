"""Leave-one-dataset-out, and seed variance.

WHY
  SUPPORT2 contributes 15 of 46 positives -- a third of the corpus.  Any pooled
  number is disproportionately a statement about that one dataset, and the
  obvious reviewer question is whether the headline survives dropping it.  The
  same question applies to STEEL, which contributes 6 of the 15 REASON columns
  and is the only dataset where the models get REASON right without help.

WHAT IS REPORTED
  For each held-out dataset: F1 at C1 and C6 on the remaining 11, plus the
  REASON recall that the paper's central claim rests on.  A claim that only
  holds with a particular dataset present is a claim about that dataset.

SEEDS
  Where several shuffle seeds exist for a cell, the spread is reported as
  min-max rather than a standard deviation: with 5 seeds an SD is not
  meaningfully estimable, and a range states the same thing without implying
  more precision than the data supports.
"""
import json, os, glob, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
from salvage import parse
import runner as RN
from subtypes import subtype


def load(model, conds=(1, 6, 7)):
    """(condition, seed, dataset) -> {column: flagged}"""
    out = collections.defaultdict(dict)
    newest = {}
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if r.get("paraphrase") or r["model"] != model or r["condition"] not in conds:
            continue
        if r["status"].startswith("ERROR"):
            continue
        k = (r["condition"], r.get("seed"), r["dataset"])
        if k not in newest or r.get("ts", "") > newest[k].get("ts", ""):
            newest[k] = r
    for k, r in newest.items():
        d, _ = parse(r.get("raw", ""))
        if not d:
            continue
        out[k] = {c["name"]: (c.get("verdict") == "UNAVAILABLE")
                  for c in d["columns"] if isinstance(c, dict) and c.get("name")}
    return out


def rr(res):
    """REASON recall as 'hit/total' for the table."""
    h, t = res["reason"]
    return f"{h}/{t}"


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def score(flags, bundles, conds, seed, skip=None):
    tp = fp = fn = 0
    rhit = rtot = 0
    for name, b in bundles.items():
        if name == skip:
            continue
        got = flags.get((conds, seed, name))
        if got is None:
            return None
        for col, is_pos in b["truth"].items():
            f = got.get(col, False)
            if is_pos and f: tp += 1
            elif is_pos: fn += 1
            elif f: fp += 1
            if is_pos and subtype(name, col) == "REASON":
                rtot += 1
                if f:
                    rhit += 1
    p, r, f1 = prf(tp, fp, fn)
    return dict(p=p, r=r, f1=f1, tp=tp, fp=fp, fn=fn,
                reason=(rhit, rtot))


def main():
    model = "gemini-3.7-flash"
    for a in sys.argv[1:]:
        if a.startswith("--model="):
            model = a.split("=", 1)[1]
    bundles = {}
    for k in RN.ALLSETS:
        b = RN.spec_bundle(k)
        bundles[b["name"]] = b
    flags = load(model)
    seeds = sorted({k[1] for k in flags})

    print(f"model: {model}\nseeds present: {seeds}\n")

    # ---- seed variance on the full corpus --------------------------------
    print("SEED VARIANCE (full 12-dataset corpus)")
    print(f"  {'cond':<6}{'n seeds':>8}{'F1 min':>9}{'F1 max':>9}{'F1 mean':>9}"
          f"{'REASON recall range':>24}")
    base = {}
    for cond in (1, 6, 7):
        vals, rrange = [], []
        for s in seeds:
            r = score(flags, bundles, cond, s)
            if r:
                vals.append(r["f1"])
                rrange.append(r["reason"][0] / r["reason"][1] if r["reason"][1] else 0)
        if not vals:
            continue
        base[cond] = vals
        print(f"  C{cond:<5}{len(vals):>8}{min(vals):>9.3f}{max(vals):>9.3f}"
              f"{sum(vals)/len(vals):>9.3f}"
              f"{f'{min(rrange):.0%} - {max(rrange):.0%}':>24}")
    if 1 in base and 6 in base:
        lo = min(base[6]) - max(base[1])
        print(f"\n  worst-case C6 - C1 across seeds: {lo:+.3f}  "
              f"({'holds' if lo > 0 else 'DOES NOT HOLD'} at every seed pairing)")

    # ---- leave one dataset out -------------------------------------------
    print(f"\nLEAVE-ONE-DATASET-OUT (seed {seeds[0]}, 11 datasets each row)")
    print(f"  {'held out':<13}{'C1 F1':>8}{'C6 F1':>8}{'delta':>8}"
          f"{'C1 REASON':>12}{'C6 REASON':>12}")
    full1 = score(flags, bundles, 1, seeds[0])
    full6 = score(flags, bundles, 6, seeds[0])
    if full1 and full6:
        print(f"  {'(none)':<13}{full1['f1']:>8.3f}{full6['f1']:>8.3f}"
              f"{full6['f1']-full1['f1']:>+8.3f}"
              f"{rr(full1):>12}{rr(full6):>12}")
    worst = None
    for name in sorted(bundles):
        a = score(flags, bundles, 1, seeds[0], skip=name)
        b_ = score(flags, bundles, 6, seeds[0], skip=name)
        if not a or not b_:
            continue
        d = b_["f1"] - a["f1"]
        if worst is None or d < worst[1]:
            worst = (name, d)
        print(f"  {name:<13}{a['f1']:>8.3f}{b_['f1']:>8.3f}{d:>+8.3f}"
              f"{rr(a):>12}{rr(b_):>12}")
    if worst:
        print(f"\n  smallest C6 gain with any single dataset removed: "
              f"{worst[1]:+.3f} (dropping {worst[0]})")
        print("  the C6 effect is not an artifact of one dataset"
              if worst[1] > 0 else
              "  !! the C6 effect DEPENDS on one dataset -- report this")


if __name__ == "__main__":
    main()
