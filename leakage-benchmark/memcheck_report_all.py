"""Cross-model memorisation table: recall of leaking columns, per model.

WHAT THE SINGLE-MODEL REPORT COULD NOT ANSWER

  memcheck_report.py produced the bound the paper reports -- gemini-3.5-flash
  recalls 33% of columns but only 19% of the LEAKING ones.  That is one model's
  memorisation profile being used to bound fourteen models' detection scores,
  and a reviewer is entitled to ask the obvious question: is the model that
  scores best also the model that remembers most?

  One model cannot answer it.  This reports every model on the same axis, so
  the answer is a comparison rather than an assumption.

THE MEASUREMENT THAT MATTERS IS NOT "IS THIS DATASET MEMORISED"

  It is whether the model can recall THE COLUMNS WHOSE DETECTION WE SCORE.  A
  model that reproduces Titanic's canonical schema but cannot produce `boat` or
  `body` has memorised something, and not the thing that would inflate our
  numbers.  So every row reports two rates side by side:

    all      fraction of the dataset's columns the model completed from memory
    POS      fraction of the LEAKING columns it completed

  POS is the one that bounds the detection result.  `all` is context: a model
  with high `all` and low POS is recalling the ordinary schema, which is not a
  threat to a benchmark whose positives are the unusual columns.

ERRORS ARE NOT ZEROS

  A cell that failed with a quota error is excluded from both numerator and
  denominator and counted separately.  Reading an API failure as "recalled
  nothing" is how the first memcheck campaign reported 55 HTTP 429s as data.
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
from memcheck_report import positives, parse_tuple, names

SRC = HERE + "memcheck_all.json"


def main():
    res = json.load(open(SRC))
    pos = positives()
    rows = []
    print("=" * 92)
    print("FEATURE-NAMES TEST across models — can the model complete the "
          "column list from memory?")
    print("=" * 92)
    print(f"{'model':<44}{'datasets':>9}{'all cols':>10}{'LEAKING cols':>14}"
          f"{'errors':>8}")
    for label in sorted(res):
        tr = tt = pr = pt = nds = err = 0
        permodel = {}
        for ds, cell in res[label].items():
            r = cell.get("feature_names_test")
            if not r:
                continue
            if "error" in r:
                err += 1
                continue
            t = parse_tuple(r.get("result", ""))
            if not t:
                continue
            _, truth, pred = t
            T = names(truth)
            P = {n.lower() for n in names(pred)}
            hit = [n for n in T if n.lower() in P]
            p_all = [n for n in T if n in pos.get(ds, set())]
            p_hit = [n for n in p_all if n.lower() in P]
            tr += len(hit); tt += len(T)
            pr += len(p_hit); pt += len(p_all)
            nds += 1
            permodel[ds] = (len(p_hit), len(p_all))
        if not nds:
            print(f"  {label[:42]:<44}{'-':>9}{'-':>10}{'-':>14}{err:>8}")
            continue
        print(f"  {label[:42]:<44}{nds:>9}{tr/max(tt,1):>9.0%}"
              f"{f'{pr}/{pt} = {pr/max(pt,1):.0%}':>14}{err:>8}")
        rows.append((label, tr / max(tt, 1), pr, pt, permodel))

    if rows:
        print("\n" + "-" * 92)
        print("Datasets on which NO model recalled any leaking column "
              "(safe for the detection claim):")
        allds = sorted({d for _, _, _, _, pm in rows for d in pm})
        clean = [d for d in allds
                 if all(pm.get(d, (0, 0))[0] == 0 for _, _, _, _, pm in rows)]
        print(f"  {', '.join(clean) if clean else '(none)'}")
        print("\nDatasets where at least one model recalled a leaking column:")
        for d in allds:
            worst = max((pm.get(d, (0, 0))[0] for _, _, _, _, pm in rows),
                        default=0)
            tot = max((pm.get(d, (0, 0))[1] for _, _, _, _, pm in rows),
                      default=0)
            if worst:
                who = [lab for lab, _, _, _, pm in rows
                       if pm.get(d, (0, 0))[0] == worst]
                print(f"  {d:<12}{worst}/{tot} leaking columns recalled by "
                      f"{', '.join(w[:28] for w in who)}")

    for test, title in (
            ("row_completion_test",
             "ROW COMPLETION — verbatim data rows, the strongest evidence"),
            ("header_test", "HEADER TEST — verbatim CSV header"),
            ("dataset_name_test",
             "DATASET-NAME TEST — recognition, weaker than memorisation")):
        print("\n" + "=" * 92); print(title); print("=" * 92)
        for label in sorted(res):
            ok = err = 0
            for ds, cell in res[label].items():
                r = cell.get(test)
                if not r:
                    continue
                if "error" in r:
                    err += 1
                else:
                    ok += 1
            if ok or err:
                print(f"  {label[:42]:<44}{ok:>4} completed{err:>6} errored")
    print("\nA cell that errored is excluded from every rate above and counted "
          "separately.\nAn API failure is not a memorisation result.")


if __name__ == "__main__":
    main()
