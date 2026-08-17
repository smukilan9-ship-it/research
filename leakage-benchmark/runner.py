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
    # Vertex has no API key and no single URL: it authenticates with an ADC
    # bearer token and its endpoint is built per (project, region, publisher,
    # model).  The entry exists so `--provider vertex` is a legal choice and
    # so keyring() has something to look up and correctly find nothing; the
    # real endpoint construction lives in vertex.py.
    "vertex":      (None, "VERTEX_PROJECT"),
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
# Vertex thinking-token budget, set from --think-budget.  Module-global for the
# same reason REASONING is: it is per-run, never per-call.
THINK = [None]


def call(provider, model, system, user, key, max_tokens=4000, temperature=0.0):
    """POST via curl.

    urllib is rejected by Cloudflare at the Featherless edge (error 1010) on
    TLS/client fingerprint, before the key is evaluated. curl is a conventional
    HTTP client and is accepted. The key is passed through a header file rather
    than argv so it never appears in the process table.
    """
    # Vertex authenticates with an ADC bearer token rather than an API key, and
    # its two publishers take different body shapes, so it owns its own module.
    # Routed here rather than in run_one() so that every guarantee the rest of
    # this file makes -- the coverage gate, the join gate, never caching a
    # failure -- applies to Vertex cells unchanged.
    if provider == "vertex":
        import vertex as VX
        return VX.call(model, system, user, max_tokens=max_tokens,
                       think=THINK[0], timeout=HTTP_TIMEOUT[0])
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


_RESTORED = set()


def spec_bundle(key):
    # Every bundle passes through audit.apply() on the way out, so scoring,
    # downstream, baselines and the appendix cannot disagree about the ground
    # truth.  Correcting the truth in one scorer and not another is exactly how
    # the two strata ended up reading subtypes from different files (H13).
    import audit as AUDIT
    try:
        return _spec_bundle_upstream(key)
    except FileNotFoundError:
        # The upstream archive files are deliberately not committed
        # (MANIFEST.md), and UCI no longer serves several of them in their
        # original layout.  `datasets/` is the export of the resolved frames,
        # checked against NUMBERS.txt and a per-file SHA256 by
        # verify_datasets.py, so rebuilding from it is a restoration rather
        # than a substitution -- see datasets_bundle.py.
        #
        # Announced, not silent: a fallback that quietly produced a slightly
        # different bundle would make new cells non-comparable with the 1,812
        # already cached, and nothing downstream would say so.
        import datasets_bundle as DB
        name = key.upper()
        if not (DB.available() and name in DB.manifest()):
            raise
        b = AUDIT.apply(DB.build(name, want_sample=True))
        if name not in _RESTORED:
            _RESTORED.add(name)
            print(f"  [restored {name} from datasets/ — upstream file absent]",
                  flush=True)
        return b


def _spec_bundle_upstream(key):
    """The canonical path: the loaders that every number was computed by."""
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
    ap.add_argument("--think-budget", type=int, default=None,
                    help="vertex only: thinking-token budget as an INTEGER, "
                         "which is the point of using Vertex rather than a "
                         "vendor effort label. Forces temperature=1.0 for "
                         "Anthropic publishers -- see vertex.py.")
    a = ap.parse_args()

    models = [m.strip() for m in a.models.split(",") if m.strip()]
    REASONING[0] = a.reasoning
    HTTP_TIMEOUT[0] = a.http_timeout
    THINK[0] = a.think_budget
    conds = [int(c) for c in a.conditions.split(",")]
    dsets = ALLSETS if a.all else [d.strip() for d in a.datasets.split(",")]
    os.makedirs(CACHE, exist_ok=True)

    _, envvar = ENDPOINTS[a.provider]
    keys = keyring(a.provider)
    # scrub against every key of every provider, not just the one in use
    allkeys = list({k for p in ENDPOINTS for k in keyring(p)})
    if a.provider == "vertex":
        # ADC, not a key: there is nothing for keyring() to find and nothing to
        # scrub, because the bearer token is minted per run and never stored.
        # Fail here rather than 216 cells later if the environment is not set.
        if not a.dry_run:
            import vertex as VX
            if not VX.PROJECT:
                sys.exit("VERTEX_PROJECT is not set. Vertex needs a project id "
                         "and ADC:\n"
                         "  gcloud auth application-default login --no-launch-browser\n"
                         "  export VERTEX_PROJECT=<project-id>\n"
                         "  export VERTEX_REGION=us-central1   # optional")
            try:
                VX.token()
            except Exception as e:
                sys.exit(f"Vertex auth failed: {e}")
            print(f"vertex: project={VX.PROJECT} region={VX.REGION} "
                  f"think_budget={a.think_budget}")
            # Only warn about the temperature fork for models it applies to.
            # Printed unconditionally, it told a Gemini run that its
            # temperature had been forced to 1.0 when vertex.py had correctly
            # held it at 0.0 -- a scary, false claim about the very parameter
            # §8 says determines comparability.
            _anthropic = [m for m in models
                          if str(m).lower().startswith("claude")]
            if a.think_budget and _anthropic:
                print(f"  NOTE: a thinking budget forces temperature=1.0 for "
                      f"Anthropic publishers ({', '.join(_anthropic)}); every "
                      f"other API cell in the cache\n  is at 0.0. That is "
                      f"recorded in the model label so the two can never "
                      f"pool. See vertex.py.")
            elif a.think_budget:
                print("  temperature stays 0.0 (Google publishers take a "
                      "thinking budget and 0.0 together),\n  so these cells "
                      "stay comparable with the rest of the cache.")
                # A reasoning model spends minutes before emitting a token.
                # The 300s default was tuned for non-reasoning models, and
                # every cell of an earlier reasoning run died with `curl exit
                # 28` -- a timeout that looks exactly like a model failure and
                # is not one.  Worse here: a timeout is classified TRANSIENT
                # and retried up to six times, and a call that generated
                # tokens before we hung up is BILLED for them.  So a low
                # ceiling does not just lose cells, it pays six times to lose
                # each one.  Raise it rather than warn: nobody reads a warning
                # that scrolls past at cell 3 of 72.
                need = max(1800, (a.think_budget // 10) + 900)
                if HTTP_TIMEOUT[0] < need:
                    print(f"  RAISING --http-timeout {HTTP_TIMEOUT[0]}s -> "
                          f"{need}s: a {a.think_budget:,}-token thinking budget "
                          f"needs it, and a\n  timeout is retried up to six "
                          f"times with every attempt billed for what it "
                          f"generated.")
                    HTTP_TIMEOUT[0] = need
    elif not keys and not a.dry_run:
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
                    # The thinking budget joins the cache key for the same
                    # reason reasoning_effort does: a cell run at a different
                    # budget is a different cell, and letting the two collide
                    # would silently serve one run's answer for the other's.
                    cid = hashlib.sha256(
                        f"{model}{a.reasoning or ''}{a.think_budget or ''}|"
                        f"{b['name']}|{cond}|{seed}|"
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
            # The label carries the run regime, so cells parameterised
            # differently can never pool into one number.  For Vertex that is
            # the thinking budget and, when one is set, the temperature the
            # budget forces -- which is the whole reason the label is not just
            # the model id.
            if a.provider == "vertex":
                import vertex as VX
                # temperature is NOT passed: vertex.label derives it from the
                # same function body() uses, so the label cannot claim one
                # value while the request carries another.
                mlabel = VX.label(t["model"], a.think_budget)
            else:
                mlabel = t["model"] + (f"::{a.reasoning}" if a.reasoning else "")
            rec = dict(model=mlabel,
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
