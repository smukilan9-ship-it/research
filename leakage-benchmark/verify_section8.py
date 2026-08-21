"""Hand-audit of every quantity in section 8, recomputed from primary sources.

WHY THIS EXISTS ALONGSIDE prose_pins.py

  `prose_pins.py` pins prose to NUMBERS by regex.  That is worth having, but a
  regex has a failure mode this project has already been bitten by twice: when
  the prose moves, the pin stops MATCHING rather than failing, and a pin that
  silently stops matching checks nothing at all.  It also only covers the
  quantities somebody remembered to pin -- seven, for section 8.

  This file takes the opposite approach.  Each claim is written out BY HAND as
  a literal below, exactly as the manuscript states it, and then recomputed
  from the frozen tables and the response cache.  Nothing is extracted from
  PAPER.md, so nothing can silently stop matching; if the manuscript and this
  file drift apart, that is a diff a human can see.

  It found three errors in the first draft of section 8 that the pins did not:
    * "two tables carry no REASON column"  -- one does (TOWER_OUTAGE); a second
      lacks CONSEQUENCE (TRIAL_WITHDRAWAL).  Misread from STATUS.md.
    * "spread collapses by a factor of 3.2" -- 3.1.  I inverted a rounded 0.32
      instead of dividing the unrounded standard deviations.
    * "2,428 abstentions in 2,448 judgments" -- that is the FOUR-arm total.
      Section 8 reports three arms: 1,816 in 1,836.

    python3 verify_section8.py
"""
import collections
import glob
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "."); sys.path.insert(0, "synth")
import runner as RN                                          # noqa: E402
import verify_paper as V                                     # noqa: E402
import export as EX                                          # noqa: E402
from salvage import parse                                    # noqa: E402
from scipy import stats                                      # noqa: E402

BUND = {d.upper(): RN.spec_bundle(d) for d in RN.ALLSETS}
SYN = set(EX.names())
RESULTS = []


def claim(text, stated, actual, tol=0.0):
    ok = (abs(stated - actual) <= tol
          if isinstance(stated, (int, float)) and isinstance(actual, (int, float))
          else stated == actual)
    RESULTS.append((ok, text, stated, actual))


# ---------------------------------------------------------------- cache reads
def synth_cells(model, cond):
    out, stamp = {}, {}
    for f in sorted(glob.glob("responses/*.json")):
        try: r = json.load(open(f))
        except Exception: continue
        if r.get("dataset") not in SYN or r.get("paraphrase"): continue
        if r.get("condition") != cond: continue
        nm = r["model"]
        if nm != model:
            if model not in nm: continue
            if "::" in nm and "::" not in model: continue
        d, _ = parse(r.get("raw", "") or "")
        if not d: continue
        k = r["dataset"]; this = (r.get("ts") or "", f)
        if k in stamp and this < stamp[k]: continue
        stamp[k] = this
        out[k] = {x["name"]: x.get("verdict") for x in d["columns"]
                  if isinstance(x, dict) and x.get("name")}
    return out


def f1_synth(model, cond):
    o = synth_cells(model, cond)
    if len(o) < len(SYN): return None
    tp = fp = fn = 0
    for n, g in o.items():
        b = EX.bundle(n, want_sample=False)
        for col, pos in b["truth"].items():
            fl = g.get(col) == "UNAVAILABLE"
            if pos: tp += fl; fn += not fl
            elif fl: fp += 1
    if tp + fn == 0: return None
    p = tp/(tp+fp) if tp+fp else 0; r = tp/(tp+fn) if tp+fn else 0
    return 2*p*r/(p+r) if p+r else 0


def f1_real(model, cond):
    cells = V.cells_for(model); tp = fp = fn = 0
    for (d, cc, s), got in cells.items():
        if cc != cond or d not in BUND: continue
        for col, pos in BUND[d]["truth"].items():
            v = got.get(col, {})
            v = v.get("verdict") if isinstance(v, dict) else v
            fl = v == "UNAVAILABLE"
            if pos: tp += fl; fn += not fl
            elif fl: fp += 1
    if tp + fn == 0: return None
    p = tp/(tp+fp) if tp+fp else 0; r = tp/(tp+fn) if tp+fn else 0
    return 2*p*r/(p+r) if p+r else 0


