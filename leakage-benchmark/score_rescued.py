"""Score the temperature-rescued cells SEPARATELY, and never anywhere else.

WHY THIS IS ITS OWN SCRIPT

Two cells in this corpus cannot be obtained at the temperature every other cell
was run at.  `gemini-3.5-flash` decodes greedily at `temperature = 0.0`, falls
into a repetition loop inside its own thinking channel, and spends the whole
output budget before emitting an answer -- 46,080 thinking tokens against a
16,000-token budget it was given and a 48,000-token ceiling, leaving 1,916 for
the answer.  Greedy decoding is deterministic, so the loop reproduces exactly
and no number of retries recovers the cell.  At `temperature = 0.7` the same
prompt completes: 5,119 thinking tokens, all 40 columns, `finishReason: STOP`.

So the choice was between a permanently missing cell and a cell obtained under
a different decoding regime.  We take the second and quarantine it HERE, in its
own arm, because a cell run at a different temperature is not comparable with
the ones it would be pooled against -- and pooling it anyway is the precise
failure this paper is about.  The label carries the regime
(`::vertex-think16000-t0.7`), `runner.py` puts the temperature in the cache key,
and `verify_paper.cells_for` refuses the cross-regime substring match, so the
isolation holds in three independent places rather than by anyone remembering.

The two CRIME C9 cells that DO exist at both temperatures are the control: they
say how much of any difference is the temperature rather than the cell.

    python score_rescued.py
"""
import sys
import verify_paper as V

T07 = "gemini-3.5-flash::vertex-think16000-t0.7"
T00 = "gemini-3.5-flash::vertex-think16000-t0.0"


def flags(cell):
    return {n for n, c in cell.items() if c.get("verdict") == "UNAVAILABLE"}


def main():
    main_b, expl_b = V.corpus()
    bundles = dict(main_b)
    bundles.update(expl_b)

    hot = V.cells_for(T07)
    cold = V.cells_for(T00)
    if not hot:
        sys.exit("no t=0.7 cells cached; nothing to score")

    print("=" * 78)
    print("TEMPERATURE-RESCUED CELLS — scored alone, pooled with nothing")
    print("=" * 78)
    print(f"  arm: {T07}")
    print(f"  {len(hot)} cell(s) at t=0.7; the rest of the corpus is t=0.0\n")

    # ---- the control: cells answered at BOTH temperatures ------------------
    both = sorted(set(hot) & set(cold))
    print(f"--- agreement control: {len(both)} cell(s) answered at both temperatures")
    if not both:
        print("    none -- the rescued cells have no t=0.0 counterpart by")
        print("    construction, so there is no direct check and the arm is")
        print("    reported as its own number and nothing else.")
    for k in both:
        a, b = flags(cold[k]), flags(hot[k])
        inter, union = a & b, a | b
        j = len(inter) / len(union) if union else 1.0
        print(f"    {k[0]:<9} C{k[1]} s{k[2]}   t0.0 flagged {len(a):>3}   "
              f"t0.7 flagged {len(b):>3}   Jaccard {j:.3f}")
        if a - b:
            print(f"        only at t=0.0: {sorted(a - b)[:6]}")
        if b - a:
            print(f"        only at t=0.7: {sorted(b - a)[:6]}")

    # ---- the rescued cells, scored on their own ----------------------------
    rescued = sorted(set(hot) - set(cold))
    print(f"\n--- the {len(rescued)} rescued cell(s), scored alone")
    if not rescued:
        print("    none")
        return 0
    tp = fp = fn = 0
    for k in rescued:
        d, cond, seed = k
        if d not in bundles:
            print(f"    {d} not in either corpus; skipped")
            continue
        truth = bundles[d]["truth"]
        got = hot[k]
        if not (set(got) & set(truth)):
            print(f"    JOIN ERROR {d} C{cond}: no verdict key matches truth")
            continue
        a = b = c = 0
        for col, pos in truth.items():
            fl = got.get(col, {}).get("verdict") == "UNAVAILABLE"
            if pos and fl:
                a += 1
            elif pos:
                c += 1
            elif fl:
                b += 1
        tp += a; fp += b; fn += c
        p = a / (a + b) if a + b else 0.0
        r = a / (a + c) if a + c else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        print(f"    {d:<9} C{cond} s{seed}   P {p:.3f}  R {r:.3f}  F1 {f:.3f}   "
              f"tp {a}  fp {b}  fn {c}   ({len(truth)} columns)")
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    print(f"\n    POOLED over the rescued cells only: "
          f"P {p:.3f}  R {r:.3f}  F1 {f:.3f}   tp {tp}  fp {fp}  fn {fn}")
    print("\n    This number belongs in no table that also contains a t=0.0")
    print("    cell.  It is reported so the cells are not silently absent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
