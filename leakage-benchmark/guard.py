"""Supervisor: keep every overnight job alive, and restart the ones that die.

WHY THIS EXISTS

  Four separate runs in this project have died quietly overnight -- a stray
  timeout, a `nohup ... &` inside an already-backgrounded call, a single API
  key hitting its daily quota -- and in every case the log simply stopped and
  the run looked, from outside, exactly like a slow one.  Checking in every
  fifteen minutes catches that within fifteen minutes.  A supervisor catches it
  within one, and does not need anyone awake.

  Every managed job is CHECKPOINTED AND RESUMABLE, which is what makes restart
  the correct response rather than a way to corrupt state:

    kaggle_enrich   writes full.json every 25 datasets and skips what it has
    openml_harvest  writes desc/features/dead every 25 and skips what it has
    hf_harvest      writes cards.json every 50 and skips what it has
    memcheck_all    writes memcheck_all.json after every single test
    sweep_models    runner.py caches per cell by content hash; a restarted arm
                    re-walks the grid and pays only for the cells it lost

  So a restart costs at most one checkpoint interval of duplicated work.

TWO KINDS OF DEATH, BOTH HANDLED

  DEAD    no process matching the script is running.  Restart it.
  STALLED a process is running but its log has not advanced in `stall`
          seconds.  This is the dangerous one: the process still holds its
          slot, so nothing else notices.  Kill it, then restart.

  Stall thresholds are per-job and generous, because a healthy job CAN be quiet:
  memcheck's row_completion_test is 25 chained calls, and a reasoning model at
  a 900s timeout can legitimately spend half an hour on one cell.  A threshold
  set too tight turns the supervisor into the thing that kills the run.

COMPLETION IS NOT DEATH

  A job that finished must not be restarted forever.  Each job declares a
  completion marker; when the process is gone AND the marker is in the log,
  the job is retired.  Without this the supervisor would relaunch a finished
  sweep every minute until morning.

  sweep_models is watched through the NEWEST FILE IN sweep_logs/ rather than
  its own log, because its own log prints once per (model, arm) -- up to ninety
  minutes of deliberate silence -- while the per-model log advances per cell.
"""
import os, re, subprocess, sys, time, json

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
LOG = HERE + "guard.log"
STATE = HERE + "guard_state.json"


def env():
    """Provider keys, read from the 0600 env files, never logged."""
    e = dict(os.environ)
    for f in ("feather.env", "nvidia.env"):
        p = HERE + f
        if not os.path.exists(p):
            continue
        for line in open(p):
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                e[k.strip()] = v.strip().strip('"').strip("'")
    return e


JOBS = {
    "kaggle_enrich": dict(
        script="kaggle_enrich.py", log="kaggle_enrich.log",
        stall=1500, done=r"^DONE: \d+ enriched"),
    "openml_harvest": dict(
        script="openml_harvest.py", log="openml_harvest.log",
        stall=1200, done=r"surviving sentences across"),
    "hf_harvest": dict(
        script="hf_harvest.py", log="hf_harvest.log",
        stall=1500, done=r"surviving sentences across"),
    # The loop owns memcheck now: it waits for the in-flight standalone pass,
    # then re-runs it until nothing is left failing.  Watching memcheck_all.py
    # directly here would restart a pass the loop is about to start itself.
    # Stall allowance covers the 25-minute inter-pass sleep with margin: the
    # subprocess inherits this log, so a running pass advances it continuously
    # and only the deliberate sleep is quiet.
    "memcheck_loop": dict(
        script="memcheck_loop.py", log="memcheck_loop.log",
        stall=3000, done=r"^FINAL: \d+ tests succeeded"),
    "sweep_models": dict(
        script="sweep_models.py", log="sweep_models.log",
        watch_dir="sweep_logs", stall=2100, done=r"arms clean",
        args=["2"]),
    # Prints a waiting line every 60s while it blocks on sweep_models, so a
    # deliberate wait cannot be mistaken for a wedge.
    "sweep_stratb": dict(
        script="sweep_stratb.py", log="sweep_stratb.log",
        watch_dir="sweep_logs", stall=2100, done=r"arms clean",
        args=["2"]),
    "sweep_stratc": dict(
        script="sweep_stratc.py", log="sweep_stratc.log",
        watch_dir="sweep_logs", stall=2100, done=r"arms clean",
        args=["2"]),
}


def say(msg):
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as fh:
        fh.write(line + "\n")


