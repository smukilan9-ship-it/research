"""Stratum C across the roster: CIRRHOSIS, both arms.

WHY IT IS WORTH RUNNING DESPITE BEING ONE DATASET WITH ONE POSITIVE

  It is the hardest case in the corpus and it is hard in a specific,
  diagnostic way.  The frozen sieve returns zero on the whole UCI record: no
  warning verb, no derivation verb, nothing a regular expression can catch.
  The leak is visible only by reading "number of days between registration and
  the earlier of death, transplantation, or study analysis time" and noticing
  that the interval's endpoint IS the target event.

  That is REASON-mechanism inference, and REASON is where every model was
  weakest -- 62% recall at C1, 81% at C6.  A single-positive dataset cannot
  move a pooled F1 and is not meant to; it answers a narrower question that the
  pooled number cannot: does the derivation clause (C6) recover a positive that
  no scanner and no keyword could have found?

WHY THE PARAPHRASE ARM MATTERS MORE HERE THAN ANYWHERE ELSE

  This table is the Mayo Clinic PBC trial.  It ships inside R's `survival`
  package as `pbc`, it is in most survival-analysis textbooks, and it is one of
  the most reproduced clinical tables in existence.  If any dataset in this
  project is memorised verbatim by a frontier model, it is this one.  The
  aliased arm is therefore not a formality -- a large gap between arms here is
  the single most interpretable memorisation signal available.

SEQUENCING

  Waits for sweep_stratb, which waits for sweep_models.  Featherless bills
  concurrency per organisation, so three drivers at once queue rather than
  parallelise.  98 cells at most; it is the cheapest of the three.
"""
import os, subprocess, sys, time, json

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
LOGS = HERE + "sweep_logs/"
STATE = HERE + "sweep_stratc_state.json"
os.makedirs(LOGS, exist_ok=True)

import runner as RN
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

UPSTREAM = [("sweep_models.py", HERE + "sweep_models.log"),
            ("sweep_stratb.py", HERE + "sweep_stratb.log")]


def wait_for_upstream():
    t0 = time.time()
    while True:
        pending = []
        for script, log in UPSTREAM:
            done = (os.path.exists(log)
                    and "arms clean" in
                    open(log, errors="replace").read()[-3000:])
            alive = subprocess.run(["pgrep", "-f", script],
                                   capture_output=True,
                                   text=True).stdout.split()
            if alive and not done:
                pending.append(script)
        if not pending:
            print("upstream sweeps clear; starting Stratum C", flush=True)
            return
        print(f"  waiting for {', '.join(pending)} ... "
              f"{int(time.time()-t0)//60}m", flush=True)
        time.sleep(60)


def run(model, provider, reasoning, extra, paraphrase):
    arm = "para" if paraphrase else "norm"
    tag = (f"{model.replace('/', '_')}"
           f"{'::' + reasoning if reasoning else ''}.stratC.{arm}")
    log = LOGS + tag + ".log"
    # Every Stratum C dataset, read from runner.STRATC rather than named here,
    # so adding a dataset to the stratum does not require remembering to add it
    # to the driver.  Klaverjas arrived after this file was written and a
    # hardcoded "cirrhosis" would have silently left it unrun all night.
    dsets = ",".join(RN.STRATC)
    cmd = [sys.executable, "-u", HERE + "runner.py",
           "--models", model, "--provider", provider,
           "--conditions", CONDS, "--datasets", dsets, "--repeats", "1",
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
    for p in range(1, passes + 1):
        print(f"\n########## STRATUM C PASS {p}/{passes}", flush=True)
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
