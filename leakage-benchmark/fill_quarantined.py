"""Refill the quarantined gemini-3.5 cells WITHOUT changing any run parameter.

WHY A RETRY LOOP AND NOT A BIGGER TOKEN BUDGET

  These cells were attributed to "our own token budget" (§8).  That is wrong.
  At temperature=0.0 this model intermittently returns finish_reason='length'
  after a few hundred visible tokens no matter how large max_tokens is -- 12 of
  40 entries at max_tokens=16000, reproducibly on some prompts.  Removing the
  temperature field fixes it outright, and CRIME (144 columns) never fails even
  at temperature 0, so it is prompt-specific rather than a size limit.

  Refilling by dropping temperature would make these cells the only ones in a
  1,808-cell corpus run at a different temperature, and a cell that differs in
  a run parameter is not comparable with the cells it is pooled against.  So
  the temperature stays at 0.0 and the cell is simply retried: the failure is
  intermittent for most prompts, and a complete answer at the corpus's own
  settings is worth more than a complete answer at different ones.

  A cell that will not complete after MAX_TRY attempts stays quarantined and is
  reported.  Nothing partial is ever written into the live cache.
"""
import json, glob, os, random, re, subprocess, sys, tempfile, time
import runner as RN, prompts, verify_paper as V

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
MAX_TRY = 8
PACE = 20        # seconds between calls; the API 429s with a ~51s retryDelay
URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
KEYS = [l.split("=", 1)[1].strip() for l in open(HERE + "gemini.env")
        if l.startswith("GEMINI_API_KEY_")]

DSKEY = {"AI4I": "ai4i", "KOI": "koi", "LC": "lc", "STUDENT": "student"}


def build(bundle, cond, seed):
    cols = bundle["columns"][:]
    random.Random(seed).shuffle(cols)
    if cond == 9:
        return prompts.SYSTEM, prompts.build_derivation_v2(bundle["name"], cols, bundle["target"])
    if cond == 7:
        return prompts.SYSTEM, prompts.build_surrogate(bundle["name"], cols, bundle["target"])
    if cond == 6:
        return prompts.SYSTEM, prompts.build_derivation(bundle["name"], cols, bundle["target"])
    if cond == 5:
        return prompts.EXPERT_SYSTEM, prompts.build_expert(
            bundle["name"], cols, bundle["target"], bundle["description"], None)
    return prompts.SYSTEM, prompts.build(
        bundle["name"], cols, cond, bundle["target"], bundle["prediction_point"],
        bundle["description"], None)


def ask(sysmsg, user, key):
    body = {"model": "gemini-3.5-flash", "max_tokens": 16000, "temperature": 0.0,
            "messages": [{"role": "system", "content": sysmsg},
                         {"role": "user", "content": user}]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(body, f); bp = f.name
    with tempfile.NamedTemporaryFile("w", suffix=".curl", delete=False) as f:
        f.write(f'header = "Authorization: Bearer {key}"\n'
                f'header = "Content-Type: application/json"\n'); cp = f.name
    os.chmod(cp, 0o600)
    try:
        out = subprocess.run(["curl", "-sS", "-K", cp, "-d", "@" + bp, URL],
                             capture_output=True, text=True, timeout=600).stdout
    finally:
        os.unlink(bp); os.unlink(cp)
    try:
        d = json.loads(out); ch = d["choices"][0]
        return ch.get("finish_reason"), (ch["message"]["content"] or "")
    except Exception:
        # Distinguish rate limiting from a real failure.  Reporting a 429 as
        # "error" made seven recoverable cells look permanently stuck.
        if '"code": 429' in out or "RESOURCE_EXHAUSTED" in out:
            m = re.search(r'"retryDelay":\s*"(\d+)s"', out)
            wait = int(m.group(1)) + 5 if m else 60
            print(f"      429 rate limit, waiting {wait}s", flush=True)
            time.sleep(wait)
            return "429", ""
        return "error", ""


def main():
    missing = []
    for f in glob.glob(HERE + "responses_truncated/*.json"):
        r = json.load(open(f))
        if "gemini-3.5" not in r["model"]:
            continue
        k = (r["dataset"], r["condition"], r.get("seed"))
        missing.append(k)
    live = {(r["dataset"], r["condition"], r.get("seed"))
            for r in (json.load(open(f)) for f in glob.glob(HERE + "responses/*.json"))
            if "gemini-3.5" in r["model"] and not r.get("paraphrase")}
    todo = sorted({k for k in missing if k not in live and k[0] in DSKEY})
    print(f"{len(todo)} quarantined cells to refill, temperature 0.0 unchanged, "
          f"up to {MAX_TRY} attempts each\n")
    filled, stuck = 0, []
    for ds, cond, seed in todo:
        b = RN.spec_bundle(DSKEY[ds])
        sysmsg, user = build(b, cond, seed)
        need = len(b["columns"])
        for attempt in range(1, MAX_TRY + 1):
            time.sleep(PACE)
            fr, txt = ask(sysmsg, user, KEYS[attempt % len(KEYS)])
            p, _ = V.parse(txt)
            n = len((p or {}).get("columns", []))
            if fr == "stop" and n >= need:
                cid = f"refill_{ds}_C{cond}_s{seed}"
                json.dump(dict(model="gemini-3.5-flash", provider="gemini",
                               dataset=ds, shown_as=ds, paraphrase=False,
                               alias=None, condition=cond, seed=seed,
                               status="ok", raw=txt,
                               ts=time.strftime("%Y-%m-%dT%H:%M:%S")),
                          open(HERE + f"responses/{cid}.json", "w"), indent=1)
                print(f"  {ds:<9} C{cond} s{seed}  FILLED on attempt {attempt} "
                      f"({n}/{need})")
                filled += 1
                break
            print(f"  {ds:<9} C{cond} s{seed}  attempt {attempt}: "
                  f"finish={fr} {n}/{need}")
        else:
            stuck.append((ds, cond, seed))
    print(f"\nfilled {filled}; still stuck {len(stuck)}: {stuck}")


if __name__ == "__main__":
    main()
