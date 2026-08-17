"""Score run_results.json against the verified ground truth.

Scored on the POSITIVE class (label-derived). Accuracy is meaningless at 11%
prevalence -- a model answering AVAILABLE for everything scores 89%.

ABSTAIN is counted as "not flagged": abstaining on a leak is a miss, abstaining
on a legitimate column is correct. That is the conservative reading and it is
the one a practitioner would experience.

The bar is B3 from baselines.py: |correlation| with a threshold tuned on the
test set, F1 0.812. That threshold is fitted on the answers, so it is an upper
bound on what a statistical screen could achieve without knowing them.
"""
import json, os, glob, sys, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from salvage import parse
import runner as RN

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
# B3 must be measured on the SAME corpus the models were scored on.  0.812 was
# the six-dataset figure; carrying it to the ten-dataset corpus compares models
# against a bar computed on different data.  Recomputed by baselines10.py.
B3_F1_6 = 0.812
B3_F1 = 0.658
ALIAS_BACK = {}
# columns |correlation| cannot see -- the interesting subset (baselines.py)
BLIND = {("DIABETES", "discharge_disposition_id"), ("LC", "collection_recovery_fee"),
         ("COMPAS", "r_days_from_arrest"), ("TITANIC", "body")}


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score_cell(c):
    tp = fp = fn = tn = abst = 0
    missed, falsely = [], []
    for col, truth in c["truth"].items():
        v = (c["verdicts"] or {}).get(col)
        flagged = (v == "UNAVAILABLE")
        if v == "ABSTAIN":
            abst += 1
        if truth and flagged: tp += 1
        elif truth and not flagged: fn += 1; missed.append(col)
        elif not truth and flagged: fp += 1; falsely.append(col)
        else: tn += 1
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, abstain=abst,
                missed=missed, falsely=falsely)


