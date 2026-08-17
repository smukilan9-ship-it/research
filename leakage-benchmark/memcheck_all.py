"""Bordt et al.'s tabmemcheck over EVERY API-served model, not just Gemini.

WHY THE SINGLE-MODEL VERSION WAS NOT ENOUGH

  memcheck.py ran gemini-3.5-flash and produced the bound the paper reports:
  the model recalls 33% of columns but only 19% of the LEAKING ones.  That is
  one model's memorisation profile being used to bound fourteen models'
  detection scores.  A reviewer is entitled to ask whether the model that
  scores best is also the model that remembers most, and one model's results
  cannot answer that.  Running the full roster turns a bound into a
  correlation that can be checked: if detection F1 tracked recall, the
  scatter would show it.

HOW NON-GEMINI MODELS ARE DRIVEN

  tabmemcheck ships setups for OpenAI and Gemini only.  Featherless and NVIDIA
  NIM both speak the OpenAI chat surface, so an OpenAI client pointed at their
  base_url drives them unchanged -- no fork, no reimplementation of the tests,
  which is the entire reason for using the authors' package instead of writing
  our own probe.

  chat_mode MUST be forced.  OpenAILLM auto-detects it by looking for "gpt-3.5"
  or "gpt-4" in the model name, so every model here would default to the
  legacy /completions endpoint, which Featherless and NVIDIA do not serve.
  The failure is a 404 per call, which the retry decorator would patiently
  repeat seven times before surfacing.

TEST ORDER IS DELIBERATE

  feature_names_test first for every model, then dataset_name, then header,
  then row_completion.  feature_names is the test this paper's numbers
  actually rest on -- our prompts hand the model a column list -- and it costs
  one call.  row_completion is 25 calls with 7 few-shot examples each and is
  the first thing a rate limit kills.  Ordering by (value / cost) means an
  interrupted run still has the table that matters, which is what happened
  last time: row_completion competed for quota and 0 of 15 finished.
"""
import os, sys, json, time, io, contextlib

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "memcheck_all.json"
sys.path.insert(0, HERE)

import tabmemcheck as tmc
from tabmemcheck.llm import OpenAILLM
from openai import OpenAI
from memcheck import export

TESTS = ["feature_names_test", "dataset_name_test",
         "header_test", "row_completion_test"]

# (label, api model id, provider)  -- provider decides the client and keyring
#
# ORDER MATTERS AND THE FIRST ORDER WAS WRONG.  Gemini led the list, and Gemini's
# nine keys were already at their DAILY quota, so the run spent its whole first
# pass cycling every key through a 429 on one model while twelve models with
# working keys waited behind it: 23 results and 28 quota errors, none of them
# from a provider that could have answered.  Providers whose keys work go first
# now, and Gemini is retried at the end of each pass and by the outer loop.
ROSTER = [
    ("nvidia/nemotron-3-super-120b-a12b::high", "nvidia/nemotron-3-super-120b-a12b",       "nvidia"),
    ("deepseek-ai/deepseek-v4-flash-0731::high","deepseek-ai/deepseek-v4-flash-0731",      "nvidia"),
    ("deepseek-ai/DeepSeek-V4-Pro::high",       "deepseek-ai/DeepSeek-V4-Pro",             "featherless"),
    ("moonshotai/Kimi-K3::high",                "moonshotai/Kimi-K3",                      "featherless"),
    ("zai-org/GLM-5.2::high",                   "zai-org/GLM-5.2",                         "featherless"),
    ("Qwen/Qwen3-Coder-480B-A35B-Instruct",     "Qwen/Qwen3-Coder-480B-A35B-Instruct",     "featherless"),
    ("mistralai/Mistral-Large-Instruct-2411",   "mistralai/Mistral-Large-Instruct-2411",   "featherless"),
    ("Qwen/Qwen3-Next-80B-A3B-Instruct",        "Qwen/Qwen3-Next-80B-A3B-Instruct",        "featherless"),
    ("Qwen/Qwen2-72B-Instruct",                 "Qwen/Qwen2-72B-Instruct",                 "featherless"),
    ("unsloth/Llama-3.3-70B-Instruct",          "unsloth/Llama-3.3-70B-Instruct",          "featherless"),
    ("Nexusflow/Athene-V2-Chat",                "Nexusflow/Athene-V2-Chat",                "featherless"),
    ("google/gemma-4-E4B-it",                   "google/gemma-4-E4B-it",                   "featherless"),
    ("gemini-3.5-flash",                        "gemini-3.5-flash",                        "gemini"),
    ("gemini-3.7-flash",                        "gemini-3.7-flash",                        "gemini"),
]
# Consecutive "all keys exhausted" results for one provider before this pass
# gives up on it.  Without a breaker, a dead provider costs 60 cells x every
# key x a backoff sleep, which is how the first pass burned an hour to produce
# 28 quota errors.  The outer loop retries the whole provider later, when the
# daily quota may have reset -- which is the only thing that actually fixes it.
BREAKER = 4
BASE = {"featherless": "https://api.featherless.ai/v1",
        "nvidia": "https://integrate.api.nvidia.com/v1"}
ENVVAR = {"featherless": "FEATHERLESS_API_KEY", "nvidia": "NVIDIA_API_KEY",
          "gemini": "GEMINI_API_KEY"}


def keyring(provider):
    p = ENVVAR[provider]
    ks = []
    for n in [p] + [f"{p}_{i}" for i in range(1, 10)]:
        v = (os.environ.get(n) or "").strip()
        if v and v not in ks:
            ks.append(v)
    return ks


