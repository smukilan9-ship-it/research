"""The same two arms over the HELD-OUT stratum: CRIME and STUDENT.

WHY THIS IS A SEPARATE DRIVER AND WHY IT WAITS

  sweep_models.py was already in flight when the paraphrase map was extended to
  Stratum B, and a running Python process does not re-read its own source.
  Editing it would have changed nothing until it was restarted, and restarting
  it to add two datasets would have thrown away whatever arm was mid-grid.

  It waits rather than running alongside because Featherless bills concurrency
  per organisation: two drivers on the same three keys do not finish in half
  the time, they queue behind each other, hit the 900s call ceiling, and retry.
  Serial is faster here, and it also keeps the rate-limit picture legible when
  something goes wrong at 3am.

WHY MI IS NOT HERE

  Its columns cannot be paraphrased without changing their difficulty -- see
  paraphrase_extend.py.  The normal arm for MI still runs; only the aliased arm
  is out of scope, so MI appears in the normal grid below and not in the
  paraphrase one.

WHAT STUDENT CONTRIBUTES

  Nothing to recall: the ground-truth audit withdrew G1 and G2, so STUDENT has
  zero positives.  Its cell measures FALSE POSITIVES ONLY and must be read that
  way; an undefined recall averaged into a headline is how a control becomes a
  claim it cannot support.
"""
import os, subprocess, sys, time, json

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
LOGS = HERE + "sweep_logs/"
STATE = HERE + "sweep_stratb_state.json"
UPSTREAM = HERE + "sweep_models.log"
os.makedirs(LOGS, exist_ok=True)

from sweep_models import ROSTER, PER_CALL_TIMEOUT

# C1 and C6 ONLY, not the full ladder.
#
#   At the full seven conditions this grid was running ~2,000s per model-arm:
#   4 of 28 arms in three hours, so 14 models would have taken most of a day and
#   the user asked for every MODEL, not every condition.  C1 (column names only)
#   and C6 (derivation clause) are the two the paper's claims rest on, and the
#   full ladder is already measured on Stratum A for the whole roster.
#
#   Trading condition depth for model breadth is the right way round here: a
#   paraphrase decrement needs the same condition in both arms, not all seven.
CONDS = "1,6"


def wait_for_upstream():
    """Block until sweep_models.py has retired, printing so the supervisor can
    tell waiting from wedged."""
    t0 = time.time()
    while True:
        if os.path.exists(UPSTREAM):
            tail = open(UPSTREAM, errors="replace").read()[-3000:]
            if "arms clean" in tail:
                print("upstream sweep finished; starting Stratum B",
                      flush=True)
                return
        alive = subprocess.run(["pgrep", "-f", "sweep_models.py"],
                               capture_output=True, text=True).stdout.split()
        if not alive:
            print("upstream sweep is not running and shows no completion "
                  "marker; starting Stratum B anyway", flush=True)
            return
        print(f"  waiting for sweep_models.py ... {int(time.time()-t0)//60}m",
              flush=True)
        time.sleep(60)


def run(model, provider, reasoning, extra, paraphrase, datasets):
    arm = "para" if paraphrase else "norm"
    tag = (f"{model.replace('/', '_')}"
           f"{'::' + reasoning if reasoning else ''}.stratB.{arm}")
    log = LOGS + tag + ".log"
    cmd = [sys.executable, "-u", HERE + "runner.py",
           "--models", model, "--provider", provider,
           "--conditions", CONDS, "--datasets", datasets, "--repeats", "1",
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
            rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                timeout=PER_CALL_TIMEOUT, cwd=HERE).returncode
        except subprocess.TimeoutExpired:
            rc = "TIMEOUT"
        fh.write(f"===== rc={rc} in {int(time.time()-t0)}s\n")
    return rc, int(time.time() - t0)


def main():
    wait_for_upstream()
    passes = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    # normal arm covers all three; the aliased arm skips MI (see docstring)
    GRIDS = [(False, "mi,crime,student"), (True, "crime,student")]
    for p in range(1, passes + 1):
        print(f"\n########## STRATUM B PASS {p}/{passes}", flush=True)
        for model, provider, reasoning, extra in ROSTER:
            label = model + (f"::{reasoning}" if reasoning else "")
            for para, dsets in GRIDS:
                key = f"{label}|{'para' if para else 'norm'}"
                if state.get(key, {}).get("rc") == 0:
                    print(f"  skip {key} (done)", flush=True)
                    continue
                print(f"  RUN  {key}  [{dsets}]", flush=True)
                rc, secs = run(model, provider, reasoning, extra, para, dsets)
                state[key] = dict(rc=rc, secs=secs, datasets=dsets,
                                  ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
                json.dump(state, open(STATE, "w"), indent=1)
                print(f"  {key:<58} rc={rc} {secs}s", flush=True)
    bad = {k: v for k, v in state.items() if v.get("rc") != 0}
    print(f"\n{len(state)-len(bad)}/{len(state)} arms clean; "
          f"{len(bad)} not: {sorted(bad)}", flush=True)


if __name__ == "__main__":
    main()
