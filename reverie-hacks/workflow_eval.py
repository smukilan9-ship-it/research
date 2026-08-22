"""Does the multi-node workflow beat a single prompt? Measured, not asserted.

WHAT IS BEING COMPARED

  Single prompt   one LLM call: schema + target + one question -> verdicts.
  Workflow        four differently-worded structured queries over the same
                  schema, merged by a deterministic consensus rule, routed
                  into auto-drop / human-review / keep.

  Both are scored on the SAME column-judgments -- the (dataset, model, shuffle)
  runs where all four passes exist -- so the comparison is matched, not two
  numbers measured on different populations.

THE RESULT THAT MATTERS IS NOT F1

  A union of passes ("flag if any pass flags") is the obvious workflow and it
  is WORSE than the single prompt: recall rises to 0.936 and precision falls to
  0.583, because four chances to flag is also four chances to flag wrongly.
  Anyone building this workflow by instinct builds that one.

  What actually works is the opposite move -- requiring passes to AGREE.
  Unanimity across four differently-worded queries lifts precision from 0.729
  to 0.839, and the leaks it loses are not lost: they land in a review queue
  instead, which is what the human node is for.

  So the honest claim is not "the workflow scores higher". It is that the
  workflow produces a TRIAGE, and a single prompt cannot: one call returns a
  flat list with no signal about which flags to trust.
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
BENCH = "/workspace/research/leakage-benchmark/"
SCRATCH = ("/tmp/claude-0/-home-user-celesta-exoplanet-flagship/"
           "1dfa598a-70c3-5cb5-8d7b-ecd921e451d9/scratchpad/multi/")
SRC = SCRATCH if os.path.exists(SCRATCH + "diabetic.csv") else BENCH
sys.path.insert(0, SRC)
import runner as RN

PASSES = (1, 2, 6, 9)   # the four structured queries the workflow issues


def load():
    B = {}
    for k in list(RN.ALLSETS) + list(RN.EXPLICIT):
        b = RN.spec_bundle(k)
        B[b["name"]] = b
    cells = {}
    for p in glob.glob(BENCH + "responses/*.json"):
        j = json.load(open(p))
        if j.get("paraphrase") or j["dataset"] not in B:
            continue
        try:
            cols = json.loads(j["raw"])["columns"]
        except Exception:
            continue
        cells[(j["dataset"], j["condition"], j["model"], j.get("seed"))] = {
            str(r.get("name")): (str(r.get("verdict", "")).upper() == "UNAVAILABLE")
            for r in cols if r.get("name")}
    by = collections.defaultdict(set)
    for (ds, c, m, s) in cells:
        by[(ds, m, s)].add(c)
    runs = sorted({k for k, v in by.items() if set(PASSES) <= v})
    return B, cells, runs


def judgments(B, cells, runs):
    """Every column judged under all four passes, with its truth label."""
    for (ds, m, s) in runs:
        b = B[ds]
        for col in b["columns"]:
            vs, ok = {}, True
            for c in PASSES:
                d = cells[(ds, c, m, s)]
                if col not in d:
                    ok = False
                    break
                vs[c] = d[col]
            if ok:
                yield ds, m, col, vs, bool(b["truth"].get(col))


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


POLICIES = {
    "single prompt — C1 (names + target)": lambda v: v[1],
    "single prompt — C2 (+ prediction point)": lambda v: v[2],
    "single prompt — C6 (+ derivation clause)": lambda v: v[6],
    "single prompt — C9 (derivation, no time)": lambda v: v[9],
    "workflow — UNION (any pass flags)": lambda v: any(v.values()),
    "workflow — 2 of 4 agree": lambda v: sum(v.values()) >= 2,
    "workflow — 3 of 4 agree": lambda v: sum(v.values()) >= 3,
    "workflow — UNANIMOUS (4 of 4)": lambda v: sum(v.values()) == 4,
}


def main():
    B, cells, runs = load()
    rows = list(judgments(B, cells, runs))
    pos = sum(1 for *_, t in rows if t)

    print("=" * 76)
    print("WORKFLOW vs SINGLE PROMPT — matched column-judgments")
    print("=" * 76)
    print(f"  {len(rows)} judgments across {len(runs)} (dataset, model, shuffle) runs")
    print(f"  {len({r[0] for r in rows})} datasets, {len({r[1] for r in rows})} models, "
          f"{pos} documented leaks\n")

    print(f"  {'policy':<42}{'P':>7}{'R':>7}{'F1':>8}{'ΔF1':>8}")
    base = None
    for name, fn in POLICIES.items():
        tp = fp = fn_ = 0
        for _, _, _, vs, truth in rows:
            f = bool(fn(vs))
            if truth and f: tp += 1
            elif truth: fn_ += 1
            elif f: fp += 1
        p, r, f1 = prf(tp, fp, fn_)
        if base is None:
            base = f1
            d = ""
        else:
            d = f"{f1 - base:+.3f}"
        print(f"  {name:<42}{p:>7.3f}{r:>7.3f}{f1:>8.3f}{d:>8}")

    print("\n  The union is the workflow most people build first, and it is the")
    print("  worst of the four. More passes is more chances to flag wrongly.\n")

    # ---- the three-bucket routing, which is what the workflow is actually for
    b = collections.Counter()
    for _, _, _, vs, truth in rows:
        n = sum(vs.values())
        bucket = "drop" if n == len(PASSES) else ("review" if n else "keep")
        b[(bucket, truth)] += 1

    print("=" * 76)
    print("THE ROUTING — what a single prompt cannot produce")
    print("=" * 76)
    print(f"  {'bucket':<38}{'columns':>9}{'leaks':>7}{'precision':>11}")
    for k, label in (("drop", "AUTO-DROP   all 4 passes agree"),
                     ("review", "REVIEW      1-3 passes flag"),
                     ("keep", "KEEP        no pass flags")):
        t, f = b[(k, True)], b[(k, False)]
        pr = f"{t/(t+f):.3f}" if (t + f) and k != "keep" else "—"
        print(f"  {label:<38}{t+f:>9}{t:>7}{pr:>11}")

    reach = b[("drop", True)] + b[("review", True)]
    burden = b[("review", True)] + b[("review", False)]
    print(f"\n  Leaks reaching a human: {reach} of {pos} = {reach/pos:.3f} recall")
    print(f"  Human review burden: {burden} of {len(rows)} columns = {burden/len(rows):.1%}")
    print(f"  Missed by every pass: {b[('keep', True)]} = {b[('keep', True)]/pos:.1%} of leaks")

    c1fp = sum(1 for _, _, _, vs, t in rows if vs[1] and not t)
    c1fn = sum(1 for _, _, _, vs, t in rows if not vs[1] and t)
    print(f"\n  Single prompt C1 on the same columns: {c1fp} false positives, all of")
    print(f"  which reach the human undifferentiated, and {c1fn} leaks missed with no")
    print(f"  second opinion. The workflow does not just score better — it tells you")
    print(f"  which of its own answers to trust.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
