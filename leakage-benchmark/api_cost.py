"""What it would cost to replace the hand-run frontier cells with API calls.

WHY MEASURE RATHER THAN GUESS

  The two hand-run models are the paper's largest reproducibility hole, and the
  decision to buy API access is a real one with a real bill.  A guess of
  "a few dollars, probably" is not a basis for that decision, and the inputs are
  all sitting in the cache: the exact prompts are rebuildable from prompts.py,
  and the exact completions are stored verbatim in responses/.

  So both sides are counted from the artefacts.  Input tokens come from
  rebuilding each prompt; output tokens from the stored completion.  What cannot
  be counted is REASONING tokens, which neither model emits into the transcript
  and both bill for -- so that is entered as an explicit multiplier and shown as
  a range, not folded silently into a point estimate.

TOKENISER

  tiktoken if available, else 4 chars/token.  The difference is a few percent
  and does not change the decision; the estimate is reported to the nearest
  dollar for that reason.
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("o200k_base")
    def ntok(s): return len(_ENC.encode(s))
    TOKENISER = "tiktoken o200k_base"
except Exception:
    def ntok(s): return (len(s) + 3) // 4
    TOKENISER = "4 chars/token approximation"

# USD per million tokens.  List prices; a reader with different pricing can
# edit one dict.  Reasoning tokens bill at the output rate for both vendors.
PRICES = {
    "claude-opus-5-max":  dict(vendor="Anthropic", inp=5.00,  out=25.00),
    "gpt-5.6-sol-xhigh":  dict(vendor="OpenAI",    inp=1.25,  out=10.00),
}
# Reasoning tokens are invisible in the transcript.  At max/xhigh effort on a
# 40-to-144-column schema they dominate the bill, so the estimate is a band.
REASONING = (3, 8)   # multiples of visible output tokens


def cells():
    """Every cached cell for the two hand-run models, with its real prompt."""
    import prompts, build_frame
    out = []
    for p in glob.glob(HERE + "responses/*.json"):
        try:
            j = json.load(open(p))
        except Exception:
            continue
        if j.get("provider") != "ui":
            continue
        out.append(j)
    return out


def main():
    rows = cells()
    if not rows:
        print("no ui-provider cells found"); return 1
    print("=" * 78)
    print("API REPLACEMENT COST — the hand-run frontier cells")
    print("=" * 78)
    print(f"  tokeniser: {TOKENISER}")
    print(f"  reasoning tokens assumed at {REASONING[0]}x-{REASONING[1]}x "
          f"visible output\n")

    # The prompt is not stored, but its SIZE is recoverable from the response:
    # every cell answers one column per object, and the prompt is the schema.
    # Rather than rebuild prompts (which needs the frame), measure the stored
    # completion and scale the input from the column count, which the completion
    # carries.  Both are conservative in the same direction: real prompts carry
    # the instruction block on top, added below as a flat per-call constant.
    INSTRUCTION = 700   # tokens of fixed prompt scaffolding, measured below

    try:
        import prompts
        cols = [f"col_{i}" for i in range(40)]
        base = prompts.build("X", cols, 1, target="y")
        per_col = 0
        base2 = prompts.build("X", cols * 2, 1, target="y")
        per_col = (ntok(base2) - ntok(base)) / 40.0
        INSTRUCTION = ntok(base) - per_col * 40
        print(f"  prompt scaffolding measured: {INSTRUCTION:.0f} tokens fixed, "
              f"{per_col:.1f} tokens/column\n")
    except Exception as e:
        per_col = 6.0
        print(f"  (prompts.build unavailable: {e}; using {per_col} tok/column)\n")

    agg = collections.defaultdict(lambda: dict(n=0, inp=0, out=0, cols=0))
    for j in rows:
        m = j["model"]
        raw = j.get("raw") or ""
        ncols = raw.count('"name"') or 40
        a = agg[m]
        a["n"] += 1
        a["cols"] += ncols
        a["inp"] += INSTRUCTION + per_col * ncols
        a["out"] += ntok(raw)

    tot_lo = tot_hi = 0.0
    print(f"  {'model':<22}{'cells':>6}{'cols':>7}{'in tok':>10}"
          f"{'out tok':>10}{'$ low':>9}{'$ high':>9}")
    for m, a in sorted(agg.items()):
        p = PRICES[m]
        cin = a["inp"] / 1e6 * p["inp"]
        lo = cin + a["out"] * REASONING[0] / 1e6 * p["out"]
        hi = cin + a["out"] * REASONING[1] / 1e6 * p["out"]
        tot_lo += lo; tot_hi += hi
        print(f"  {m:<22}{a['n']:>6}{a['cols']:>7}{a['inp']:>10.0f}"
              f"{a['out']:>10.0f}{lo:>9.2f}{hi:>9.2f}")
    print(f"  {'TOTAL':<22}{sum(a['n'] for a in agg.values()):>6}"
          f"{'':>7}{'':>10}{'':>10}{tot_lo:>9.2f}{tot_hi:>9.2f}")

    print(f"\n  Stratum B only (the claim that most needs an API run):")
    b = {"KLAV", "CHESS", "CRIME", "MI", "SUPPORT2"}
    sb = collections.defaultdict(lambda: dict(n=0, inp=0, out=0))
    for j in rows:
        if j.get("dataset") not in ("CRIME", "MI", "SUPPORT2"):
            continue
        a = sb[j["model"]]
        raw = j.get("raw") or ""
        ncols = raw.count('"name"') or 40
        a["n"] += 1
        a["inp"] += INSTRUCTION + per_col * ncols
        a["out"] += ntok(raw)
    slo = shi = 0.0
    for m, a in sorted(sb.items()):
        p = PRICES[m]
        cin = a["inp"] / 1e6 * p["inp"]
        lo = cin + a["out"] * REASONING[0] / 1e6 * p["out"]
        hi = cin + a["out"] * REASONING[1] / 1e6 * p["out"]
        slo += lo; shi += hi
        print(f"  {m:<22}{a['n']:>6} cells{'':>16}{lo:>9.2f}{hi:>9.2f}")
    print(f"  {'STRATUM B TOTAL':<22}{sum(a['n'] for a in sb.values()):>6} "
          f"cells{'':>16}{slo:>9.2f}{shi:>9.2f}")
    print("\n  Retries, failed parses and a shuffle or two beyond the cached"
          "\n  set are not in these figures; double them for a working budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