def pids(script):
    """PIDs of a PYTHON process running this script.

    Matched on the bare filename, not a full command line: jobs already in
    flight were started with a relative path and the ones this supervisor
    starts use an absolute one, so a pattern pinning the prefix would see every
    running job as dead and start a second copy of each.

    But a bare `pgrep -f sweep_stratc.py` matches ANY command line containing
    that text -- including a shell wrapper, an editor, or an operator running
    `tail -f sweep_stratc.log` in a `bash -c` whose whole script is on the
    command line.  That is not hypothetical: sweep_stratc was killed and
    restarted at 01:58 to pick up a new dataset, and guard did not relaunch it,
    because the very shell command checking on it contained the script name and
    guard read that as the job being alive.  The job sat dead for minutes.

    Same self-match family as the `pgrep -f X` deadlock in the wait-wrappers,
    which has now cost time three times.  The fix is to require the process to
    be a python interpreter running that script, checked against /proc rather
    than against a substring."""
    out = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or pid == str(os.getpid()):
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as fh:
                argv = fh.read().split(b"\0")
        except (OSError, IOError):
            continue                       # process exited mid-scan
        argv = [a.decode(errors="replace") for a in argv if a]
        if not argv:
            continue
        # argv[0] must be the interpreter, and some later argument must end in
        # the script name -- so `bash -c '... sweep_stratc.py ...'` never counts.
        if "python" not in os.path.basename(argv[0]):
            continue
        if any(a.split("/")[-1] == script for a in argv[1:]):
            out.append(pid)
    return out


def freshness(job):
    """Seconds since the job's liveness signal last advanced."""
    paths = []
    if job.get("watch_dir"):
        d = HERE + job["watch_dir"]
        if os.path.isdir(d):
            paths += [os.path.join(d, f) for f in os.listdir(d)]
    paths.append(HERE + job["log"])
    ts = [os.path.getmtime(p) for p in paths if os.path.exists(p)]
    return time.time() - max(ts) if ts else 1e9


def finished(job):
    """Has this job printed its completion marker anywhere in its log?

    The marker is searched for in the WHOLE file, not the last 4 KB.  hf_harvest
    prints its summary line and then lists every candidate dataset underneath,
    so the marker scrolled out of a 4 KB tail: guard read a finished job as dead
    and relaunched it every two minutes, each relaunch re-indexing 18,000
    datasets against somebody else's API to rediscover that the work was
    already done.

    Scanning the whole file risks a false positive only if a job prints its own
    completion string before finishing, which none of these do."""
    p = HERE + job["log"]
    if not os.path.exists(p):
        return False
    return bool(re.search(job["done"], open(p, errors="replace").read(), re.M))


def launch(name, job, e):
    cmd = [sys.executable, "-u", HERE + job["script"]] + job.get("args", [])
    fh = open(HERE + job["log"], "a")
    fh.write(f"\n===== guard relaunch {time.strftime('%H:%M:%S')}\n")
    fh.flush()
    subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=HERE,
                     env=e, start_new_session=True)
    say(f"RELAUNCHED {name}")


def main():
    e = env()
    say(f"guard up, watching {len(JOBS)} jobs")
    while True:
        # RE-READ the state file every pass.  Loading it once at startup meant
        # an operator marking a job "retired" from outside had no effect on the
        # running supervisor: sweep_models was stopped deliberately, written to
        # guard_state.json as retired, and relaunched twice anyway by a guard
        # holding a stale copy in memory -- which put it straight back into
        # contention with the grid it had been stopped for.
        state = json.load(open(STATE)) if os.path.exists(STATE) else {}
        alive = 0
        for name, job in JOBS.items():
            if state.get(name) == "retired":
                continue
            running = pids(job["script"])
            if finished(job) and not running:
                state[name] = "retired"
                say(f"RETIRED {name} (completion marker present)")
                continue
            if not running:
                say(f"DEAD {name}: no process")
                launch(name, job, e)
                state[name] = "restarted"
                continue
            age = freshness(job)
            if age > job["stall"]:
                say(f"STALLED {name}: {int(age)}s since last output "
                    f"(limit {job['stall']}s); killing {running}")
                for p in running:
                    subprocess.run(["kill", "-9", p])
                time.sleep(3)
                launch(name, job, e)
                state[name] = "restarted"
                continue
            alive += 1
        json.dump(state, open(STATE, "w"), indent=1)
        if int(time.time()) % 900 < 60:
            say(f"heartbeat: {alive} healthy, "
                f"{sum(1 for v in state.values() if v == 'retired')} retired")
        time.sleep(60)


if __name__ == "__main__":
    main()
