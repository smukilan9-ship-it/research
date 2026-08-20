"""Every figure section X needs, computed once, from the certified cache.

Real-corpus numbers come from verify_paper's own cells_for() and spec_bundle,
so they agree with NUMBERS.txt by construction rather than by coincidence.
Stratum E numbers come from synth/score.py, loaded BY PATH -- `import runner`
pulls the repository-root score.py into sys.modules, so a plain `import score`
silently returns the wrong module.

Matched datasets only: a model contributes to a real-vs-synthetic delta only
where it answered the same Stratum A datasets at both conditions.
"""
import glob, importlib.util, json, sys
sys.path.insert(0, "."); sys.path.insert(0, "synth")
import runner as RN, verify_paper as V, export as EX
from salvage import parse

_s = importlib.util.spec_from_file_location("synth_score", "synth/score.py")
SC = importlib.util.module_from_spec(_s); _s.loader.exec_module(SC)

SYN = set(EX.names())
BUND = {d.upper(): RN.spec_bundle(d) for d in RN.ALLSETS}
B3_REAL, B3_SYN = 0.630, 0.665


def synth_f1(model, cond):
    got = SC.cells(model); tp = fp = fn = 0; n = 0
    for name in EX.names():
        g = got.get((name, cond))
        if not g: continue
        n += 1; b = EX.bundle(name, want_sample=False)
        for col, pos in b["truth"].items():
            fl = g.get(col) == "UNAVAILABLE"
            if pos: tp += fl; fn += not fl
            elif fl: fp += 1
    if n < len(SYN) or tp + fn == 0: return None
    p = tp/(tp+fp) if tp+fp else 0; r = tp/(tp+fn) if tp+fn else 0
    return 2*p*r/(p+r) if p+r else 0


def real_f1(model, cond, keep=None):
    cells = V.cells_for(model); tp = fp = fn = 0; ds = set()
    for (d, c, s), got in cells.items():
        if c != cond or d not in BUND: continue
        if keep is not None and d not in keep: continue
        ds.add(d)
        for col, pos in BUND[d]["truth"].items():
            v = got.get(col, {})
            v = v.get("verdict") if isinstance(v, dict) else v
            fl = v == "UNAVAILABLE"
            if pos: tp += fl; fn += not fl
            elif fl: fp += 1
    if tp + fn == 0: return None, ds
    p = tp/(tp+fp) if tp+fp else 0; r = tp/(tp+fn) if tp+fn else 0
    return (2*p*r/(p+r) if p+r else 0), ds


def main():
    print("=" * 78)
    print("SECTION X FIGURES — real corpus (Stratum A) against Stratum E")
    print("=" * 78)
    print(f"  baselines: B3 pooled 0.630 real, {B3_SYN:.3f} synthetic\n")
    print(f'{"model":<40}{"realC1":>8}{"synC1":>7}{"d":>8}{"realC6":>8}{"synC6":>7}{"d":>8}')
    rows = []
    for m in V.MODELS:
        rc1, ds1 = real_f1(m, 1); rc6, ds6 = real_f1(m, 6)
        sc1, sc6 = synth_f1(m, 1), synth_f1(m, 6)
        if None in (rc1, rc6, sc1, sc6): 
            print(f'{m[:38]:<40}  incomplete on the real corpus — excluded')
            continue
        rows.append((m, rc1, sc1, rc6, sc6))
        print(f'{m[:38]:<40}{rc1:>8.3f}{sc1:>7.3f}{sc1-rc1:>+8.3f}'
              f'{rc6:>8.3f}{sc6:>7.3f}{sc6-rc6:>+8.3f}')
    if not rows: return
    n = len(rows)
    print(f"\n  {n} models with matched real and synthetic cells")
    print(f"  mean delta C1 {sum(s-r for _,r,s,_,_ in rows)/n:+.3f}"
          f"   mean delta C6 {sum(s-r for _,_,_,r,s in rows)/n:+.3f}")
    print(f"  best real C1 {max(r for _,r,_,_,_ in rows):.3f}"
          f"   best synth C1 {max(s for _,_,s,_,_ in rows):.3f}")
    print(f"  best real C6 {max(r for _,_,_,r,_ in rows):.3f}"
          f"   best synth C6 {max(s for _,_,_,_,s in rows):.3f}")
    up = [m for m,r,s,_,_ in rows if s > r]
    print(f"\n  models that GAIN on unseen tables at C1: {len(up)}/{n}")
    for m in up: print(f"     {m}")


if __name__ == "__main__":
    main()