def main():
    # ---- 8.1 the corpus ---------------------------------------------------
    man = json.load(open("synth/tables/MANIFEST.json"))
    claim("20 tables", 20, len(man))
    claim("840 columns", 840, sum(r["columns"] for r in man))
    claim("120 injected positives", 120, sum(r["positives"] for r in man))

    mech = collections.Counter(); prev = []
    lack = collections.Counter()
    for n in EX.names():
        b = EX.bundle(n, want_sample=False)
        per = collections.Counter()
        for col, st in b["subtype"].items():
            if st: mech[st] += 1; per[st] += 1
        for k in ("REASON", "CONSEQUENCE", "TIMING"):
            if per[k] == 0: lack[k] += 1
        df = pd.read_csv(f"synth/tables/{n}/data.csv")
        y = pd.to_numeric(df[b["target"]], errors="coerce").fillna(0).astype(bool)
        prev.append(100.0 * float(y.mean()))
    for k in ("REASON", "CONSEQUENCE", "TIMING"):
        claim(f"exactly 40 {k}", 40, mech[k])
    claim("leak density 14.3%", 14.3,
          round(100*sum(r["positives"] for r in man)/sum(r["columns"] for r in man), 1))
    claim("one table lacks REASON", 1, lack["REASON"])
    claim("one table lacks CONSEQUENCE", 1, lack["CONSEQUENCE"])
    claim("prevalence spans 0.5%", 0.5, round(min(prev), 1), tol=0.05)
    claim("prevalence spans to 28%", 28, round(max(prev)), tol=0.5)
    claim("no column named leaky_col_*", True,
          not any("leaky_col" in c for n in EX.names()
                  for c in EX.bundle(n, want_sample=False)["columns"]))
    tot = pos = 0
    for d in RN.ALLSETS:
        b = RN.spec_bundle(d); tot += len(b["truth"]); pos += sum(b["truth"].values())
    claim("Stratum A density 13.1%", 13.1, round(100*pos/tot, 1), tol=0.05)

    # ---- 8.2 the dependent variables --------------------------------------
    d1s, d2s, npos = [], [], 0
    for m in V.MODELS:
        g1, g6 = synth_cells(m, 1), synth_cells(m, 6)
        h = collections.Counter(); t = collections.Counter()
        h6 = collections.Counter(); t6 = collections.Counter()
        for n in EX.names():
            b = EX.bundle(n, want_sample=False)
            for g, H, T in ((g1, h, t), (g6, h6, t6)):
                gg = g.get(n)
                if not gg: continue
                for col, st in b["subtype"].items():
                    if not st: continue
                    T[st] += 1
                    if gg.get(col) == "UNAVAILABLE": H[st] += 1
        pc = lambda a, b_: 100.0*a/b_ if b_ else float("nan")
        D1 = pc(h["CONSEQUENCE"], t["CONSEQUENCE"]) - pc(h["REASON"], t["REASON"])
        D2 = pc(h6["REASON"], t6["REASON"]) - pc(h["REASON"], t["REASON"])
        d1s.append(D1); d2s.append(D2); npos += D1 > 0
    claim("D1 mean +33.0", 33.0, round(float(np.mean(d1s)), 1))
    claim("D2 mean +22.0", 22.0, round(float(np.mean(d2s)), 1))
    claim("16 of 16 models positive D1", 16, npos)
    claim("smallest D1 +17.5", 17.5, round(min(d1s), 1))

    # ---- 8.3 the baseline -------------------------------------------------
    sc, ps = [], []
    for n in EX.names():
        b = EX.bundle(n, want_sample=False)
        df = pd.read_csv(f"synth/tables/{n}/data.csv")
        y = df[b["target"]].to_numpy().astype(float)
        for col in b["columns"]:
            v = pd.to_numeric(df[col], errors="coerce").to_numpy().astype(float)
            msk = ~np.isnan(v)
            r = (0.0 if msk.sum() < 3 or v[msk].std() == 0
                 else abs(np.corrcoef(v[msk], y[msk])[0, 1]))
            sc.append(0.0 if np.isnan(r) else r); ps.append(bool(b["truth"][col]))
    sc = np.array(sc); ps = np.array(ps); b3 = 0.0
    for th in sorted(set(sc.tolist())):
        fl = sc >= th
        tp = int((fl & ps).sum()); fp = int((fl & ~ps).sum()); fn = int((~fl & ps).sum())
        p = tp/(tp+fp) if tp+fp else 0; r = tp/(tp+fn) if tp+fn else 0
        b3 = max(b3, 2*p*r/(p+r) if p+r else 0)
    claim("B3 synthetic 0.665", 0.665, round(b3, 3))
    import prose_pins as PZ
    X = PZ.src_exceed()
    claim("B3 real 0.630", 0.630, X["b3"])
    claim("real exceed C1 = 12 of 16", (12, 16), (X["c1"], X["n"]))
    claim("real exceed C6 = 14 of 16", (14, 16), (X["c6"], X["n"]))

    rows = []
    for m in V.MODELS:
        a, b6 = f1_synth(m, 1), f1_synth(m, 6)
        r1, r6 = f1_real(m, 1), f1_real(m, 6)
        if None not in (a, b6, r1, r6): rows.append((m, r1, a, r6, b6))
    claim("16 models matched on both corpora", 16, len(rows))
    claim("synthetic exceed C1 = 12", 12, sum(1 for _, _, a, _, _ in rows if a > b3))
    claim("synthetic exceed C6 = 14", 14, sum(1 for _, _, _, _, b in rows if b > b3))
    claim("best margin C6 +0.187", 0.187,
          round(max(b for _, _, _, _, b in rows) - b3, 3))

    # ---- 8.4 the inversion ------------------------------------------------
    claim("best real C1 0.905", 0.905, round(max(r for _, r, _, _, _ in rows), 3))
    claim("best synth C1 0.754", 0.754, round(max(a for _, _, a, _, _ in rows), 3))
    claim("best real C6 0.929", 0.929, round(max(r for _, _, _, r, _ in rows), 3))
    claim("best synth C6 0.852", 0.852, round(max(b for _, _, _, _, b in rows), 3))
    claim("mean delta C1 -0.054", -0.054,
          round(float(np.mean([a-r for _, r, a, _, _ in rows])), 3))
    R1 = np.array([r for _, r, _, _, _ in rows])
    S1 = np.array([a for _, _, a, _, _ in rows])
    R6 = np.array([r for _, _, _, r, _ in rows])
    S6 = np.array([b for _, _, _, _, b in rows])
    # corr(public, unseen) -- the quantity that replaced the withdrawn
    # difference-on-component regression.  See the note in section 8.4.
    claim("corr(real, synth) C1 = +0.054", 0.054,
          round(float(stats.pearsonr(R1, S1)[0]), 3))
    claim("its p = 0.84", 0.84, round(float(stats.pearsonr(R1, S1)[1]), 2))
    claim("corr(real, synth) C6 = +0.473", 0.473,
          round(float(stats.pearsonr(R6, S6)[0]), 3))
    # AND the disclosure itself: the withdrawn r must equal what independence
    # predicts, or the paragraph explaining the withdrawal is wrong.
    sX, sY = R1.std(ddof=1), S1.std(ddof=1)
    claim("independence predicts -0.952", -0.952,
          round(float(-sX / np.sqrt(sX**2 + sY**2)), 3))
    claim("the withdrawn r WAS -0.951", -0.951,
          round(float(stats.pearsonr(R1, S1 - R1)[0]), 3))
    claim("real C1 range 0.425-0.905", (0.425, 0.905), (round(R1.min(), 3), round(R1.max(), 3)))
    claim("synth C1 range 0.614-0.754", (0.614, 0.754), (round(S1.min(), 3), round(S1.max(), 3)))
    claim("sd real C1 0.145", 0.145, round(float(R1.std(ddof=1)), 3))
    claim("sd synth C1 0.046", 0.046, round(float(S1.std(ddof=1)), 3))
    claim("spread factor 3.1", 3.1, round(float(R1.std(ddof=1)/S1.std(ddof=1)), 1))
    claim("Levene p 0.014", 0.014, round(float(stats.levene(R1, S1).pvalue), 3))
    claim("four models gain at C1", 4, sum(1 for _, r, a, _, _ in rows if a > r))
    R6 = np.array([r for _, _, _, r, _ in rows]); S6 = np.array([b for _, _, _, _, b in rows])
    claim("sd real C6 0.109", 0.109, round(float(R6.std(ddof=1)), 3))
    claim("sd synth C6 0.056", 0.056, round(float(S6.std(ddof=1)), 3))
    claim("Levene C6 p 0.162", 0.162, round(float(stats.levene(R6, S6).pvalue), 3))
    g = [(r, a) for _, r, a, _, _ in rows if a - r > 0.25]
    claim("weakest model gains +0.258", 0.258, round(g[0][1]-g[0][0], 3) if g else None)
    claim("weakest model real 0.425", 0.425, round(g[0][0], 3) if g else None)

    # ---- 8.5 the three controls -------------------------------------------
    for tag, m, syn, real, gap, d1 in (
            ("nano", "nvidia/nemotron-3-nano-30b-a3b::high", 0.630, 0.632, -0.002, 17.5),
            ("super", "nvidia/nemotron-3-super-120b-a12b::high", 0.617, 0.652, -0.035, 45.0),
            ("ultra", "nvidia/nemotron-3-ultra-550b-a55b::high", 0.605, 0.725, -0.120, 27.5)):
        a, b = f1_synth(m, 1), f1_real(m, 1)
        claim(f"ladder {tag} synth F1", syn, round(a, 3))
        claim(f"ladder {tag} real F1", real, round(b, 3))
        claim(f"ladder {tag} gap", gap, round(a-b, 3))
        gg = synth_cells(m, 1); h = collections.Counter(); t = collections.Counter()
        for n, x in gg.items():
            bb = EX.bundle(n, want_sample=False)
            for col, st in bb["subtype"].items():
                if not st: continue
                t[st] += 1
                if x.get(col) == "UNAVAILABLE": h[st] += 1
        pc = lambda p_, q: 100.0*p_/q if q else float("nan")
        claim(f"ladder {tag} D1", d1,
              round(pc(h["CONSEQUENCE"], t["CONSEQUENCE"]) - pc(h["REASON"], t["REASON"]), 1))

    def reason_real(m, cond):
        cells = V.cells_for(m)
        at = {cc: {d for (d, c2, s) in cells if c2 == cc and d in BUND} for cc in (1, 6)}
        keep = at[1] & at[6]; h = t = 0
        for (d, cc, s), got in cells.items():
            if cc != cond or d not in keep: continue
            for col, pos in BUND[d]["truth"].items():
                if not pos or V.subtype(d, col) != "REASON": continue
                t += 1
                v = got.get(col, {})
                v = v.get("verdict") if isinstance(v, dict) else v
                h += v == "UNAVAILABLE"
        return f"{h}/{t}"
    for m, e1, e6 in (("deepseek-v4-flash-0731::high", "0/42", "19/42"),
                      ("grok-4.20-non-reasoning::vertex-t0.0", "10/14", "14/14")):
        claim(f"clause {m[:20]} real C1", e1, reason_real(m, 1))
        claim(f"clause {m[:20]} real C6", e6, reason_real(m, 6))

    OP = collections.defaultdict(collections.Counter)
    for f in glob.glob("responses/*.json"):
        try: r = json.load(open(f))
        except Exception: continue
        if not r.get("dataset", "").endswith("__OPAQUE"): continue
        d, _ = parse(r.get("raw", "") or "")
        if not d: continue
        for x in d["columns"]:
            if isinstance(x, dict) and x.get("name"):
                OP[r["model"]][x.get("verdict")] += 1
    THREE = ["gemini-3.1-pro-preview::vertex-think16000-t0.0",
             "grok-4.20-reasoning::vertex-t0.0",              # the MATCHED arm
             "gemini-2.5-pro::vertex-think16000-t0.0"]
    for m, ab in zip(THREE, (612, 612, 592)):
        claim(f"opaque {m[:24]} abstain", ab, OP[m]["ABSTAIN"])
        claim(f"opaque {m[:24]} total", 612, sum(OP[m].values()))
    claim("opaque 1,816 abstentions", 1816, sum(OP[m]["ABSTAIN"] for m in THREE))
    claim("opaque 1,836 judgments", 1836, sum(sum(OP[m].values()) for m in THREE))

    # ---- 8.6 the amendments -----------------------------------------------
    PRE = open("PREREG.md").read()
    claim("Amendment 1 in PREREG", True, "# Amendment 1" in PRE)
    claim("Amendment 2 in PREREG", True, "# Amendment 2" in PRE)
    claim("ladder models off-roster", True,
          not any("nano-30b" in m or "ultra-550b" in m for m in V.MODELS))
    claim("gpt-5.6-sol-xhigh on roster", True, "gpt-5.6-sol-xhigh" in V.MODELS)
    tools = [r.get("tool_items") for f in glob.glob("responses/*.json")
             for r in [json.load(open(f))] if r.get("provider") == "codex-cli"]
    claim("all 40 codex cells tool_items=0", True, len(tools) == 40 and set(tools) == {0})

    # ---- report -----------------------------------------------------------
    print("=" * 78)
    print("SECTION 8 — every quantity, recomputed from primary sources")
    print("=" * 78)
    bad = 0
    for ok, text, stated, actual in RESULTS:
        if not ok:
            print(f'  FAIL  {text:<40}paper={stated!s:<14}computed={actual!s}')
            bad += 1
    print(f"\n  {len(RESULTS)-bad} of {len(RESULTS)} claims verified, {bad} failing")
    if not bad:
        print("  Every number in section 8 recomputes from the frozen tables,")
        print("  the response cache and NUMBERS.txt.  Nothing was read back out")
        print("  of NUMBERS_E.txt, so this is a check and not an echo.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