def make_llm(api_model, provider, key):
    if provider == "gemini":
        return tmc.gemini_setup(model=api_model, api_key=key)
    # chat_mode forced: see module docstring
    return OpenAILLM(OpenAI(api_key=key, base_url=BASE[provider]),
                     api_model, chat_mode=True)


# Failures that will never succeed on a retry, because they happen inside
# tabmemcheck's own parsing rather than at the API.  Both are the 144- and
# 122-column CSVs (CRIME and MI) defeating its delimiter sniffing; the message
# is byte-identical for every model and every pass.
#
# The distinction matters for QUOTA, not tidiness.  Every pass re-attempted
# these on every model, so the loop spent its first calls on the two widest
# tables in the corpus to rediscover a fixed fact -- while gemini-3.7, which
# actually needed the quota to finish its remaining datasets, waited behind
# them.  A transient "all keys exhausted: 429" must still be retried, and is.
PERMANENT = ("Could not determine delimiter",
             "Unable to construct a query where the desired output")


def permanent(err):
    return bool(err) and any(p in str(err) for p in PERMANENT)


def save(res):
    """Merge `res` into whatever is on disk NOW, then write atomically.

    This file is written by more than one process at a time on purpose: the
    loop's child works the featherless roster while a hand-launched pass works
    gemini, because they are different providers with different quotas.  The
    previous code snapshotted the file once at startup and wrote its whole
    in-memory copy back after every test, so the two processes silently
    clobbered each other -- last writer wins, and every model the OTHER process
    had added since the snapshot vanished.

    It did happen.  gemini-3.7-flash was complete across 15 datasets at 00:38
    and was gone from the file by 01:23, erased by the concurrent featherless
    pass writing back a snapshot taken before gemini-3.7 existed.  Those tests
    have to be re-run; nothing else recovers them, because only the payloads
    are lost and the logs keep just the ok/FAIL line.

    This is the sixth instance in this project of one bug: state inferred from
    a stale view and then written back as if it were current.  guard.py had it
    with guard_state.json and was fixed the same way -- re-read at the point of
    write, merge per key, never assume you are the only writer.

    Merge is per (model, dataset, test) so two processes working different
    models, or different datasets of one model, both survive.  The write goes
    to a temp file and is renamed, so a crash mid-write cannot leave a
    truncated JSON where 1.9 MB of results used to be."""
    disk = {}
    if os.path.exists(OUT):
        try:
            disk = json.load(open(OUT))
        except Exception:
            disk = {}                      # unreadable: keep what we have
    for model, dsets in res.items():
        for ds, cell in dsets.items():
            disk.setdefault(model, {}).setdefault(ds, {}).update(cell)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(disk, fh, indent=1)
    os.replace(tmp, OUT)
    return disk


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    paths = export()
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}

    for label, api_model, provider in ROSTER:
        if only and only not in label:
            continue
        keys = keyring(provider)
        if not keys:
            print(f"SKIP {label}: no key for {provider}", flush=True)
            continue
        ki = 0
        dry = 0                       # consecutive all-keys-exhausted results
        res.setdefault(label, {})
        print(f"\n=== {label}  ({provider}, {len(keys)} key(s))", flush=True)
        for test in TESTS:
            if dry >= BREAKER:
                break
            fn = getattr(tmc, test)
            for name, p in paths.items():
                if dry >= BREAKER:
                    print(f"  BREAKER: {provider} exhausted {dry} times in a "
                          f"row; skipping the rest of {label} this pass",
                          flush=True)
                    break
                cell = res[label].setdefault(name, {})
                if test in cell and "error" not in cell[test]:
                    continue
                if test in cell and permanent(cell[test].get("error")):
                    # Deterministic failure inside tabmemcheck, not an API
                    # problem.  Retrying it every pass costs the whole loop the
                    # widest two CSVs in the corpus before it reaches any work
                    # that can succeed, and the answer never changes.
                    continue
                last = None
                for attempt in range(len(keys) * 3):
                    llm = make_llm(api_model, provider, keys[ki % len(keys)])
                    buf = io.StringIO()
                    try:
                        with contextlib.redirect_stdout(buf):
                            r = fn(p, llm)
                        # NOT truncated: feature_names_test's third element is
                        # the whole predicted column list and a character cap
                        # silently made it unparseable last time.
                        cell[test] = dict(result=repr(r),
                                          log=buf.getvalue()[-4000:])
                        dry = 0
                        print(f"  {name:<12}{test:<22}ok", flush=True)
                        break
                    except Exception as e:
                        last = e
                        s = str(e)
                        if ("429" in s or "rate" in s.lower()
                                or "quota" in s.lower()
                                or "ResourceExhausted" in type(e).__name__):
                            ki += 1
                            time.sleep(4)
                            continue
                        cell[test] = dict(error=f"{type(e).__name__}: {e}")
                        print(f"  {name:<12}{test:<22}FAIL "
                              f"{type(e).__name__}", flush=True)
                        break
                else:
                    cell[test] = dict(error=f"all keys exhausted: {last}")
                    dry += 1
                    print(f"  {name:<12}{test:<22}FAIL keys exhausted "
                          f"({dry}/{BREAKER})", flush=True)
                save(res)
                time.sleep(0.4)

    ok = bad = 0
    for lab, ds in res.items():
        for nm, cell in ds.items():
            for t, v in cell.items():
                ok += "error" not in v
                bad += "error" in v
    print(f"\n{ok} tests succeeded, {bad} failed -> {OUT}", flush=True)
    if bad:
        print("INCOMPLETE: failed tests are stored as errors and must not be "
              "read as findings.", flush=True)


if __name__ == "__main__":
    main()
