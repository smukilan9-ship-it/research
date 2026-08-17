"""Recall by subtype x condition -- the test of the paper's central claim.

The claim: models operationalise leakage as TIMING, so they catch columns that
are merely later than the prediction point, and miss columns that are
temporally prior but record WHY the label was assigned (REASON).  C6 states the
derivation criterion explicitly and should lift REASON specifically.

Prediction, written before the table is read:
  C1   REASON recall LOW, CONSEQUENCE/TIMING recall HIGH
  C6   REASON recall RISES sharply; CONSEQUENCE/TIMING roughly unchanged
  If REASON and the others move together, the mechanism is wrong and the
  timing/derivation story does not survive.

Precision is reported alongside, because a lift bought by flagging everything
is not a lift.  Precision is a per-cell property (it involves negatives, which
have no subtype), so it is shown once per condition, not per subtype.
"""
import json, os, glob, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
from salvage import parse
import runner as RN
from subtypes import subtype

ORDER = ["REASON", "CONSEQUENCE", "TIMING", "CONTESTED"]


def main():
    want_para = "--paraphrase" in sys.argv
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--model="):
            only = a.split("=", 1)[1]

    bundles, alias_back = {}, {}
    for k in RN.ALLSETS:
        try:
            b = RN.spec_bundle(k)
            bundles[b["name"]] = b
        except Exception:
            pass
    if want_para:
        # In the paraphrase arm the truth dict is keyed on ALIASES, so looking a
        # subtype up by alias returns None and every positive lands in an
        # uncoded bucket -- the table came out empty.  Same failure mode as the
        # BLIND denominator: a join that silently matches nothing.
        import paraphrase as PP
        para = {}
        for n, b in bundles.items():
            pb = PP.apply_to(b)
            para[n] = pb
            for a, orig in pb["alias"].items():
                alias_back[(n, a)] = orig
        bundles = para

    newest = {}
    for f in glob.glob(HERE + "responses/*.json"):
        rec = json.load(open(f))
        if bool(rec.get("paraphrase")) != want_para:
            continue
        if only and only not in rec["model"]:
            continue
        k = (rec["model"], rec["dataset"], rec["condition"], rec.get("seed"))
        if k not in newest or rec.get("ts", "") > newest[k].get("ts", ""):
            newest[k] = rec

    # (model, cond, subtype) -> [found, total];  (model, cond) -> [tp, fp]
    hit = collections.defaultdict(lambda: [0, 0])
    prec = collections.defaultdict(lambda: [0, 0])
    seen_ds = collections.defaultdict(set)
    for rec in newest.values():
        d, _ = parse(rec.get("raw", ""))
        if not d:
            continue
        b = bundles.get(rec["dataset"])
        if not b:
            continue
        got = {c["name"]: c.get("verdict") for c in d["columns"]
               if isinstance(c, dict) and c.get("name")}
        if got and not (set(got) & set(b["truth"])):
            continue
        m, cond = rec["model"], rec["condition"]
        seen_ds[(m, cond)].add(rec["dataset"])
        for col, is_pos in b["truth"].items():
            flagged = got.get(col) == "UNAVAILABLE"
            if is_pos:
                key = alias_back.get((rec["dataset"], col), col)
                st = subtype(rec["dataset"], key) or "UNCODED"
                hit[(m, cond, st)][1] += 1
                if flagged:
                    hit[(m, cond, st)][0] += 1
                    prec[(m, cond)][0] += 1
            elif flagged:
                prec[(m, cond)][1] += 1

    models = sorted({k[0] for k in hit})
    print(f"{'PARAPHRASED' if want_para else 'ORIGINAL'} runs -- recall by subtype\n")
    for m in models:
        conds = sorted({k[1] for k in hit if k[0] == m})
        print(f"{m}")
        head = "".join(f"{s[:11]:>14}" for s in ORDER)
        print(f"   {'cond':<6}{head}{'precision':>12}{'ds':>5}")
        for c in conds:
            row = ""
            for st in ORDER:
                f_, t = hit[(m, c, st)]
                row += f"{(f'{f_}/{t}'):>9}{(f'{f_/t:.0%}' if t else '  -'):>5}"
            tp, fp = prec[(m, c)]
            p = tp / (tp + fp) if tp + fp else 0.0
            print(f"   C{c:<5}{row}{p:>12.3f}{len(seen_ds[(m,c)]):>5}")
        # the specific comparison the claim rests on
        if 1 in conds and 6 in conds:
            r1 = hit[(m, 1, "REASON")]
            r6 = hit[(m, 6, "REASON")]
            o1 = [sum(hit[(m, 1, s)][i] for s in ("CONSEQUENCE", "TIMING"))
                  for i in (0, 1)]
            o6 = [sum(hit[(m, 6, s)][i] for s in ("CONSEQUENCE", "TIMING"))
                  for i in (0, 1)]
            def pc(x):
                return f"{x[0]/x[1]:.0%}" if x[1] else "-"
            print(f"   -> REASON {pc(r1)} (C1) -> {pc(r6)} (C6)   "
                  f"CONSEQUENCE+TIMING {pc(o1)} -> {pc(o6)}")
        print()


if __name__ == "__main__":
    main()
