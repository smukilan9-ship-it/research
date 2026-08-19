"""Same question, but on MATCHED cells only.

The first pass compared each model's C1 against its C6 over whatever datasets
it happened to answer at each -- 41 flags for one model against 110 for
another, which is a difference of two numbers computed over different corpora.
That is the exact accounting error verify_paper.prf() carries a `refused` set
to prevent, and it produced a 0.0 -> 45.2 that may be nothing but a change of
denominator.  Here a dataset counts only if the model answered it at BOTH
conditions, and every denominator is printed.
"""
import sys
sys.path.insert(0, ".")
import verify_paper as V
import runner as RN

BUND = {}
for d in RN.ALLSETS:
    try: BUND[d.upper()] = RN.spec_bundle(d)
    except Exception: pass

MODELS = [("gpt-5.6-sol-xhigh", "+42.5"),
          ("nemotron-3-super-120b-a12b::high", "+30.0"),
          ("claude-opus-5-max", "+25.0"),
          ("grok-4.1-fast-non-reasoning::vertex-t0.0", "+20.0"),
          ("deepseek-v4-flash-0731::high", "+2.5"),
          ("grok-4.20-non-reasoning::vertex-t0.0", "+2.5")]

def stats(model):
    cells = V.cells_for(model)
    at = {c: {d for (d, cc, s) in cells if cc == c and d in BUND} for c in (1, 6)}
    keep = at[1] & at[6]                      # MATCHED datasets only
    out = {}
    for cond in (1, 6):
        h = t = flags = neg = negflag = 0
        for (d, c, s), got in cells.items():
            if c != cond or d not in keep: continue
            for col, pos in BUND[d]["truth"].items():
                v = got.get(col, {})
                v = v.get("verdict") if isinstance(v, dict) else v
                fl = v == "UNAVAILABLE"
                flags += fl
                if not pos:
                    neg += 1; negflag += fl
                elif V.subtype(d, col) == "REASON":
                    t += 1; h += fl
        out[cond] = dict(h=h, t=t, flags=flags,
                         fpr=100.0*negflag/neg if neg else 0.0)
    return keep, out

print(f'{"model":<40}{"ds":>4}{"REASON C1":>13}{"REASON C6":>13}{"D2":>8}{"flags":>12}{"FPR%":>13}  synthD2')
for m, tag in MODELS:
    keep, s = stats(m)
    if 1 not in s or 6 not in s or not s[1]["t"]:
        print(f'{m[:38]:<40}  no matched C1/C6 on Stratum A'); continue
    a, b = s[1], s[6]
    pa = 100.0*a["h"]/a["t"]; pb = 100.0*b["h"]/b["t"]
    print(f'{m[:38]:<40}{len(keep):>4}'
          f'{a["h"]:>6}/{a["t"]:<3}{pa:>5.1f}%'.ljust(0) +
          f'{b["h"]:>6}/{b["t"]:<3}{pb:>5.1f}%{pb-pa:>+8.1f}'
          f'{a["flags"]:>6}->{b["flags"]:<5}{a["fpr"]:>6.1f}->{b["fpr"]:<6.1f}  {tag}')
