"""Extract the prompt-ladder demo data from the cached model responses.

  Nothing here is generated for the demo.  Every verdict and every sentence of
  reasoning in the output is a real completion from a real model, cached at run
  time, and the same cells the benchmark's F1 numbers are computed from.  The
  demo is a viewer over evidence, not a simulation of one.

  Ground truth and mechanisms come from the benchmark's own corpus, so the
  demo cannot drift from the paper it is showing.
"""
import os, sys, json, glob, collections

# The scratchpad working copy carries the raw CSVs the loaders need; the repo
# clone deliberately does not.  Falls back to the repo when only that exists.
SCRATCH = "/tmp/claude-0/-home-user-celesta-exoplanet-flagship/1dfa598a-70c3-5cb5-8d7b-ecd921e451d9/scratchpad/multi/"
BENCH = SCRATCH if os.path.exists(SCRATCH + "diabetic.csv") else "/workspace/research/leakage-benchmark/"
sys.path.insert(0, BENCH)
import runner as RN
from subtypes import subtype

# The story the demo tells is C1 -> C6: what one sentence buys.  C9 is kept
# because it is the honest counterweight -- a differently-worded version of the
# same criterion that helps some models and hurts others.
CONDS = (1, 6, 9)

# One model per lab, the ones the paper reports.  Including all eighteen cached
# models would triple the payload to show near-duplicates.
KEEP = {
    "claude-opus-5-max": "claude-opus-5",
    "gpt-5.6-sol-xhigh": "gpt-5.6-sol",
    "gemini-3.7-flash": "gemini-3.7-flash",
    "moonshotai/Kimi-K3::high": "Kimi-K3",
    "zai-org/GLM-5.2::high": "GLM-5.2",
    "nvidia/nemotron-3-super-120b-a12b::high": "nemotron-3-super",
    "deepseek-ai/deepseek-v4-flash-0731::high": "deepseek-v4-flash",
    "Qwen/Qwen3-Coder-480B-A35B-Instruct": "Qwen3-Coder-480B",
}


def main():
    bundles = {}
    for k in list(RN.ALLSETS) + list(RN.EXPLICIT):
        b = RN.spec_bundle(k)
        bundles[b["name"]] = b

    best = {}          # (ds, cond, model) -> the most complete cell
    for p in glob.glob(BENCH + "responses/*.json"):
        j = json.load(open(p))
        if j.get("paraphrase") or j["model"] not in KEEP:
            continue
        if j["condition"] not in CONDS or j["dataset"] not in bundles:
            continue
        try:
            parsed = json.loads(j["raw"])["columns"]
        except Exception:
            continue
        key = (j["dataset"], j["condition"], KEEP[j["model"]])
        if key not in best or len(parsed) > len(best[key][1]):
            best[key] = (j, parsed)

    out = {"datasets": {}, "runs": {}}
    for name, b in sorted(bundles.items()):
        cols = list(b["columns"])
        out["datasets"][name] = dict(
            target=b["target"],
            prediction_point=b.get("prediction_point") or "",
            columns=cols,
            truth={c: bool(b["truth"].get(c)) for c in cols},
            mechanism={c: (subtype(name, c) or "CONTESTED")
                       for c in cols if b["truth"].get(c)},
            n_pos=sum(1 for c in cols if b["truth"].get(c)),
        )

    for (ds, cond, model), (j, parsed) in sorted(best.items()):
        v = {}
        for row in parsed:
            n = row.get("name")
            if n is None:
                continue
            v[str(n)] = dict(
                f=1 if str(row.get("verdict", "")).upper() == "UNAVAILABLE" else 0,
                r=(row.get("reason") or "")[:400],
            )
        out["runs"].setdefault(ds, {}).setdefault(str(cond), {})[model] = v

    dst = os.path.dirname(os.path.abspath(__file__)) + "/demo_data.json"
    json.dump(out, open(dst, "w"), separators=(",", ":"))
    n = sum(len(m) for d in out["runs"].values() for m in d.values())
    print(f"  {len(out['datasets'])} datasets, {n} cells, "
          f"{os.path.getsize(dst)/1048576:.2f} MB -> {dst}")

    have = collections.Counter()
    for ds, byc in out["runs"].items():
        for c, bym in byc.items():
            have[c] += len(bym)
    print(f"  cells per condition: {dict(sorted(have.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
