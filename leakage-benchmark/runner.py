"""Run the provenance-detection benchmark against one or more models.

    export FEATHERLESS_API_KEY=...        # or ANTHROPIC_API_KEY / OPENAI_API_KEY
    python3 runner.py --models meta-llama/Meta-Llama-3.1-8B-Instruct --conditions 1
    python3 runner.py --models A,B --conditions 0,1,2,3,4 --repeats 3

KEY HANDLING
  Keys are read from the environment only.  They are never written to the cache,
  never printed, and are scrubbed from exception text before anything is logged.
  If a key ever appears in a traceback, that is a bug -- report it.

COST CONTROL
  Every response is cached on disk keyed by (model, dataset, condition, seed).
  Re-running is free.  Use --dry-run to see the call count and rough token
  volume before spending anything.
"""
import argparse, hashlib, json, os, random, re, subprocess, sys, tempfile, threading, time, urllib.request
import concurrent.futures as cf
import warnings
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import prompts, harness as H

CACHE = HERE + "responses/"
ENDPOINTS = {
    "featherless": ("https://api.featherless.ai/v1/chat/completions", "FEATHERLESS_API_KEY"),
    "openai":      ("https://api.openai.com/v1/chat/completions",     "OPENAI_API_KEY"),
    "anthropic":   ("https://api.anthropic.com/v1/messages",          "ANTHROPIC_API_KEY"),
    # Google's OpenAI-compatible surface, so the request body is unchanged.
    "gemini":      ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    "GEMINI_API_KEY"),
    # NVIDIA NIM, same OpenAI-compatible shape.  Worth having as a SECOND host
    # for models Featherless also serves: nemotron-3-super-120b returns in 13s
    # here against minutes there, on the same weights.  Cells are never pooled
    # across hosts -- the model ids differ, and the quantisation may too.
    "nvidia":      ("https://integrate.api.nvidia.com/v1/chat/completions",
                    "NVIDIA_API_KEY"),
}
GEMINI_LIST = "https://generativelanguage.googleapis.com/v1beta/models"


def keyring(provider):
    """Every key available for a provider, in a stable order.

    Gemini quota is per-key and tight, so several keys are the normal case:
    GEMINI_API_KEY, GEMINI_API_KEY_1..9, or GEMINI_API_KEYS as a comma list.
    Rotating across them spreads rate limits instead of serialising on one.
    Keys are read from the environment only and never written anywhere.
    """
    _, primary = ENDPOINTS[provider]
    names = [primary] + [f"{primary}_{i}" for i in range(1, 10)]
    keys = []
    for n in names:
        v = (os.environ.get(n) or "").strip()
        if v and v not in keys:
            keys.append(v)
    for v in (os.environ.get(primary + "S") or "").split(","):
        v = v.strip()
        if v and v not in keys:
            keys.append(v)
    return keys


def list_gemini_models(key):
    """Ask the API which models exist rather than guessing IDs from memory."""
    r = subprocess.run(["curl", "-sS", "--max-time", "60",
                        "-H", f"x-goog-api-key: {key}", GEMINI_LIST],
                       capture_output=True, text=True, timeout=70)
    d = json.loads(r.stdout)
    if isinstance(d, list):          # same list-wrapped error shape as above
        d = d[0] if d else {}
    if "error" in d:
        raise RuntimeError(str(d["error"])[:200])
    out = []
    for m in d.get("models", []):
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        out.append((m["name"].replace("models/", ""),
                    m.get("inputTokenLimit", 0), m.get("description", "")[:70]))
    return out

# the six pilot datasets: ground truth already verified, 150 columns, 17 positive
PILOT = ["koi", "diabetes", "lc", "compas", "ai4i", "titanic"]
# expansion datasets, evidenced in this session (newspecs.py).  Kept in a
# separate list so the original six stay byte-identical and every result
# computed on them remains comparable.
EXPANSION = ["bank", "support2", "bonemarrow", "heartfail"]
# Held out from all prompt development.  C6 and C7 were written before these
# existed in the benchmark and their failures have never been inspected, so
# they are the transfer test for the derivation clause.
TRANSFER = ["steel", "echo"]
# Datasets whose positives are named by the source itself rather than inferred
# from a description.  Kept as their own set, never merged into ALLSETS by
# default, so no existing table silently changes denominator when they arrive.
EXPLICIT = ["mi", "crime", "student"]
# Stratum C: tables this project did not choose.  Same reasoning as EXPLICIT
# and one step stronger -- these are not merged into ALLSETS or EXPLICIT under
# any flag, because every number already reported is scored against those two
# and a post-hoc addition must run BESIDE the frozen result, never inside it.
STRATC = ["cirrhosis", "klaverjas", "bikesharing"]
ALLSETS = PILOT + EXPANSION + TRANSFER
PREDICTION_POINT = {
    "KOI": "when the object is first vetted, before any disposition is assigned",
    "DIABETES": "at hospital discharge, before any readmission could occur",
    "LC": "at loan origination, before any repayment behaviour is observed",
    "COMPAS": "at the COMPAS screening date, before any subsequent arrest",
    "AI4I": "during operation, before any failure has occurred",
    "TITANIC": "at the moment of boarding",
}
TARGET = {"KOI": "koi_disposition", "DIABETES": "readmitted", "LC": "loan_status",
          "COMPAS": "two_year_recid", "AI4I": "Machine failure", "TITANIC": "survived"}


