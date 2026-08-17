"""Keep retrying quarantined cells until every one is back.

WHY IT HAS TO BE A LOOP WITH LONG SLEEPS

  The single-pass restore put 13 of 33 cells back and then hit the wall that no
  amount of retrying inside one pass can get past: all nine Gemini keys returned
  HTTP 429 for their DAILY quota, and Featherless refused new work because the
  main sweep is using its whole concurrency allowance.  Neither clears in
  seconds; both clear in hours.

  So this sleeps between passes rather than hammering, and it recomputes the
  missing set every time -- cells restored by some other job (sweep_stratc will
  collect the Klaverjas ones on its own) simply drop out.

WHAT COUNTS AS MISSING

  A cell in responses_truncated/ whose (model, dataset, paraphrase, condition,
  seed) tuple has no counterpart in responses/.  Seed is part of the key on
  purpose: dropping it is exactly the bug that lost these cells in the first
  place, when a re-run grouped by (model, dataset, condition) and asked for
  `--repeats 1`, regenerating seed 1000 and silently abandoning 1001-1003.

WHY NOT JUST RESTORE THE QUARANTINED FILE

  Because it is truncated.  Putting it back would restore the original defect --
  a partial column list scored as though the model had declined to flag
  everything missing.  The only correct repair is a fresh completion at a
  budget large enough to finish, and until that exists the cell is honestly
  absent and verify_paper says so.
"""
import collections, glob, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
QUAR = HERE + "responses_truncated/"
PASSES = int(sys.argv[1]) if len(sys.argv) > 1 else 12
GAP = int(sys.argv[2]) if len(sys.argv) > 2 else 1800      # 30 min
MAXTOK = 32000


def missing():
    live = collections.defaultdict(set)
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        live[(r["model"], r["dataset"], bool(r.get("paraphrase")))].add(
            (r["condition"], r.get("seed")))
    out = []
    for f in glob.glob(QUAR + "*.json"):
        r = json.load(open(f))
        k = (r["model"], r["dataset"], bool(r.get("paraphrase")))
        if (r["condition"], r.get("seed")) not in live[k]:
            out.append(r)
    return out


def main():
    sys.path.insert(0, HERE)
    import runner as RN
    keyfor = {}
    for k in list(RN.ALLSETS) + list(RN.EXPLICIT) + list(RN.STRATC):
        try:
            keyfor[RN.spec_bundle(k)["name"]] = k
        except Exception:
            pass

    for p in range(1, PASSES + 1):
        rows = missing()
        if not rows:
            print(f"\nALL RESTORED after pass {p-1}.", flush=True)
            return
        print(f"\n########## RESTORE PASS {p}/{PASSES}: {len(rows)} cell(s) "
              f"missing", flush=True)
        group = collections.defaultdict(lambda: [set(), 1000, False])
        for r in rows:
            key = keyfor.get(r["dataset"])
            if not key:
                continue
            model, reasoning = r["model"], None
            if "::" in model:
                model, reasoning = model.split("::", 1)
            g = group[(model, r.get("provider"), reasoning, key)]
            g[0].add(r["condition"])
            g[1] = max(g[1], r.get("seed") or 1000)
            g[2] = g[2] or bool(r.get("paraphrase"))
        for (model, provider, reasoning, key), (conds, maxseed, para) in \
                sorted(group.items(), key=lambda kv: str(kv[0])):
            cmd = [sys.executable, "-u", HERE + "runner.py",
                   "--models", model, "--provider", provider,
                   "--conditions", ",".join(str(c) for c in sorted(conds)),
                   "--datasets", key, "--repeats", str(max(1, maxseed - 999)),
                   "--max-tokens", str(MAXTOK), "--http-timeout", "1200"]
            if reasoning:
                cmd += ["--reasoning", reasoning]
            if para:
                cmd += ["--paraphrase"]
            if provider == "nvidia":
                cmd += ["--workers", "4"]
            print(f"\n=== {model}{'::'+reasoning if reasoning else ''} {key} "
                  f"C{sorted(conds)} seeds 1000..{maxseed}"
                  f"{' [paraphrase]' if para else ''}", flush=True)
            t0 = time.time()
            rc = subprocess.run(cmd, cwd=HERE).returncode
            print(f"=== rc={rc} in {int(time.time()-t0)}s", flush=True)
        left = len(missing())
        print(f"\nafter pass {p}: {left} still missing", flush=True)
        if left and p < PASSES:
            print(f"  sleeping {GAP}s — Gemini daily quota and Featherless "
                  f"concurrency clear in hours, not seconds", flush=True)
            time.sleep(GAP)
    left = missing()
    print(f"\nFINAL: {len(left)} cell(s) never restored.", flush=True)
    for r in sorted(left, key=lambda x: (x["model"], x["dataset"])):
        print(f"  {r['model'][:38]:<40}{r['dataset']:<12}C{r['condition']} "
              f"seed={r.get('seed')}", flush=True)


if __name__ == "__main__":
    main()
