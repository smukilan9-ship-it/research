"""Re-run tabmemcheck until the failures are gone or provably permanent.

WHY A LOOP AND NOT A LONGER RETRY

  The first pass is already reporting `FAIL keys exhausted` on Gemini cells.
  That is not a property of the cell -- it is a property of nine API keys
  having spent their DAILY quota, which no amount of in-run backoff can fix
  because the quota does not reset for hours.  Retrying harder inside one pass
  burns the remaining budget on 429s; waiting and retrying later gets the
  answer.

  memcheck_all.py already skips any cell that has a stored non-error result and
  retries every cell that has an error, so re-running it IS the retry, and each
  pass costs only the outstanding failures.

WHY THIS MATTERS RATHER THAN BEING TIDINESS

  An error stored in a results file is not a result.  The first memcheck
  campaign in this project recorded 55 HTTP 429s as data and reported "15/15
  datasets complete"; the resulting table was of quota exhaustion, not
  memorisation.  A run that ends with failures still outstanding must say so
  loudly enough that nobody reads the file as finished, which is what the final
  summary here does.
"""
import os, subprocess, sys, time, json

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "memcheck_all.json"
PASSES = int(sys.argv[1]) if len(sys.argv) > 1 else 8
GAP = int(sys.argv[2]) if len(sys.argv) > 2 else 1500     # 25 min


def tally():
    if not os.path.exists(OUT):
        return 0, 0
    res = json.load(open(OUT))
    ok = bad = 0
    for ds in res.values():
        for cell in ds.values():
            for v in cell.values():
                ok += "error" not in v
                bad += "error" in v
    return ok, bad


def wait_for_running():
    """Do not start a second copy alongside the pass already in flight."""
    while True:
        alive = subprocess.run(["pgrep", "-f", "memcheck_all.py"],
                               capture_output=True, text=True).stdout.split()
        if not alive:
            return
        print(f"  waiting for the in-flight memcheck_all pass ({len(alive)} "
              f"proc) ...", flush=True)
        time.sleep(60)


def main():
    wait_for_running()
    for p in range(1, PASSES + 1):
        ok, bad = tally()
        if p > 1 and bad == 0:
            print(f"no outstanding failures after pass {p-1}; stopping",
                  flush=True)
            break
        print(f"\n########## MEMCHECK PASS {p}/{PASSES}  "
              f"({ok} stored ok, {bad} to retry)", flush=True)
        subprocess.run([sys.executable, "-u", HERE + "memcheck_all.py"],
                       cwd=HERE)
        ok, bad = tally()
        print(f"after pass {p}: {ok} ok, {bad} still failing", flush=True)
        if bad and p < PASSES:
            print(f"  sleeping {GAP}s before the next attempt (quota resets "
                  f"are measured in hours, not seconds)", flush=True)
            time.sleep(GAP)
    ok, bad = tally()
    print(f"\nFINAL: {ok} tests succeeded, {bad} failed", flush=True)
    if bad:
        print("INCOMPLETE: stored errors are NOT results and must not be read "
              "as findings.", flush=True)


if __name__ == "__main__":
    main()
