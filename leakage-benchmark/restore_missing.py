"""Restore every quarantined cell that the first re-run did not put back.

THE MISTAKE THIS REPAIRS

  33 truncated cells were quarantined and re-run.  The re-run plan grouped them
  by (model, dataset, condition) and DROPPED THE SEED, then invoked the runner
  with `--repeats 1`, which produces seed 1000 only.  Every quarantined cell at
  seed 1001, 1002 or 1003 was therefore removed and never regenerated, and a
  few seed-1000 cells were missed too when their provider was busy.

  23 cells were left missing.  The damage was not hypothetical: gemini-3.5-flash
  lost four AI4I cells, AI4I dropped out of the paraphrase control's matched-cell
  set, and that control's recall fell from 0.680 to 0.000 -- a number that looks
  like a model failing completely and was in fact a dataset silently leaving the
  comparison.  The NUMBERS diff against the pre-fix copy is what surfaced it.

WHAT THIS DOES DIFFERENTLY

  It re-runs each cell at ITS OWN SEED, by asking the runner for enough repeats
  to reach that seed (`--repeats seed-999`).  Extra seeds cost nothing: they are
  already cached and the runner skips them.

  Budget is 32,000 tokens, the value that finally satisfied CRIME's 144 columns.

WHY NOT JUST DELETE THE QUARANTINE

  Because a missing cell and a truncated cell are different failures and only
  one of them is recoverable by re-running.  Everything moved aside is still in
  responses_truncated/ and is the evidence for both this repair and the earlier
  one.
"""
import collections, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
MISSING = HERE + "rerun_missing.json"
MAXTOK = 32000


def main():
    rows = json.load(open(MISSING))
    sys.path.insert(0, HERE)
    import runner as RN
    keyfor = {}
    for k in list(RN.ALLSETS) + list(RN.EXPLICIT) + list(RN.STRATC):
        try:
            keyfor[RN.spec_bundle(k)["name"]] = k
        except Exception:
            pass

    # Group so one runner invocation covers as many cells as possible, but
    # never merge different seeds into a smaller --repeats than the largest
    # one needs.  That is the exact mistake being repaired.
    group = collections.defaultdict(lambda: [set(), 1000])
    for r in rows:
        key = keyfor.get(r["dataset"])
        if not key:
            print(f"  SKIP {r['dataset']}: no runner key", flush=True)
            continue
        model, reasoning = r["model"], None
        if "::" in model:
            model, reasoning = model.split("::", 1)
        g = group[(model, r["provider"], reasoning, key)]
        g[0].add(r["condition"])
        g[1] = max(g[1], r.get("seed") or 1000)

    for (model, provider, reasoning, key), (conds, maxseed) in sorted(
            group.items(), key=lambda kv: str(kv[0])):
        repeats = max(1, maxseed - 999)
        cmd = [sys.executable, "-u", HERE + "runner.py",
               "--models", model, "--provider", provider,
               "--conditions", ",".join(str(c) for c in sorted(conds)),
               "--datasets", key, "--repeats", str(repeats),
               "--max-tokens", str(MAXTOK), "--http-timeout", "1200"]
        if reasoning:
            cmd += ["--reasoning", reasoning]
        if provider == "nvidia":
            cmd += ["--workers", "4"]
        print(f"\n=== {model}{'::'+reasoning if reasoning else ''} {key} "
              f"C{sorted(conds)} seeds 1000..{maxseed}", flush=True)
        t0 = time.time()
        rc = subprocess.run(cmd, cwd=HERE).returncode
        print(f"=== rc={rc} in {int(time.time()-t0)}s", flush=True)


if __name__ == "__main__":
    main()
