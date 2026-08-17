"""One process that runs the whole campaign and supervises itself.

WHY THIS REPLACES supervise.sh + watchdog.sh

  The shell version had three layers -- a harness wrapper, supervise.sh, and
  watchdog.sh -- and killed things by PATTERN:

      pkill -9 -f "supervise.sh"

  The harness launches a tracked job as `bash -c '... ./supervise.sh ...'`, so
  that pattern matches the wrapper too.  The watchdog's first restart therefore
  killed the very process tree that was supposed to be doing the restarting,
  and both jobs exited code 1 with no output.  A watchdog whose failure mode is
  suicide is worse than no watchdog, because it looks like it is working.

  So: no nested shells, no setsid, no pattern kills.  One Python process owns
  a child by PID, watches its stdout, and kills exactly that PID and nothing
  else.

WHAT IT WATCHES

  Not "is the child alive" -- the two real failures were HANGS, where the
  process was alive and doing nothing for hours.  It watches PROGRESS: the
  child prints one line per completed cell, and a cell takes ~90s.  If no line
  arrives for STALL_S, the child is wedged regardless of what its state says,
  and it is killed and the phase re-run.

  Re-running is cheap: cached cells are skipped, failed cells are never cached,
  so a restart costs only the calls in flight.
"""
import os, subprocess, sys, threading, time, queue, signal

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "overnight.log")

# The child now emits a heartbeat every 3 minutes (runner.py), so silence is
# unambiguous.  Kept well above the heartbeat interval so a slow write or a
# scheduling hiccup cannot be mistaken for a hang.
STALL_S = 10 * 60
COOLDOWN_S = 75            # Featherless keeps generating after we kill curl;
                           # restarting instantly hits the concurrency wall
MAX_ATTEMPTS = 12          # per phase

MODELS = ("moonshotai/Kimi-K3,zai-org/GLM-5.2,deepseek-ai/DeepSeek-V4-Pro,"
          "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16")
BASE = ["python3", "-u", "runner.py", "--provider", "featherless",
        "--reasoning", "high", "--models", MODELS,
        "--workers", "3", "--max-tokens", "20000", "--http-timeout", "900"]

PHASES = [
    ("1  main corpus, C1+C6",
     BASE + ["--all", "--conditions", "1,6", "--repeats", "1"]),
    ("2  explicit transfer set, C1+C2+C6, 3 shuffles",
     BASE + ["--datasets", "mi,crime,student", "--conditions", "1,2,6",
             "--repeats", "3"]),
    ("3  main corpus, 3 shuffles, for intervals",
     BASE + ["--all", "--conditions", "1,6", "--repeats", "3"]),
    ("4  memorisation control, columns renamed",
     BASE + ["--all", "--conditions", "1,6", "--repeats", "1", "--paraphrase"]),
]


def say(msg):
    line = f"{time.strftime('%H:%M:%S', time.gmtime())} [drive] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as fh:
        fh.write(line + "\n")


def pump(stream, q):
    for line in iter(stream.readline, ""):
        q.put(line)
    q.put(None)


def run_once(argv):
    """Run one phase attempt. Returns 'done', 'stalled' or 'exited'."""
    p = subprocess.Popen(argv, cwd=HERE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1,
                         start_new_session=True)      # own group, killable alone
    q = queue.Queue()
    threading.Thread(target=pump, args=(p.stdout, q), daemon=True).start()
    last = time.time()
    with open(LOG, "a") as fh:
        while True:
            try:
                line = q.get(timeout=15)
            except queue.Empty:
                if time.time() - last > STALL_S:
                    say(f"no output for {STALL_S//60}m -- killing pid {p.pid}")
                    try:
                        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                    except Exception as e:
                        say(f"kill failed: {type(e).__name__}")
                    p.wait(timeout=30)
                    return "stalled"
                continue
            if line is None:
                p.wait(timeout=60)
                return "done" if p.returncode == 0 else "exited"
            last = time.time()
            fh.write(line)
            fh.flush()


def main():
    say(f"campaign start, {len(PHASES)} phases")
    for name, argv in PHASES:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            say(f"PHASE {name}  (attempt {attempt}/{MAX_ATTEMPTS})")
            outcome = run_once(argv)
            say(f"PHASE {name} -> {outcome}")
            if outcome == "done":
                break
            say(f"cooling down {COOLDOWN_S}s before retry")
            time.sleep(COOLDOWN_S)
        else:
            say(f"PHASE {name} exhausted attempts; moving on")
    say("ALL PHASES DONE")


if __name__ == "__main__":
    main()
