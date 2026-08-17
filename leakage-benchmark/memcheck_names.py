"""feature_names_test only, over all 15 datasets, one call each.

WHY SEPARATE FROM memcheck.py

  The full tabmemcheck suite is dominated by row_completion_test, which fires
  25 queries per dataset with 7 few-shot examples each.  That is the strongest
  evidence and the slowest to get.

  feature_names_test is ONE call per dataset and is the test this paper
  actually needs: our prompts hand the model a column list, so the question
  that bears on our numbers is whether the model can produce that list from
  memory.  This runs it alone so the table exists while the rest is still
  going.

  Writes its own file so it cannot race the full run's checkpoint.
"""
import os, sys, json, time, io, contextlib, re

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "memcheck_names.json"
sys.path.insert(0, HERE)

import tabmemcheck as tmc
from memcheck import export, keys


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.5-flash"
    KEYS = keys()
    paths = export()
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    ki = 0
    for name, p in paths.items():
        if name in res and "error" not in res[name]:
            continue
        last = None
        for _ in range(len(KEYS) * 3):
            llm = tmc.gemini_setup(model=model, api_key=KEYS[ki % len(KEYS)])
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    r = tmc.feature_names_test(p, llm)
                res[name] = dict(result=repr(r))
                print(f"  {name:<12} ok", flush=True)
                break
            except Exception as e:
                last = e
                if "429" in str(e) or "ResourceExhausted" in type(e).__name__:
                    ki += 1; time.sleep(1.5); continue
                res[name] = dict(error=f"{type(e).__name__}: {e}"[:200])
                print(f"  {name:<12} FAIL {type(e).__name__}", flush=True)
                break
        else:
            res[name] = dict(error=f"all keys exhausted: {last}"[:200])
            print(f"  {name:<12} FAIL all keys exhausted", flush=True)
        json.dump(res, open(OUT, "w"), indent=1)
    ok = sum(1 for v in res.values() if "error" not in v)
    print(f"\n{ok}/{len(paths)} feature-name tests succeeded -> {OUT}")


if __name__ == "__main__":
    main()
