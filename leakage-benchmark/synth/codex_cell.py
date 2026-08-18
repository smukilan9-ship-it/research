"""Run one Stratum E cell in its own `codex exec` session.

WHY THIS EXISTS

  PREREG section 3 declares `gpt-5.6-sol-xhigh` unrunnable here: "A sub-agent
  in this harness is Claude.  Producing its 40 cells requires that model's own
  chat interface, run by hand.  If those cells are not obtained, the model is
  reported as absent."

  The Codex CLI ships inside /Applications/ChatGPT.app and is authenticated on
  this machine.  It IS that model's own harness, driven non-interactively.  So
  the cells are obtainable after all, and the model does not have to be
  reported absent.  This is not a new model and not a substitution -- it is the
  declared roster entry, reached by a route PREREG did not know existed.

  A FOURTH RUN MODE IS BEING ADDED AFTER RESULTS WERE SEEN, AND THAT MUST BE
  SAID PLAINLY.  PREREG section 9 forbids adding models, dropping models,
  moving the bar or changing the dependent variable; it does not forbid
  obtaining a declared model's cells by a better route, and reporting the model
  is strictly more informative than reporting it absent.  But the sequence is
  what it is, and section 7's table is applied to the completed roster
  unchanged.

ONE SESSION PER CELL

  Same reason as the sub-agent path: an agent that answers WAREHOUSE and then
  COLD_CHAIN has its second answer conditioned on its first, and the cells stop
  being independent observations.  `--ephemeral` means no session file is even
  written, so a later run cannot resume into one.

WHAT THIS ARM CAN AND CANNOT DO -- THE PART THAT MATTERS FOR RIGOUR

  The sub-agent path's weakness (PREREG section 3) is that a sub-agent can read
  the answer key, and the only evidence it did not is the access time on the
  ground-truth files.  That is evidence about what happened, not a bound on
  what could happen.

  This arm is structurally bounded instead.  Every cell runs with:

      --disable shell_tool --disable unified_exec   no command execution at all
      -s read-only                                  no writes even if it had
      -C <empty dir outside the repository>         nothing to find where it is
      --ignore-user-config                          no MCP servers, no plugins

  Verified, not assumed: asked directly to `ls` the synth directory, the model
  answers "shell execution isn't available in this session".  It cannot open
  synth/tables.py because it has no tool that opens anything.  Each cell also
  records `tool_items`, counted from the JSONL event stream, and `record()`
  REFUSES to cache a cell whose count is not zero.

WHAT IS NOT IDENTICAL TO AN API RUN

  identical:  the user prompt, byte for byte -- asserted against
              subagent_cell.build(), which is the text runner.py would send
  NOT identical:  the system prompt is Codex's harness prompt, which also
                  carries a skill listing (~29k input tokens against the API
                  path's ~5k).  Same class of difference the sub-agent path
                  already declares and records; it is recorded here too, in
                  `run_mode`, in the cell itself.

  No --output-schema is used, deliberately.  Constraining the decode would make
  this arm's answers easier to parse than every other arm's, and the comparison
  is between models, not between JSON validators.  The reply goes through
  salvage.parse exactly like an API reply.

    python3 synth/codex_cell.py todo
    python3 synth/codex_cell.py run <DATASET> <COND>
    python3 synth/codex_cell.py runall [--limit N]
"""
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import export as EX                                          # noqa: E402
import subagent_cell as SA                                   # noqa: E402
from salvage import parse                                    # noqa: E402

MODEL = "gpt-5.6-sol-xhigh"
CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex"
CODEX_MODEL = "gpt-5.6-sol"
EFFORT = "xhigh"

# An EMPTY directory outside the repository.  The model has no shell tool, so
# this is belt as well as braces -- but a cell that somehow acquired one would
# still start somewhere with nothing in it.
WORKROOT = HERE + ".codexroot/"

RUN_MODE = ("codex-cli exec, one ephemeral session per cell; shell_tool and "
            "unified_exec disabled so the session has no command execution "
            "and cannot read ground truth; read-only sandbox rooted at an "
            "empty directory outside the repository; system prompt is Codex's, "
            "not prompts.SYSTEM; no output schema")

# Tools are disabled by name.  `shell_tool` and `unified_exec` are the two that
# could reach the filesystem; the rest are off because a tool the API arm does
# not have is a capability difference, even an unused one.
DISABLE = ["shell_tool", "unified_exec", "plugins", "apps", "skill_search",
           "browser_use", "browser_use_external", "browser_use_full_cdp_access",
           "computer_use", "multi_agent", "view_image", "image_generation",
           "tool_suggest", "memories", "goals", "hooks"]

# Item types that mean the session did something other than think and answer.
# `error` is excluded: the skills-budget warning arrives as one and is not a
# tool call.  Anything in this set appearing in a cell voids that cell.
TOOL_ITEMS = {"command_execution", "file_change", "mcp_tool_call", "web_search",
              "patch_apply", "tool_call", "local_shell_call", "custom_tool_call"}


