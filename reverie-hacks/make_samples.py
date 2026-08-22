"""Generate SAMPLES.md — the workflow against a single prompt, case by case.

  The track asks for sample test cases run through the workflow "as compared to
  using a single prompt approach with the same test cases".  Same test cases is
  the operative phrase, so every case below is scored on columns answered under
  ALL FOUR passes and under the single prompt -- one population, two methods.

  Cases are selected by what they demonstrate, not by which flatter the
  workflow: a clean win, a recall rescue that lands in review rather than in
  auto-drop, the false-alarm cost paid for that precision, and a table with no
  leaks at all where the only correct behaviour is silence.
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
BENCH = "/workspace/research/leakage-benchmark/"
SCRATCH = ("/tmp/claude-0/-home-user-celesta-exoplanet-flagship/"
           "1dfa598a-70c3-5cb5-8d7b-ecd921e451d9/scratchpad/multi/")
sys.path.insert(0, SCRATCH if os.path.exists(SCRATCH + "diabetic.csv") else BENCH)
import runner as RN

PASSES = (1, 2, 6, 9)
PASSNAME = {1: "P1 bare", 2: "P2 timing", 6: "P3 derivation", 9: "P4 reworded"}

# (dataset, model, seed, why this case is here)
# Chosen by measured outcome, not by memory. An earlier version of this list
# described a case as "consensus recovers all six" when the data showed it
# recovered one -- the caption was written from what was expected rather than
# from the output, which is the exact failure this project is about.
CASES = [
    ("MI", "claude-opus-5-max", 1000,
     "The clean win. A single prompt raises 9 false alarms on a 122-column "
     "table; the workflow auto-drops all 11 real leaks with none."),
    ("STEEL", "nvidia/nemotron-3-super-120b-a12b::high", 1000,
     "Recall rescue, and note HOW. A single prompt misses all six sibling fault "
     "columns silently. The workflow does not catch them outright either — it "
     "escalates all six to a human instead of dropping them on the floor."),
    ("SUPPORT2", "nvidia/nemotron-3-super-120b-a12b::high", 1000,
     "The cost, shown rather than hidden. Auto-drop is perfectly precise, and "
     "the price is 11 columns in review of which 8 are false alarms."),
    ("STUDENT", "claude-opus-5-max", 1001,
     "A table with NO leaks, where the only correct behaviour is silence. The "
     "single prompt raises three false alarms; the workflow auto-drops nothing "
     "and routes all three to review."),
]


def load():
    B = {}
    for k in list(RN.ALLSETS) + list(RN.EXPLICIT):
        b = RN.spec_bundle(k)
        B[b["name"]] = b
    raw = {}
    for p in glob.glob(BENCH + "responses/*.json"):
        j = json.load(open(p))
        if j.get("paraphrase") or j["dataset"] not in B:
            continue
        try:
            cols = json.loads(j["raw"])["columns"]
        except Exception:
            continue
        raw[(j["dataset"], j["condition"], j["model"], j.get("seed"))] = {
            str(r.get("name")): (str(r.get("verdict", "")).upper() == "UNAVAILABLE",
                                 (r.get("reason") or "").strip())
            for r in cols if r.get("name")}
    return B, raw


def rows_for(B, raw, ds, model, seed):
    b = B[ds]
    out = []
    for col in b["columns"]:
        vs, ok = {}, True
        for c in PASSES:
            d = raw.get((ds, c, model, seed))
            if not d or col not in d:
                ok = False
                break
            vs[c] = d[col]
        if ok:
            out.append((col, vs, bool(b["truth"].get(col))))
    return b, out


def main():
    B, raw = load()
    L = []
    A = L.append
    A("# Samples — the workflow vs a single prompt, on the same test cases\n")
    A("Every case below is scored on the **same columns**: only those answered")
    A("under the single prompt *and* all four workflow passes. One population,")
    A("two methods. Verdicts and quoted reasons are real cached model outputs.\n")
    A("- **Single prompt** = one call, P1's query alone (`schema + target →")
    A("  which columns could not honestly be known?`).")
    A("- **Workflow** = four differently-worded passes, merged by counting")
    A("  agreements: 4/4 → auto-drop, 1–3 → human review, 0 → keep.\n")
    A("---\n")

    for n, (ds, model, seed, why) in enumerate(CASES, 1):
        b, rows = rows_for(B, raw, ds, model, seed)
        if not rows:
            A(f"## Case {n}: {ds} — data unavailable in this checkout\n")
            continue
        npos = sum(1 for _, _, t in rows if t)

        # single prompt
        s_tp = sum(1 for _, v, t in rows if v[1][0] and t)
        s_fp = sum(1 for _, v, t in rows if v[1][0] and not t)
        s_fn = sum(1 for _, v, t in rows if not v[1][0] and t)
        # workflow
        drop = [(c, v, t) for c, v, t in rows if sum(x[0] for x in v.values()) == 4]
        rev = [(c, v, t) for c, v, t in rows if 0 < sum(x[0] for x in v.values()) < 4]
        keep = [(c, v, t) for c, v, t in rows if sum(x[0] for x in v.values()) == 0]

        A(f"## Case {n}: `{ds}` — predicting `{b['target']}`\n")
        A(f"*{why}*\n")
        A(f"**Prediction point (human input):** {b.get('prediction_point') or '—'}  ")
        A(f"**Model:** `{model}` · **Columns:** {len(rows)} · "
          f"**Documented leaks:** {npos}\n")

        A("| | flagged | correct | false alarms | leaks missed |")
        A("|---|---|---|---|---|")
        A(f"| **Single prompt** | {s_tp+s_fp} | {s_tp} | **{s_fp}** | **{s_fn}** |")
        A(f"| **Workflow — auto-drop** | {len(drop)} | "
          f"{sum(1 for _,_,t in drop if t)} | "
          f"{sum(1 for _,_,t in drop if not t)} | — |")
        A(f"| **Workflow — to review** | {len(rev)} | "
          f"{sum(1 for _,_,t in rev if t)} | "
          f"{sum(1 for _,_,t in rev if not t)} | — |")
        A(f"| **Workflow — kept** | 0 | — | — | "
          f"**{sum(1 for _,_,t in keep if t)}** |\n")

        # per-column detail, leaks first then anything either method flagged
        # Documented leaks first, then anything either method flagged. Source
        # order buried all 11 of MI's leaks below 14 legitimate columns, so the
        # table's first screen argued the opposite of the case it illustrates.
        shown = [r for r in rows if r[2] or r[1][1][0] or
                 sum(x[0] for x in r[1].values()) > 0]
        shown.sort(key=lambda r: (not r[2], -sum(x[0] for x in r[1].values())))
        if shown:
            A("| column | truth | single prompt | P1 | P2 | P3 | P4 | workflow says |")
            A("|---|---|---|---|---|---|---|---|")
            for col, vs, truth in shown[:14]:
                n_f = sum(x[0] for x in vs.values())
                route = ("auto-drop" if n_f == 4 else
                         "review" if n_f else "keep")
                mark = lambda c: "🚩" if vs[c][0] else "·"
                sp = "🚩 flagged" if vs[1][0] else "· allowed"
                A(f"| `{col}` | {'**LEAK**' if truth else 'legitimate'} | {sp} | "
                  f"{mark(1)} | {mark(2)} | {mark(6)} | {mark(9)} | **{route}** |")
            if len(shown) > 14:
                A(f"\n*({len(shown)-14} further flagged columns omitted for length.)*")
            A("")

        # one column where the passes disagreed, with the model's own words
        dis = [(c, v, t) for c, v, t in rows
               if 0 < sum(x[0] for x in v.values()) < 4]
        pick = next((x for x in dis if x[2]), dis[0] if dis else None)
        if pick:
            col, vs, truth = pick
            A(f"**Why `{col}` went to a human** — the passes disagreed, in the "
              f"model's own words:\n")
            for c in PASSES:
                flag, reason = vs[c]
                A(f"- **{PASSNAME[c]}** → {'FLAGGED' if flag else 'allowed'}"
                  + (f" — *“{reason[:170]}”*" if reason else ""))
            A(f"\nGround truth: this column **{'is' if truth else 'is not'}** a "
              f"documented leak. A single prompt returns one of these four "
              f"answers and no indication that the other three exist.\n")
        A("---\n")

    A("## What the cases show together\n")
    A("1. **The workflow's win is precision, not recall.** Requiring four")
    A("   differently-worded passes to agree raises precision from 0.729 to")
    A("   0.839 across the full 2,548-judgment population.")
    A("2. **The union workflow is a trap.** Flagging on *any* pass reaches 0.936")
    A("   recall and drops precision to 0.583 — worse F1 than the single prompt")
    A("   it was supposed to improve on.")
    A("3. **The routing is the product.** A single call returns a flat list. The")
    A("   workflow returns three lists, and the middle one is the only place a")
    A("   human's time is worth spending.\n")
    A("Full numbers: `python3 workflow_eval.py`.")

    open(HERE + "SAMPLES.md", "w").write("\n".join(L) + "\n")
    print(f"  wrote SAMPLES.md ({len(L)} lines, {len(CASES)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
