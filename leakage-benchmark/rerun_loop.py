"""Detect → quarantine → re-run, until no truncated cell is left.

WHY A LOOP RATHER THAN ONE PASS

  The first re-run raised the budget from 4,000 to 16,000 and CRIME C6 on
  nemotron came back at 122 of 144 columns -- better than the original 1 of 144,
  and still cut off.  144 JSON objects at roughly 150 tokens apiece is ~21,600
  tokens before the model reasons at all, so one guess at a budget was never
  going to settle it for the widest dataset in the corpus.

  Each pass raises the budget and re-runs only what is still short, so the cost
  is paid per stubborn cell rather than per cell.

WHAT IS AND IS NOT RE-RUN

  Only cells that stop MID-OBJECT: last non-space character is not a closing
  brace, bracket, fence or quote, and braces do not balance.  A response that is
  well-formed and merely lists fewer columns is the model omitting them, which
  is a model property and must be scored as one -- 47 such cells exist and none
  of them is touched here.  Sorting on coverage alone would delete 47 genuine
  model failures and flatter every model in the table.

  Paraphrased cells are skipped entirely: their columns are aliases, so
  comparing them against the original column list reports 0% coverage for
  perfectly good answers.  That mistake was made once, against the whole
  cirrhosis paraphrase arm, and was recoverable only because quarantine moves
  files instead of deleting them.

STOPPING

  Stops when a pass finds nothing truncated, when the budget ceiling is
  reached, or when a pass fails to improve any cell -- the last of which means
  the model is failing for a reason a bigger budget will not fix, and grinding
  on it would waste the night.
"""
import collections, glob, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
QUAR = HERE + "responses_truncated/"
BUDGETS = [32000, 48000, 64000]
os.makedirs(QUAR, exist_ok=True)
sys.path.insert(0, HERE)


def bundles():
    import runner as RN
    out = {}
    for k in list(RN.ALLSETS) + list(RN.EXPLICIT) + list(RN.STRATC):
        try:
            b = RN.spec_bundle(k)
            out[b["name"]] = (k, b)
        except Exception:
            pass
    return out


def truncated(bs):
    """(cache path, model, provider, reasoning, runner key, condition, n, tot)"""
    import verify_paper as VP
    out = []
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if r.get("paraphrase"):
            continue
        nm = r.get("shown_as") or r.get("dataset")
        if nm not in bs:
            continue
        key, b = bs[nm]
        raw = r.get("raw", "")
        d, _ = VP.parse(raw)
        if not d:
            continue
        got = {c["name"] for c in d["columns"]
               if isinstance(c, dict) and c.get("name")}
        n = sum(1 for c in b["truth"] if c in got)
        tot = len(b["truth"])
        if n == tot:
            continue
        tail = raw.rstrip()[-1:] if raw.strip() else ""
        if tail in "}]`\"" and (raw.count("{") - raw.count("}")) <= 1:
            continue                       # well-formed, model omitted columns
        model, reasoning = r["model"], None
        if "::" in model:
            model, reasoning = model.split("::", 1)
        out.append((f, model, r.get("provider"), reasoning, key,
                    r["condition"], n, tot))
    return out


def main():
    bs = bundles()
    prev = None
    for budget in BUDGETS:
        bad = truncated(bs)
        if not bad:
            print(f"\nNo truncated cells remain. Done.", flush=True)
            return
        cov = {(x[1], x[4], x[5]): x[6] for x in bad}
        if prev is not None and cov == prev:
            print(f"\nSTOPPING: {len(bad)} cell(s) did not improve at the last "
                  f"budget increase.\nA larger budget is not the problem; these "
                  f"need looking at by hand:", flush=True)
            for f, m, p, rs, key, c, n, tot in bad:
                print(f"  {key:<12}C{c} {m[:36]:<38}{n}/{tot}", flush=True)
            return
        prev = cov
        print(f"\n########## PASS at max_tokens={budget}: {len(bad)} truncated "
              f"cell(s)", flush=True)
        group = collections.defaultdict(set)
        for f, m, p, rs, key, c, n, tot in bad:
            print(f"  quarantine {key:<12}C{c} {m[:34]:<36}{n}/{tot}",
                  flush=True)
            shutil.move(f, QUAR + os.path.basename(f))
            group[(m, p, rs)].add((key, c))
        for (m, p, rs), cells in sorted(group.items()):
            bykey = collections.defaultdict(set)
            for key, c in cells:
                bykey[key].add(c)
            for key, conds in sorted(bykey.items()):
                cmd = [sys.executable, "-u", HERE + "runner.py",
                       "--models", m, "--provider", p,
                       "--conditions", ",".join(str(c) for c in sorted(conds)),
                       "--datasets", key, "--repeats", "1",
                       "--max-tokens", str(budget), "--http-timeout", "1200"]
                if rs:
                    cmd += ["--reasoning", rs]
                if p == "nvidia":
                    cmd += ["--workers", "4"]
                print(f"\n=== {m}{'::'+rs if rs else ''} {key} C{sorted(conds)} "
                      f"@ {budget}", flush=True)
                t0 = time.time()
                rc = subprocess.run(cmd, cwd=HERE).returncode
                print(f"=== rc={rc} in {int(time.time()-t0)}s", flush=True)
    bad = truncated(bs)
    print(f"\nFINAL: {len(bad)} still truncated at the highest budget "
          f"({BUDGETS[-1]}).", flush=True)
    for f, m, p, rs, key, c, n, tot in bad:
        print(f"  {key:<12}C{c} {m[:36]:<38}{n}/{tot}", flush=True)


if __name__ == "__main__":
    main()
