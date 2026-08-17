"""Finish enriching the Kaggle index.  Enrichment only -- the index is done.

WHY THIS IS A SEPARATE FILE FROM kaggle_deep.py

  kaggle_deep.main() re-runs the 60-query index sweep before it enriches.  The
  index is complete at 8,694 datasets and re-walking it costs ~600 API calls
  that produce nothing new -- and worse, those calls burn the rate-limit
  budget that the enrichment needs, so the re-index actively makes the part we
  care about slower.

  It also stopped on the first Throttled.  That was right for a foreground run
  with a person watching.  This one runs unattended for hours, so a 429 is a
  reason to wait, never a reason to stop: the only exit conditions are "every
  dataset enriched" or "this ref returns a non-429 error", and the second is
  recorded per-ref so a permanently dead ref cannot spin forever.

  Checkpoints every 25 datasets.  Four separate runs in this project have been
  killed by a timeout or a stray signal; the cost of a checkpoint is one file
  write and the cost of not having one is the whole night.
"""
import json, os, sys, time, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "kaggle_meta/"
CURL = HERE + "kaggle.curl"
FULL = OUT + "full.json"
DEAD = OUT + "dead_refs.json"


def get(url):
    """One GET.  Returns (body, status).  Never raises on HTTP status."""
    p = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "90", "-K", CURL,
         "-w", "\n%{http_code}", url],
        capture_output=True, text=True)
    if p.returncode != 0 or "\n" not in p.stdout:
        return None, "curl"
    body, _, code = p.stdout.rpartition("\n")
    return body, code.strip()


def main():
    idx = {r["ref"]: r for r in json.load(open(OUT + "deep_index.json"))}
    cache = json.load(open(FULL)) if os.path.exists(FULL) else {}
    dead = json.load(open(DEAD)) if os.path.exists(DEAD) else {}
    todo = [r for r in idx if r not in cache and r not in dead]
    print(f"{len(idx)} indexed | {len(cache)} enriched | {len(dead)} dead | "
          f"{len(todo)} to fetch", flush=True)

    delay = 1.2          # adaptive: rises on 429, decays on success
    done = 0
    for ref in todo:
        for attempt in range(40):
            body, code = get(
                f"https://www.kaggle.com/api/v1/datasets/view/{ref}")
            if code == "200":
                try:
                    cache[ref] = json.loads(body)
                except Exception:
                    dead[ref] = "unparseable JSON"
                delay = max(1.0, delay * 0.9)
                break
            if code == "429":
                delay = min(30.0, delay * 1.35)
                time.sleep(min(90, 5 * 1.6 ** min(attempt, 8)))
                continue
            # 403/404 and friends: the ref is gone or private.  Record it so
            # the next resume does not retry it, and so the denominator in the
            # write-up counts it as unreachable rather than as clean.
            dead[ref] = f"HTTP {code}"
            break
        else:
            dead[ref] = "429 after 40 attempts"
        done += 1
        if done % 25 == 0:
            json.dump(cache, open(FULL, "w"))
            json.dump(dead, open(DEAD, "w"))
            print(f"  {len(cache):>6} enriched  {len(dead):>4} dead  "
                  f"{len(todo)-done:>6} left  delay={delay:.1f}s", flush=True)
        time.sleep(delay)

    json.dump(cache, open(FULL, "w"))
    json.dump(dead, open(DEAD, "w"))
    print(f"\nDONE: {len(cache)} enriched, {len(dead)} unreachable, "
          f"{len(idx)} indexed", flush=True)


if __name__ == "__main__":
    main()