def main():
    # re-parse from the response cache so scoring never depends on how the
    # runner happened to parse at call time
    bundles = {}
    R, modes = [], collections.Counter()

    # Two things this loop must get right, both of which silently corrupted the
    # table before 2026-08-13:
    #
    # 1. PARAPHRASED RUNS ARE A DIFFERENT EXPERIMENT.  Their records carry the
    #    ORIGINAL dataset name (so they can be joined back) but ALIASED column
    #    names.  Scored against the original truth dict, not one key matches, so
    #    every positive reads as a miss and the model gains phantom zero-recall
    #    cells.  They are excluded here and scored separately by --paraphrase.
    #
    # 2. DUPLICATE CELLS FROM PROMPT CHANGES.  The cache key is a hash of the
    #    prompt, so fixing the empty-description bug produced a SECOND C4 record
    #    for DIABETES and AI4I -- build() is cumulative, so C4 gained a
    #    description for the two datasets that have one.  Globbing both into C4
    #    double-counts those datasets under two different prompts.  Keep the
    #    newest record per (model, dataset, condition, seed).
    want_para = "--paraphrase" in sys.argv
    newest = {}
    for f in sorted(glob.glob(HERE + "responses/*.json")):
        rec = json.load(open(f))
        if bool(rec.get("paraphrase")) != want_para:
            continue
        k = (rec["model"], rec["dataset"], rec["condition"], rec.get("seed"))
        if k not in newest or rec.get("ts", "") > newest[k].get("ts", ""):
            newest[k] = rec
    dropped = sum(1 for f in glob.glob(HERE + "responses/*.json")
                  if bool(json.load(open(f)).get("paraphrase")) == want_para) - len(newest)

    for k in RN.ALLSETS:
        try:
            bb = RN.spec_bundle(k)
        except Exception as e:
            print(f"  spec {k} unavailable: {type(e).__name__}"); continue
        bundles[bb["name"]] = bb
    global ALIAS_BACK
    ALIAS_BACK = {}
    if want_para:
        import paraphrase as PP
        bundles = {n: PP.apply_to(b) for n, b in bundles.items()}
        # alias -> original, so BLIND (keyed on originals) still resolves
        for n, b in bundles.items():
            for alias, orig in b["alias"].items():
                ALIAS_BACK[(n, alias)] = orig

    for rec in newest.values():
        d, mode = parse(rec.get("raw", ""))
        modes[mode] += 1
        if not d:
            continue
        b = bundles.get(rec["dataset"])
        if not b:
            continue
        got = {c["name"]: c.get("verdict") for c in d["columns"]
               if isinstance(c, dict) and c.get("name")}
        # a cell whose verdict keys do not match the truth keys is a join bug,
        # not a zero score -- refuse it loudly rather than record 0 recall
        if got and not (set(got) & set(b["truth"])):
            print(f"  JOIN ERROR {rec['model'][:24]} {rec['dataset']} C{rec['condition']}: "
                  f"no verdict key matches truth; skipped")
            continue
        R.append(dict(model=rec["model"], dataset=rec["dataset"],
                      condition=rec["condition"], seed=rec.get("seed"),
                      parsed=True, parse_mode=mode, verdicts=got, truth=b["truth"]))
    ok = R
    if dropped:
        print(f"  {dropped} superseded cell(s) dropped (older prompt for the "
              f"same model/dataset/condition)")
    print(f"  scoring {'PARAPHRASED' if want_para else 'ORIGINAL'} runs\n")
    print(f"{sum(modes.values())} cached responses -> {len(ok)} scored   "
          f"parse modes: {dict(modes)}\n")

    agg = collections.defaultdict(lambda: dict(tp=0, fp=0, fn=0, tn=0, abstain=0))
    per_ds = collections.defaultdict(lambda: dict(tp=0, fn=0))
    blind_hits = collections.defaultdict(lambda: [0, 0])
    for c in ok:
        s = score_cell(c)
        k = (c["model"], c["condition"])
        for f in ("tp", "fp", "fn", "tn", "abstain"):
            agg[k][f] += s[f]
        for col, truth in c["truth"].items():
            if not truth: continue
            # BLIND is keyed on ORIGINAL column names.  In the paraphrase arm
            # the truth dict is keyed on aliases, so a raw lookup matches
            # nothing and every cell reports 0/0 -- an empty denominator that
            # reads like "found none" but means "never checked".
            key = (c["dataset"], ALIAS_BACK.get((c["dataset"], col), col))
            if key in BLIND:
                blind_hits[k][1] += 1
                if (c["verdicts"] or {}).get(col) == "UNAVAILABLE":
                    blind_hits[k][0] += 1
        per_ds[(c["model"], c["condition"], c["dataset"])]["tp"] += s["tp"]
        per_ds[(c["model"], c["condition"], c["dataset"])]["fn"] += s["fn"]

    # How many datasets actually contributed to each cell.  Without this an
    # aggregate over the 2 datasets that happened to succeed reads as a score
    # over all 6 -- Athene scored F1 1.000 on 2 datasets and looked like the
    # best model in the benchmark.  A cell is only comparable to another cell
    # covering the same datasets.
    ndatasets = collections.defaultdict(set)
    npos = collections.defaultdict(int)
    for c in ok:
        ndatasets[(c["model"], c["condition"])].add(c["dataset"])
        npos[(c["model"], c["condition"])] += sum(c["truth"].values())
    # Completeness is relative to what the cell was RUN over, not to a constant.
    # With 6 hardcoded, every 10-dataset cell reads PARTIAL and every 6-dataset
    # cell over the expansion set reads complete when it is not.  Take the max
    # coverage any cell of that model achieved as its intended scope.
    scope = collections.defaultdict(int)
    for (m, cond) in ndatasets:
        scope[m] = max(scope[m], len(ndatasets[(m, cond)]))

    print(f"{'model':<42}{'C':>2}{'P':>7}{'R':>7}{'F1':>7}{'vs B3':>8}{'abst':>6}"
          f"{'blind':>7}{'cov':>8}")
    print("-" * 96)
    rows = []
    for (m, cond), v in sorted(agg.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        p, r, f = prf(v["tp"], v["fp"], v["fn"])
        bh, bn = blind_hits[(m, cond)]
        nd = len(ndatasets[(m, cond)])
        FULL = scope[m]
        full = nd == FULL
        rows.append((m, cond, p, r, f, nd, npos[(m, cond)]))
        flag = "" if full else "  PARTIAL"
        print(f"{m.split('/')[-1][:40]:<42}{cond:>2}{p:>7.3f}{r:>7.3f}{f:>7.3f}"
              f"{f-B3_F1:>+8.3f}{v['abstain']:>6}{bh:>4}/{bn}"
              f"{nd:>5}/{FULL} ds{flag}")
    part = [x for x in rows if x[5] != scope[x[0]]]
    if part:
        print(f"\n  {len(part)} cell(s) marked PARTIAL cover fewer datasets than "
              f"the same model's fullest run and are NOT comparable to it:")
        for m, c, p, r, f, nd, np_ in part:
            print(f"    {m.split('/')[-1][:38]:<40}C{c}  {nd}/{scope[m]} datasets, "
                  f"{np_} positives -> F1 {f:.3f} is over a subset")
    print(f"\n  B3 baseline (tuned |correlation|): F1 {B3_F1:.3f}")
    print("  'blind' = of the 4 columns correlation cannot see, how many were found")

    beat = [x for x in rows if x[4] > B3_F1]
    print(f"\n  cells beating the baseline: {len(beat)}/{len(rows)}")
    for m, c, p, r, f in sorted(beat, key=lambda x: -x[4])[:5]:
        print(f"    {m.split('/')[-1][:40]:<42}C{c}  F1 {f:.3f}")

    print("\nmost-missed positives (across all parsed cells):")
    miss = collections.Counter()
    for c in ok:
        for col in score_cell(c)["missed"]:
            miss[(c["dataset"], col)] += 1
    for (ds, col), n in miss.most_common(12):
        tag = "  <- correlation-blind" if (ds, col) in BLIND else ""
        print(f"   {ds:<10}{col:<26}missed in {n} cells{tag}")

    print("\nmost-common false positives (legitimate columns flagged):")
    fpc = collections.Counter()
    for c in ok:
        for col in score_cell(c)["falsely"]:
            fpc[(c["dataset"], col)] += 1
    for (ds, col), n in fpc.most_common(10):
        print(f"   {ds:<10}{col:<26}flagged in {n} cells")


if __name__ == "__main__":
    main()
