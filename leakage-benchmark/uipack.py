"""Emit paste-ready session files for running the benchmark through a chat UI.

WHY THIS IS NOT JUST "PRINT THE PROMPTS"

  A UI run is only worth anything if its numbers sit in the same table as the
  API numbers.  That requires the prompt to be BYTE-IDENTICAL to what
  runner.py sends, including the shuffled column order for the stated seed --
  ordering alone moved F1 by 0.312 on the transfer set, so a file that
  regenerates the order differently is measuring a different experiment.
  Every block below therefore comes from the same prompts.build* call the
  runner uses, with the same random.Random(seed).shuffle.

CONTAMINATION, WHICH IS THE REAL RISK HERE

  The conditions form a cumulative ladder, so putting two of them in one
  session destroys both.  C1 states the target; if a C0 block sits in the same
  context, C0 is no longer "names only".  C6 carries the derivation clause; if
  a C1 block can see it, C1 is no longer the plain condition.  One condition
  per FILE and one file per SESSION is not tidiness, it is the only way the
  ladder means anything.

  Sub-agents must also not see each other's answers.  Nine independent
  judgments that have read each other are one judgment repeated nine times,
  and the seed-variance measurement -- the most important thing this run can
  produce -- would collapse to zero by construction.

NO ANSWERS IN THE FILE
  Nothing here contains the truth labels, the positive counts, or the subtype
  codes.  A file that mentions how many leaks a dataset has is an answer key.
"""
import os, sys, json, random, textwrap

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN
import prompts as P

OUT = HERE + "ui/"

TRANSFER = ["mi", "crime", "student"]
MAIN = RN.ALLSETS                       # the 12-dataset corpus


def cell_prompt(b, cond, seed):
    """Exactly what runner.py would send for this cell."""
    cols = b["columns"][:]
    random.Random(seed).shuffle(cols)
    if cond == 9:
        return P.SYSTEM, P.build_derivation_v2(b["name"], cols, b["target"])
    if cond == 7:
        return P.SYSTEM, P.build_surrogate(b["name"], cols, b["target"])
    if cond == 6:
        return P.SYSTEM, P.build_derivation(b["name"], cols, b["target"])
    if cond == 5:
        return P.EXPERT_SYSTEM, P.build_expert(b["name"], cols, b["target"],
                                               b["description"], None)
    return P.SYSTEM, P.build(b["name"], cols, cond, b["target"],
                             b["prediction_point"], b["description"], b["sample"])


HEADER = """\
# Benchmark run — condition {cond}{condname}

**Run this file in a FRESH session. Do not run any other condition file in
this session.** The conditions are cumulative; if a block from another
condition is visible in this context, both conditions are invalidated and the
results are unusable.

## What to do

There are {n} independent tasks below. For each one:

1. Spawn a **separate sub-agent**. One sub-agent per task, {n} in total.
2. Give that sub-agent **only** its own SYSTEM and USER text, verbatim.
   Do not summarise it, do not reformat it, do not add context, do not tell it
   what the other tasks are.
3. Collect its reply exactly as returned.

## Rules that make the results usable

- **Do not answer any task yourself.** You are dispatching, not judging.
- **Do not let sub-agents see each other's output.** Several tasks are the same
  dataset with the columns in a different order — that is deliberate, it is the
  measurement. If they influence each other the measurement is destroyed.
- **Do not reconcile disagreements.** If two tasks on the same dataset disagree,
  report both. The disagreement is the finding.
- **Do not look anything up.** No web search, no consulting documentation for
  these datasets. The task is to judge from the column names and the framing
  given, nothing else.
- **Judge every column.** A reply that covers 40 of 122 columns is not a partial
  answer, it is a failed cell.
- **Do not drop the `reason` field.** It is half the results.

## How to give the results back

Reply with one block per task, in this exact shape, and nothing else between
them:

```
### CELL <cell id>
<the sub-agent's raw JSON, unedited>
```

Keep the JSON exactly as the sub-agent returned it — do not pretty-print it,
merge it, deduplicate it, or fix it. If a sub-agent returned malformed JSON,
paste the malformed text; that is data too.

---
"""

CONDNAME = {0: " — names only", 1: " — target given", 2: " — prediction point",
            3: " — description", 4: " — sample rows", 5: " — expert scaffold",
            6: " — derivation criterion", 7: " — surrogate criterion",
            9: " — derivation criterion, stated without reference to time"}


def write(tag, keys, cond, seeds):
    bundles = {}
    for k in keys:
        try:
            bundles[k] = RN.spec_bundle(k)
        except Exception as e:
            print(f"    SKIP {k}: {type(e).__name__}")
    blocks, ids = [], []
    for k, b in bundles.items():
        for seed in seeds:
            if cond == 3 and not b["description"]:
                continue
            sysmsg, user = cell_prompt(b, cond, seed)
            cid = f"{b['name']}-C{cond}-s{seed}"
            ids.append(cid)
            blocks.append(
                f"## TASK {len(ids)} of {{n}} — cell id `{cid}`\n\n"
                f"**SYSTEM:**\n\n```\n{sysmsg}\n```\n\n"
                f"**USER:**\n\n```\n{user}\n```\n\n---\n")
    n = len(ids)
    body = HEADER.format(cond=f"C{cond}", condname=CONDNAME.get(cond, ""), n=n)
    body += "\n".join(bl.replace("{n}", str(n)) for bl in blocks)
    body += ("\n## Checklist before you reply\n\n"
             f"- [ ] {n} sub-agents spawned, one per task\n"
             f"- [ ] {n} `### CELL` blocks in the reply\n"
             "- [ ] every column in every cell answered\n"
             "- [ ] no cell answered by you rather than a sub-agent\n"
             "- [ ] nothing looked up externally\n\n"
             "Cell ids in this file:\n\n"
             + "\n".join(f"- `{i}`" for i in ids) + "\n")
    os.makedirs(OUT + tag, exist_ok=True)
    p = f"{OUT}{tag}/C{cond}.md"
    open(p, "w").write(body)
    ncols = sum(len(bundles[k]["columns"]) for k in bundles) * len(seeds)
    print(f"  {p:<44}{n:>3} cells{ncols:>6} column-judgments"
          f"{os.path.getsize(p)/1024:>8.0f} KB")


if __name__ == "__main__":
    # C9 only.  C1 and C6 are already cached for both frontier models, and C6
    # tells us nothing new about a model already at 100% REASON under it.  The
    # open question is whether the frontier behaves like the DeepSeek family
    # (C9 helps a lot), like nemotron (C9 costs precision), or is indifferent
    # like Kimi.
    # Separate tags: write() names the file by CONDITION, so putting both packs
    # under one tag makes the second silently overwrite the first.
    print("C9 packs -- retimed derivation clause (see REGISTERED_C9.md)")
    write("c9_main", MAIN, 9, [1000])
    write("c9_transfer", TRANSFER, 9, [1000, 1001, 1002])
    print(f"\nrun ONE file per session; never two conditions in one session")