def scrub(text, keys):
    """Never let a key reach a log, a cache file, or a traceback."""
    out = str(text)
    for k in keys:
        if k:
            out = out.replace(k, "<REDACTED>")
    return out


# Set by main() from --reasoning.  Threaded through a module global rather than
# every signature because the alternative is editing six call sites for a knob
# that is per-run, never per-call.
REASONING = [None]
HTTP_TIMEOUT = [300]


def call(provider, model, system, user, key, max_tokens=4000, temperature=0.0):
    """POST via curl.

    urllib is rejected by Cloudflare at the Featherless edge (error 1010) on
    TLS/client fingerprint, before the key is evaluated. curl is a conventional
    HTTP client and is accepted. The key is passed through a header file rather
    than argv so it never appears in the process table.
    """
    url, _ = ENDPOINTS[provider]
    if provider == "anthropic":
        body = dict(model=model, max_tokens=max_tokens, temperature=temperature,
                    system=system, messages=[dict(role="user", content=user)])
        hdr = [f"x-api-key: {key}", "anthropic-version: 2023-06-01",
               "content-type: application/json"]
    else:
        body = dict(model=model, max_tokens=max_tokens, temperature=temperature,
                    messages=[dict(role="system", content=system),
                              dict(role="user", content=user)])
        # OpenAI-compatible reasoning knob.  Providers that do not implement it
        # ignore the field; the ones that do spend more tokens thinking before
        # they answer, which is the setting a frontier model should be judged at.
        if REASONING[0]:
            body["reasoning_effort"] = REASONING[0]
        hdr = [f"Authorization: Bearer {key}", "content-type: application/json"]

    with tempfile.NamedTemporaryFile("w", suffix=".hdr", delete=False) as hf:
        hf.write("\n".join(hdr) + "\n"); hpath = hf.name
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as bf:
        json.dump(body, bf); bpath = bf.name
    try:
        # 300s was tuned for non-reasoning models.  At reasoning_effort=high a
        # frontier model spends minutes thinking before it emits a token, and
        # every cell of the first run died with `curl exit 28` -- a timeout that
        # looks exactly like a model failure in the log and is not one.  The
        # ceiling has to be set by how long the model may legitimately take,
        # not by how long we expect it to.
        r = subprocess.run(["curl", "-sS", "--max-time", str(HTTP_TIMEOUT[0]),
                            "-H", f"@{hpath}", "-d", f"@{bpath}", url],
                           capture_output=True, text=True,
                           timeout=HTTP_TIMEOUT[0] + 30)
        if r.returncode != 0:
            raise RuntimeError(f"curl exit {r.returncode}: {r.stderr[:150]}")
        d = json.loads(r.stdout)
    finally:
        for p_ in (hpath, bpath):
            try: os.unlink(p_)
            except OSError: pass
    # Google returns errors wrapped in a top-level list: [{"error": {...}}].
    # Without this, `"error" in d` is False for a list and the real message is
    # masked by a TypeError on d["choices"], making every failure undiagnosable.
    if isinstance(d, list):
        d = d[0] if d else {}
    if not isinstance(d, dict):
        raise RuntimeError(f"unexpected response type {type(d).__name__}: {str(d)[:150]}")
    if "error" in d:
        raise RuntimeError(str(d["error"])[:200])
    if provider == "anthropic":
        return "".join(b.get("text", "") for b in d.get("content", []))
    ch = d.get("choices") or []
    if not ch:
        raise RuntimeError(f"no choices in response: {str(d)[:150]}")
    # a reasoning model that spends its whole budget thinking returns an empty
    # content string rather than an error; surface that instead of scoring it
    return (ch[0].get("message") or {}).get("content") or ""


