"""Prepare and record one hand-run (sub-agent) cell.

WHY THIS EXISTS

  `claude-opus-5-max` has no API key in this environment.  Section 5.3 of the
  paper describes how its cells were obtained: "run through their chat
  interfaces with one sub-agent per cell; their prompts were verified
  byte-identical to the API runs by regenerating and hash-matching against
  cached cells."  This script is that procedure, made repeatable.

ONE SUB-AGENT PER CELL, AND WHY IT MATTERS

  Not one agent for several tables.  An agent that answers WAREHOUSE and then
  COLD_CHAIN has its second answer conditioned on its first, and the cells stop
  being independent observations -- which is what every pooled number here
  assumes.  The cost is 40 dispatches; the alternative is 40 correlated cells
  pretending to be independent.

WHAT IS AND IS NOT IDENTICAL TO AN API RUN

  identical:  the user prompt, byte for byte, and therefore the cache id
  NOT identical:  the system prompt is the harness's, not prompts.SYSTEM, and
                  the reasoning effort cannot be set to "max" from here.
  The second difference is real and is recorded in the cell itself under
  `run_mode`, so no later reader has to reconstruct it from a changelog.

    python synth/subagent_cell.py prompt  <DATASET> <COND>   -> prints the prompt
    python synth/subagent_cell.py record  <DATASET> <COND> <file-with-answer>
"""
import hashlib
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import prompts                                              # noqa: E402
import export as EX                                         # noqa: E402
from salvage import parse                                   # noqa: E402

MODEL = "claude-opus-5-max"
RUN_MODE = "subagent; system prompt is the harness's, effort not settable"


def build(dataset, cond, seed=1000):
    b = EX.bundle(dataset, want_sample=True)
    cols = b["columns"][:]
    random.Random(seed).shuffle(cols)
    if cond == 6:
        user = prompts.build_derivation(b["name"], cols, b["target"])
    elif cond == 1:
        user = prompts.build(b["name"], cols, cond, b["target"],
                             b["prediction_point"], b["description"], b["sample"])
    else:
        raise SystemExit(f"condition {cond} not part of this experiment")
    cid = hashlib.sha256(
        f"{MODEL}||{b['name']}|{cond}|{seed}|{user}".encode()).hexdigest()[:20]
    return b, user, cid


def record(dataset, cond, answer, seed=1000):
    b, user, cid = build(dataset, cond, seed)
    d, _ = parse(answer)
    if not d:
        raise SystemExit(f"{dataset} C{cond}: answer does not parse; NOT cached")
    got = {c["name"] for c in d["columns"]
           if isinstance(c, dict) and c.get("name")}
    cov = len(got & set(b["columns"])) / len(b["columns"])
    if cov < 0.95:
        raise SystemExit(f"{dataset} C{cond}: coverage {cov:.0%} — refusing to "
                         f"cache a partial answer, same rule the API path uses")
    rec = dict(model=MODEL, provider="subagent", run_mode=RUN_MODE,
               dataset=b["name"], shown_as=b["name"], paraphrase=False,
               alias=None, condition=cond, seed=seed, status="ok",
               raw=answer, ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
    path = ROOT + "responses/" + cid + ".json"
    tmp = path + ".tmp"
    json.dump(rec, open(tmp, "w"), indent=1)
    os.replace(tmp, path)
    return cid, cov, len(got)


def todo():
    """Cells still missing for this model."""
    out = []
    for name in EX.names():
        for cond in (1, 6):
            _, _, cid = build(name, cond)
            if not os.path.exists(ROOT + "responses/" + cid + ".json"):
                out.append((name, cond))
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "todo":
        t = todo()
        print(f"{len(t)} cell(s) outstanding for {MODEL}")
        for n, c in t:
            print(f"  {n} C{c}")
    elif sys.argv[1] == "prompt":
        _, user, cid = build(sys.argv[2], int(sys.argv[3]))
        print(f"### cache id {cid}\n{user}")
    elif sys.argv[1] == "record":
        ans = open(sys.argv[4]).read()
        cid, cov, n = record(sys.argv[2], int(sys.argv[3]), ans)
        print(f"cached {cid}  coverage {cov:.0%}  {n} columns")