def cid_for(dataset, cond, seed=1000):
    _, user, _ = SA.build(dataset, cond, seed)
    h = hashlib.sha256(
        f"{MODEL}||{dataset}|{cond}|{seed}|{user}".encode()).hexdigest()[:20]
    return user, h


def path_for(dataset, cond, seed=1000):
    return ROOT + "responses/" + cid_for(dataset, cond, seed)[1] + ".json"


def todo():
    out = []
    for name in EX.names():
        for cond in (1, 6):
            if not os.path.exists(path_for(name, cond)):
                out.append((name, cond))
    return out


def call(user, timeout=2700):
    """One codex session.  Returns (final_text, tool_items, usage)."""
    os.makedirs(WORKROOT, exist_ok=True)
    for junk in os.listdir(WORKROOT):                 # keep it genuinely empty
        os.remove(WORKROOT + junk)
    last = WORKROOT + ".last"
    cmd = [CODEX, "exec", "--ignore-user-config",
           "--model", CODEX_MODEL,
           "-c", f'model_reasoning_effort="{EFFORT}"',
           "-s", "read-only", "-C", WORKROOT,
           "--skip-git-repo-check", "--ephemeral", "--json",
           "-o", last]
    for f in DISABLE:
        cmd += ["--disable", f]
    cmd += ["-"]                       # prompt comes from stdin, unmodified
    p = subprocess.run(cmd, input=user, capture_output=True, text=True,
                       timeout=timeout)
    tools, usage = [], {}
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") == "item.completed":
            t = (e.get("item") or {}).get("type")
            if t in TOOL_ITEMS:
                tools.append(t)
        elif e.get("type") == "turn.completed":
            usage = e.get("usage") or {}
    text = open(last).read() if os.path.exists(last) else ""
    if not text.strip():
        raise RuntimeError(f"codex returned nothing (exit {p.returncode}): "
                           f"{p.stderr[-300:]}")
    return text, tools, usage


def record(dataset, cond, seed=1000):
    user, cid = cid_for(dataset, cond, seed)
    b = EX.bundle(dataset, want_sample=True)
    t0 = time.time()
    answer, tools, usage = call(user)
    secs = time.time() - t0

    # A cell that ran a tool is not this arm's cell.  Refuse it rather than
    # cache it with a caveat nobody will read.
    if tools:
        raise SystemExit(f"{dataset} C{cond}: session invoked {tools} — "
                         f"NOT cached; this arm's guarantee is zero tool calls")
    d, _ = parse(answer)
    if not d:
        raise SystemExit(f"{dataset} C{cond}: answer does not parse; NOT cached")
    got = {c["name"] for c in d["columns"]
           if isinstance(c, dict) and c.get("name")}
    cov = len(got & set(b["columns"])) / len(b["columns"])
    if cov < 0.95:
        raise SystemExit(f"{dataset} C{cond}: coverage {cov:.0%} — refusing to "
                         f"cache a partial answer, same rule the API path uses")
    rec = dict(model=MODEL, provider="codex-cli", run_mode=RUN_MODE,
               dataset=b["name"], shown_as=b["name"], paraphrase=False,
               alias=None, condition=cond, seed=seed, status="ok",
               raw=answer, tool_items=0, usage=usage, secs=round(secs, 1),
               ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
    path = ROOT + "responses/" + cid + ".json"
    tmp = path + ".tmp"
    json.dump(rec, open(tmp, "w"), indent=1)
    os.replace(tmp, path)
    return cid, cov, len(got), secs, usage


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if what == "todo":
        t = todo()
        print(f"{len(t)} cell(s) outstanding for {MODEL}")
        for n, c in t:
            print(f"  {n} C{c}")
    elif what == "run":
        cid, cov, n, secs, u = record(sys.argv[2], int(sys.argv[3]))
        print(f"cached {cid}  coverage {cov:.0%}  {n} cols  {secs:.0f}s  "
              f"out={u.get('output_tokens')}")
    elif what == "runall":
        lim = int(sys.argv[sys.argv.index("--limit") + 1]) \
            if "--limit" in sys.argv else 10**6
        t = todo()[:lim]
        print(f"running {len(t)} cell(s), one session each")
        ok, bad = 0, []
        for i, (n, c) in enumerate(t, 1):
            try:
                cid, cov, k, secs, u = record(n, c)
                ok += 1
                print(f"  [{i}/{len(t)}] {n:<22} C{c}  {cov:5.0%}  {k:>3} cols  "
                      f"{secs:>5.0f}s  out={u.get('output_tokens')}", flush=True)
            except SystemExit as e:
                bad.append((n, c, str(e)))
                print(f"  [{i}/{len(t)}] {n:<22} C{c}  FAILED: {e}", flush=True)
            except Exception as e:
                bad.append((n, c, repr(e)))
                print(f"  [{i}/{len(t)}] {n:<22} C{c}  ERROR: {e!r}", flush=True)
        print(f"\n{ok} cached, {len(bad)} failed")
        for n, c, why in bad:
            print(f"  {n} C{c}: {why[:160]}")