# 503 / "high demand" / "overloaded" are transient and retryable on another key
# exactly like a 429; leaving them out made 7 Gemini cells fail on the first hit
# instead of rotating.
RATE = re.compile(r"rate.?limit|quota|429|RESOURCE_EXHAUSTED|at capacity"
                  r"|503|high demand|overloaded|UNAVAILABLE|try again"
                  r"|concurrency limit", re.I)

# curl's transport-level exit codes.  These say "the request never happened",
# not "the model answered badly", and they are almost always transient: a proxy
# blip took out 91 of 96 cells in one overnight phase with `curl exit 7`, each
# failing instantly because nothing in RATE matches it.  A cell lost to a
# network hiccup is indistinguishable in the log from a cell the model failed,
# which is the worse half of the problem.
#   7 connect failed   18 partial transfer   28 timeout   35 TLS handshake
#   52 empty reply     55/56 send/recv error
TRANSIENT = re.compile(r"curl exit (7|18|28|35|52|55|56)\b")


def call_rotating(provider, model, system, user, keys, cursor, max_tokens=4000):
    """Try each key in turn on a rate-limit or capacity error.

    `cursor` is a one-element list holding the next key index, so the rotation
    persists across calls and successive requests do not all pile onto key 0.
    Non-rate errors are raised immediately -- rotating through nine keys to
    collect the same 'model not found' nine times wastes time and tells us
    nothing.
    """
    last = None
    # With a single key `range(len(keys))` is range(1): one attempt and no
    # retry, so a transient "concurrency limit exceeded" killed the cell
    # outright.  Rotation and retry are different things and this loop has to
    # do both.
    for attempt in range(max(len(keys), 6)):
        k = keys[cursor[0] % len(keys)]
        cursor[0] += 1
        try:
            return call(provider, model, system, user, k, max_tokens=max_tokens)
        except Exception as e:
            last = e
            msg = str(e)
            if not (RATE.search(msg) or TRANSIENT.search(msg)):
                raise
            # transport failures deserve a longer, less eager backoff than a
            # rate limit: the network needs seconds to come back, not milliseconds
            time.sleep(min(2 ** attempt, 15) if RATE.search(msg)
                       else min(15 * (attempt + 1), 120))
    raise last


def parse(text):
    """Extract the JSON object, tolerating fences and stray prose."""
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r"\{.*\"columns\".*\}", t, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


try:
    DESCRIPTIONS = json.load(open(HERE + "descriptions.json"))
except Exception:
    DESCRIPTIONS = {}


