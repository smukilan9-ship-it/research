"""Re-run the cells our own token budget cut off.

WHAT WENT WRONG

  Every campaign ran at `--max-tokens 4000`.  A 144-column dataset judged at
  reasoning=high needs far more than that: the model reasons, then emits one
  JSON object per column, and the completion is cut mid-object.  The parser
  still recovers whatever objects completed, so the cell looks like a valid
  answer that happens to omit most columns.

  The scorer then reads a column with no verdict as "not flagged", which for a
  positive is a miss.  CRIME C6 on nemotron parsed **1 of 144 columns** and was
  scored as a model that found almost nothing.  It was a model we cut off at
  67,868 characters of output.

  33 of 1,296 parsed non-paraphrase cells (2.5%) are affected.

WHAT IS *NOT* AFFECTED, AND WHY THE DISTINCTION MATTERS

  A further 47 cells are incomplete but WELL-FORMED -- valid JSON listing fewer
  columns than were asked for.  That is the model omitting columns, not us
  truncating it, and "no verdict" is the right reading.  Those are left alone.

  The test is structural: a truncated completion stops mid-object, so its last
  non-space character is not a closing brace, bracket, fence or quote, and its
  braces do not balance.  Sorting on coverage alone would have thrown away 47
  genuine model failures and flattered every model in the table.

WHY NO CACHE SURGERY IS NEEDED

  The cache key is a hash of (model, reasoning, dataset, condition, seed,
  prompt).  `max_tokens` is not in it.  So re-running the same cell at a larger
  budget writes the same file, and the truncated version is simply replaced --
  which is why the quarantined copies are moved aside rather than deleted, and
  why they stay readable in responses_truncated/ as the evidence for this fix.
"""
import json, os, subprocess, sys, time, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
PLAN = HERE + "rerun_plan.json"
MAXTOK = 32000          # CRIME needs ~144 JSON objects; 16000 still cut it


def main():
    plan = json.load(open(PLAN))
    todo = []
    for key, cells in plan.items():
        model, provider = key.rsplit("|", 1)
        reasoning = None
        if "::" in model:
            model, reasoning = model.split("::", 1)
        by = collections.defaultdict(set)
        for name, cond in cells:
            by[name].add(int(cond))
        todo.append((model, provider, reasoning, by))

    # Datasets are named in the cache by their DISPLAY name; the runner takes
    # its lowercase key.  Built from runner's own lists so a renamed dataset
    # cannot silently drop out of the re-run.
    sys.path.insert(0, HERE)
    import runner as RN
    keyfor = {}
    for k in list(RN.ALLSETS) + list(RN.EXPLICIT) + list(RN.STRATC):
        try:
            keyfor[RN.spec_bundle(k)["name"]] = k
        except Exception:
            pass

    for model, provider, reasoning, by in todo:
        for name, conds in sorted(by.items()):
            key = keyfor.get(name)
            if not key:
                print(f"  SKIP {name}: no runner key", flush=True)
                continue
            cmd = [sys.executable, "-u", HERE + "runner.py",
                   "--models", model, "--provider", provider,
                   "--conditions", ",".join(str(c) for c in sorted(conds)),
                   "--datasets", key, "--repeats", "1",
                   "--max-tokens", str(MAXTOK), "--http-timeout", "900"]
            if reasoning:
                cmd += ["--reasoning", reasoning]
            if provider == "nvidia":
                cmd += ["--workers", "4"]
            print(f"\n=== {model}{'::'+reasoning if reasoning else ''}  "
                  f"{name} C{sorted(conds)}", flush=True)
            t0 = time.time()
            rc = subprocess.run(cmd, cwd=HERE).returncode
            print(f"=== rc={rc} in {int(time.time()-t0)}s", flush=True)


if __name__ == "__main__":
    main()

# FIRST RE-RUN AT 16,000 WAS STILL SHORT FOR CRIME.
#   nemotron C6 on CRIME came back at 122 of 144 columns -- better than the
#   original 1 of 144, and still truncated.  144 objects at roughly 150 tokens
#   apiece is ~21,600 tokens of JSON before the model has reasoned at all, so
#   16,000 was never going to be enough for the widest dataset in the corpus.
#   The budget is 32,000 now.  verify_paper's response_coverage section is what
#   caught it, within a minute of the cell landing, which is the whole point of
#   having a guard that runs on every regeneration rather than a one-off check.
