"""Fill the paraphrase control -- and the matched normal arm -- for every
API-served model in the roster.

WHY BOTH ARMS AND NOT JUST THE PARAPHRASE ARM

  The paraphrase control is a DIFFERENCE: score on real column names minus
  score on string-distinct aliases, on the same cells.  Three models have the
  paraphrase arm today, and they are the three with the most complete normal
  arm, which is not a coincidence -- they were the models the earlier campaigns
  ran hardest.  Launching only the paraphrase arm for the other eleven would
  produce an aliased score with nothing matched to subtract it from, and the
  scorer would then quietly compare against whatever normal cells happened to
  exist.  That is how the paraphrase arm scored 0.000 the first time.

  So each model gets the same grid twice: conditions 0-6, all twelve Stratum A
  datasets, seed 1000, once normal and once aliased.  Cells that already exist
  are skipped by the runner's content-hash cache, so a model that is already
  complete costs one process start and nothing else.

WHY OPUS AND GPT ARE ABSENT

  Their provider is "ui": they were run through the agent loop, not an HTTP
  endpoint, so there is no key to hand a background process.  They are left
  for a foreground pass.  Their absence is recorded here rather than in a
  comment somewhere else, because a roster that silently drops the two best
  models would make every tier statement in the paper wrong.

WHY SEQUENTIAL

  Featherless bills concurrency per organisation and a 480B model consumes the
  whole allowance, so two models in parallel on one key do not go twice as
  fast -- they queue, time out, and retry.  The models are run one at a time
  and the parallelism lives inside runner.py, which owns one key per worker.
"""
import os, subprocess, sys, time, json

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
LOGS = HERE + "sweep_logs/"
STATE = HERE + "sweep_state.json"
os.makedirs(LOGS, exist_ok=True)

# (api model id, provider, reasoning effort or None, extra runner args)
ROSTER = [
    ("nvidia/nemotron-3-super-120b-a12b", "nvidia", "high", ["--workers", "4"]),
    ("deepseek-ai/deepseek-v4-flash-0731", "nvidia", "high", ["--workers", "4"]),
    ("deepseek-ai/DeepSeek-V4-Pro", "featherless", "high", []),
    ("moonshotai/Kimi-K3", "featherless", "high", []),
    ("zai-org/GLM-5.2", "featherless", "high", []),
    ("mistralai/Mistral-Large-Instruct-2411", "featherless", None, []),
    ("Qwen/Qwen3-Next-80B-A3B-Instruct", "featherless", None, []),
    ("Qwen/Qwen2-72B-Instruct", "featherless", None, []),
    ("unsloth/Llama-3.3-70B-Instruct", "featherless", None, []),
    ("Nexusflow/Athene-V2-Chat", "featherless", None, []),
    ("google/gemma-4-E4B-it", "featherless", None, []),
    # already have both arms; included so a resumed run verifies rather than
    # assumes, at the cost of one cache-hit pass each
    ("Qwen/Qwen3-Coder-480B-A35B-Instruct", "featherless", None, []),
    ("gemini-3.7-flash", "gemini", None, []),
    ("gemini-3.5-flash", "gemini", None, []),
]
CONDS = "0,1,2,3,4,5,6"
PER_CALL_TIMEOUT = 9000          # DeepSeek-V4-Pro para timed out at exactly 5400


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def run(model, provider, reasoning, extra, paraphrase):
    arm = "para" if paraphrase else "norm"
    tag = f"{model.replace('/', '_')}{'::' + reasoning if reasoning else ''}.{arm}"
    log = LOGS + tag + ".log"
    cmd = [sys.executable, "-u", HERE + "runner.py",
           "--models", model, "--provider", provider,
           "--conditions", CONDS, "--all", "--repeats", "1",
           # 32000, not 4000.  The 4,000-token budget is what truncated 33 cells
           # in the first campaign: a wide dataset needs one JSON object per
           # column before the model has reasoned at all, and CRIME (144 cols)
           # and MI (122 cols) live in THIS grid.  A truncated cell parses into
           # a partial column list and every missing column scores as "not
           # flagged", which is indistinguishable from the model declining.
           "--http-timeout", "1200", "--max-tokens", "32000"] + extra
    if reasoning:
        cmd += ["--reasoning", reasoning]
    if paraphrase:
        cmd += ["--paraphrase"]
    t0 = time.time()
    with open(log, "a") as fh:
        fh.write(f"\n===== {time.strftime('%H:%M:%S')} {' '.join(cmd)}\n")
        fh.flush()
        try:
            p = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                               timeout=PER_CALL_TIMEOUT, cwd=HERE)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = "TIMEOUT"
        fh.write(f"===== rc={rc} in {int(time.time()-t0)}s\n")
    return rc, int(time.time() - t0)


def main():
    passes = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    state = load_state()
    for p in range(1, passes + 1):
        print(f"\n########## PASS {p}/{passes}", flush=True)
        for model, provider, reasoning, extra in ROSTER:
            label = model + (f"::{reasoning}" if reasoning else "")
            for para in (False, True):
                key = f"{label}|{'para' if para else 'norm'}"
                if state.get(key, {}).get("rc") == 0:
                    print(f"  skip {key} (done)", flush=True)
                    continue
                print(f"  RUN  {key}", flush=True)
                rc, secs = run(model, provider, reasoning, extra, para)
                state[key] = dict(rc=rc, secs=secs,
                                  ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
                json.dump(state, open(STATE, "w"), indent=1)
                print(f"  {key:<58} rc={rc} {secs}s", flush=True)
    bad = {k: v for k, v in state.items() if v.get("rc") != 0}
    print(f"\n{len(state)-len(bad)}/{len(state)} arms clean; "
          f"{len(bad)} not: {sorted(bad)}", flush=True)


if __name__ == "__main__":
    main()