def spec_bundle(key):
    # Every bundle passes through audit.apply() on the way out, so scoring,
    # downstream, baselines and the appendix cannot disagree about the ground
    # truth.  Correcting the truth in one scorer and not another is exactly how
    # the two strata ended up reading subtypes from different files (H13).
    import audit as AUDIT
    if key in EXPLICIT:
        import explicit_specs as ES
        return AUDIT.apply(ES.build(key))
    if key in STRATC:
        import stratc_specs as SC
        return AUDIT.apply(SC.build(key))
    if key in EXPANSION or key in TRANSFER:
        import newspecs as NS
        return AUDIT.apply(NS.build(key))
    s = H.LOADERS[key]()
    cols = s["clean"] + s["leaky"]
    leaky = set(s["leaky"])
    truth = {c: (c in leaky) for c in cols}
    # C3 and C5 read this.  It was hardcoded to "" until 2026-08-13, which made
    # C3 byte-identical to C2 -- a description condition carrying no
    # description.  Descriptions must come from the dataset's own documentation,
    # never written by us: a description we author could encode the answer, and
    # C3 would then measure whether our own hint helps (PROTOCOL 4).
    desc = DESCRIPTIONS.get(s["name"], "")
    sample = s["df"][cols].head(5).to_dict("records")
    return AUDIT.apply(dict(name=s["name"], columns=cols, truth=truth,
                            target=TARGET[s["name"]],
                            prediction_point=PREDICTION_POINT[s["name"]],
                            description=desc, sample=sample))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True, help="comma-separated model ids")
    ap.add_argument("--provider", default="featherless", choices=list(ENDPOINTS))
    ap.add_argument("--conditions", default="1")
    ap.add_argument("--repeats", type=int, default=1, help="shuffle seeds per cell")
    ap.add_argument("--datasets", default=",".join(PILOT))
    ap.add_argument("--all", action="store_true",
                    help="use all 10 evidenced datasets, not just the original 6")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list-models", action="store_true",
                    help="gemini only: ask the API which models exist")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--http-timeout", type=int, default=300,
                    help="seconds a single call may take; raise it for "
                         "reasoning models, which think before they emit")
    ap.add_argument("--reasoning", default=None,
                    choices=["minimal", "low", "medium", "high"],
                    help="OpenAI-compatible reasoning_effort; recorded in the "
                         "model label so cells run at different settings never "
                         "pool into one number")
    ap.add_argument("--workers", type=int, default=0,
                    help="concurrent calls; defaults to one per available key")
    ap.add_argument("--paraphrase", action="store_true",
                    help="memorisation control: run on string-distinct aliases")
    a = ap.parse_args()

    models = [m.strip() for m in a.models.split(",") if m.strip()]
    REASONING[0] = a.reasoning
    HTTP_TIMEOUT[0] = a.http_timeout
    conds = [int(c) for c in a.conditions.split(",")]
    dsets = ALLSETS if a.all else [d.strip() for d in a.datasets.split(",")]
    os.makedirs(CACHE, exist_ok=True)

    _, envvar = ENDPOINTS[a.provider]
    keys = keyring(a.provider)
    # scrub against every key of every provider, not just the one in use
    allkeys = list({k for p in ENDPOINTS for k in keyring(p)})
    if not keys and not a.dry_run:
        sys.exit(f"{envvar} is not set (nor {envvar}_1..9 / {envvar}S). "
                 f"export it; do not hard-code it.")
    if keys:
        print(f"{len(keys)} {a.provider} key(s) available, rotating on rate limits")
    cursor = [0]

    if a.list_models:
        for name, lim, desc in sorted(list_gemini_models(keys[0])):
            print(f"  {name:<44}{lim:>10,} ctx  {desc}")
        return

    bundles = {d: spec_bundle(d) for d in dsets}
    if a.paraphrase:
        import paraphrase as PP
        if PP.check() != 0:
            sys.exit("paraphrase map failed its own checks; refusing to run")
        bundles = {d: PP.apply_to(b) for d, b in bundles.items()}
    ncalls = len(models) * len(conds) * len(dsets) * a.repeats
    approx = sum(len(b["columns"]) for b in bundles.values()) * len(models) * len(conds) * a.repeats
    print(f"{ncalls} calls  |  {len(dsets)} datasets, {len(conds)} conditions, "
          f"{a.repeats} repeat(s), {len(models)} model(s)")
    print(f"~{approx} column-judgments; prompts ~{approx*6} tokens in total\n")
    if a.dry_run:
        for d, b in bundles.items():
            pos = sum(b["truth"].values())
            print(f"   {b['name']:<10}{len(b['columns']):>4} cols, {pos:>3} positive, "
                  f"target={b['target']}")
        return

    # ---- build the work list first, so it can be sharded across keys --------
    tasks = []
    for model in models:
        for d in dsets:
            b = bundles[d]
            for cond in conds:
                # C3 without a documented description is just C2 wearing a
                # different label.  Skip loudly rather than record a duplicate.
                if cond == 3 and not b["description"]:
                    print(f"  {'':36}{b['name']:<10}C3 SKIPPED -- no documented "
                          f"description, would be identical to C2", flush=True)
                    continue
                for rep in range(a.repeats):
                    seed = 1000 + rep
                    cols = b["columns"][:]
                    random.Random(seed).shuffle(cols)
                    if cond == 9:
                        user = prompts.build_derivation_v2(b["name"], cols, b["target"])
                        sysmsg = prompts.SYSTEM
                    elif cond == 7:
                        user = prompts.build_surrogate(b["name"], cols, b["target"])
                        sysmsg = prompts.SYSTEM
                    elif cond == 6:
                        user = prompts.build_derivation(b["name"], cols, b["target"])
                        sysmsg = prompts.SYSTEM
                    elif cond == 5:
                        user = prompts.build_expert(b["name"], cols, b["target"],
                                                    b["description"], None)
                        sysmsg = prompts.EXPERT_SYSTEM
                    else:
                        user = prompts.build(b["name"], cols, cond, b["target"],
                                             b["prediction_point"], b["description"],
                                             b["sample"])
                        sysmsg = prompts.SYSTEM
                    cid = hashlib.sha256(
                        f"{model}{a.reasoning or ''}|{b['name']}|{cond}|{seed}|"
                        f"{user}".encode()).hexdigest()[:20]
                    tasks.append(dict(model=model, b=b, cond=cond, seed=seed,
                                      user=user, sysmsg=sysmsg,
                                      cf=CACHE + cid + ".json"))

    # ---- execute, one worker per key ---------------------------------------
    # Quota is per key, so N keys means N concurrent calls without any single
    # key seeing a higher request rate than it would sequentially.  Each worker
    # owns one key rather than sharing a rotating cursor: a shared cursor under
    # threads would let several workers land on the same key at once, which is
    # exactly the rate spike this is meant to avoid.  Rotation still applies
    # within a worker as a fallback when its own key is exhausted.
    # Capping workers at the number of KEYS is right for Gemini, where quota is
    # per key, and for Featherless, where each key is an org with a 4-unit
    # concurrency limit and a big model costs all 4.  It is wrong for a host
    # that allows several concurrent calls on one key -- NVIDIA NIM does, and
    # the cap silently held that campaign at a single worker.  An explicit
    # --workers is now honoured; the key count is only the DEFAULT.
    nworkers = max(1, min(a.workers or len(keys), len(tasks) or 1))
    lock = threading.Lock()
    done = [0]

    # A cell prints one line only when it COMPLETES.  At reasoning=high a
    # 47-column dataset can exceed the 900s call ceiling and then retry, so a
    # perfectly healthy cell can be silent for the better part of an hour --
    # which is indistinguishable, from outside, from a wedged process.  The
    # supervising driver kills on silence, so silence has to mean something.
    # This makes "no output" a real signal instead of a normal state.
    def heartbeat():
        t0 = time.time()
        while not stop_beat.is_set():
            if stop_beat.wait(180):
                return
            with lock:
                n = done[0]
            print(f"  ... alive {int(time.time()-t0)//60}m, {n}/{len(tasks)} "
                  f"cells done, {nworkers} worker(s) in flight", flush=True)

    stop_beat = threading.Event()
    threading.Thread(target=heartbeat, daemon=True).start()

    def run_one(t, widx):
        if os.path.exists(t["cf"]):
            rec = json.load(open(t["cf"]))
        else:
            # this worker's own key first, then the others as fallback
            ordered = keys[widx:] + keys[:widx]
            try:
                txt = call_rotating(a.provider, t["model"], t["sysmsg"], t["user"],
                                    ordered, [0], a.max_tokens)
                status = "ok" if txt.strip() else "EMPTY"
            except Exception as e:
                txt = ""
                status = "ERROR " + scrub(e, allkeys)[:120]
            b = t["b"]
            rec = dict(model=t["model"] + (f"::{a.reasoning}" if a.reasoning else ""),
                       provider=a.provider,
                       dataset=b.get("orig_name", b["name"]),
                       shown_as=b["name"], paraphrase=bool(a.paraphrase),
                       alias=b.get("alias"),
                       condition=t["cond"], seed=t["seed"], status=status,
                       raw=txt, ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
            # Do NOT cache a failure.  A quota error or an empty completion is
            # a property of the moment, not of the (model, dataset, condition)
            # cell, but caching it makes the next run skip the cell and the
            # scorer then sees a permanent zero-coverage answer that the model
            # never actually gave.  This silently produced 17 such cells on the
            # explicit-source set after all nine Gemini keys hit their daily
            # quota; every one of them looked like a model failure.
            if rec["raw"].strip():
                tmp = t["cf"] + f".tmp{widx}"
                json.dump(rec, open(tmp, "w"), indent=1)
                os.replace(tmp, t["cf"])      # atomic: no half-written cache file
        b = t["b"]
        p = parse(rec["raw"]) if rec["raw"] else None
        got = {c["name"]: c.get("verdict") for c in (p or {}).get("columns", [])
               if isinstance(c, dict) and c.get("name")}
        cov = len(set(got) & set(b["columns"])) / len(b["columns"])
        with lock:
            done[0] += 1
            print(f"  [{done[0]:>3}/{len(tasks)}] {t['model'][:30]:<32}"
                  f"{b['name'][:26]:<28}C{t['cond']} s{t['seed']}  "
                  f"{'parsed' if p else 'PARSE FAIL':<11}cov={cov:5.1%}  "
                  f"{rec['status'][:40]}", flush=True)
        return dict(model=t["model"], dataset=b["name"], condition=t["cond"],
                    seed=t["seed"], parsed=bool(p), coverage=cov,
                    verdicts=got, truth=b["truth"], status=rec["status"])

    print(f"running {len(tasks)} task(s) on {nworkers} worker(s)\n", flush=True)
    results = []
    if nworkers == 1:
        for i, t in enumerate(tasks):
            results.append(run_one(t, 0))
    else:
        with cf.ThreadPoolExecutor(max_workers=nworkers) as ex:
            futs = {ex.submit(run_one, t, i % nworkers): t
                    for i, t in enumerate(tasks)}
            for fu in cf.as_completed(futs):
                results.append(fu.result())

    json.dump(results, open(HERE + "run_results.json", "w"), indent=1)
    print(f"\nwrote run_results.json ({len(results)} cells) -> score with score.py")


if __name__ == "__main__":
    main()
