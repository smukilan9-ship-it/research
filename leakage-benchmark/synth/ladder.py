"""Three-rung nemotron ladder.  POST HOC, off-roster (PREREG Amendment 2).

Loads synth/score.py by PATH, not by name: `import runner` pulls the
repository-root score.py into sys.modules first, so a plain `import score`
silently returns the wrong module -- which is how this printed an
AttributeError rather than a wrong number.  Loud beats subtle.
"""
import glob, importlib.util, json, sys
sys.path.insert(0, "."); sys.path.insert(0, "synth")
import export as EX, runner as RN
from salvage import parse

spec = importlib.util.spec_from_file_location("synth_score", "synth/score.py")
SC = importlib.util.module_from_spec(spec); spec.loader.exec_module(SC)

SYNTH = EX.names(); STRAT_A = [d.upper() for d in RN.ALLSETS]; B3_SYN = 0.717
LADDER = [("nano  30B-a3b", "nvidia/nemotron-3-nano-30b-a3b::high"),
          ("super 120B-a12b", "nvidia/nemotron-3-super-120b-a12b::high"),
          ("ultra 550B-a55b", "nvidia/nemotron-3-ultra-550b-a55b::high")]

def f1(model, synth, cond, restrict):
    out, stamp = {}, {}
    for f in sorted(glob.glob("responses/*.json")):
        try: r = json.load(open(f))
        except Exception: continue
        if r.get("paraphrase") or r.get("model") != model: continue
        if (r.get("dataset") in set(SYNTH)) != synth: continue
        d, _ = parse(r.get("raw", "") or "")
        if not d: continue
        k = (r["dataset"], r["condition"], r["seed"]); this = (r.get("ts") or "", f)
        if k in stamp and this < stamp[k]: continue
        stamp[k] = this
        out[k] = {c["name"]: c.get("verdict") for c in d["columns"]
                  if isinstance(c, dict) and c.get("name")}
    tp = fp = fn = 0
    for (d, c, s), g in out.items():
        if c != cond or d not in restrict: continue
        try: b = EX.bundle(d, want_sample=False) if synth else RN.spec_bundle(d.lower())
        except Exception: continue
        if not (set(g) & set(b["truth"])): continue
        for col, pos in b["truth"].items():
            fl = g.get(col) == "UNAVAILABLE"
            if pos: tp += fl; fn += not fl
            elif fl: fp += 1
    if tp + fn == 0: return None
    p = tp/(tp+fp) if tp+fp else 0; r = tp/(tp+fn) if tp+fn else 0
    return 2*p*r/(p+r) if p+r else 0

print(f'{"rung":<17}{"cells":>7}{"C1REA":>7}{"C1CON":>7}{"C6REA":>7}{"D1":>7}{"D2":>7}'
      f'{"F1syn":>8}{"F1real":>8}{"delta":>8}{"vsB3":>8}')
for tag, m in LADDER:
    got = SC.cells(m)
    h1, t1, _ = SC.recall_by_subtype(got, 1, SYNTH)
    h6, t6, _ = SC.recall_by_subtype(got, 6, SYNTH)
    c1r = SC._pct(h1["REASON"], t1["REASON"]); c1c = SC._pct(h1["CONSEQUENCE"], t1["CONSEQUENCE"])
    c6r = SC._pct(h6["REASON"], t6["REASON"])
    fs = f1(m, True, 1, set(SYNTH)); fr = f1(m, False, 1, set(STRAT_A))
    dl = (fs - fr) if (fs is not None and fr is not None) else float("nan")
    print(f'{tag:<17}{len(got):>4}/40{c1r:>6.1f}%{c1c:>6.1f}%{c6r:>6.1f}%'
          f'{c1c-c1r:>+7.1f}{c6r-c1r:>+7.1f}{fs:>8.3f}'
          f'{(fr if fr is not None else float("nan")):>8.3f}{dl:>+8.3f}{fs-B3_SYN:>+8.3f}')
