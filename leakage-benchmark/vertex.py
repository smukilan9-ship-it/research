"""Google Vertex AI as a provider: Anthropic and Gemini publisher models.

WHY THIS EXISTS

  `05_OPEN_WORK.md` item 1 is to replace the 216 hand-run frontier cells with
  API calls, and the funding constraint is GCP credit with **ADC only, no API
  keys**.  `runner.py` speaks to featherless, openai, anthropic, gemini and
  nvidia, all of which authenticate with a bearer key read from the
  environment.  None of them is Vertex, so until this file existed the credit
  could not buy a single cell.

  The handoff also records a reason to prefer Vertex over an Anthropic-direct
  key, and it is not the money:

      "On Vertex you pass an explicit thinking-token budget as an integer
       against a pinned publisher model ID, not a marketing effort label.
       That is a *better* answer to the 'vendor labels rather than versioned
       artefacts' complaint than an Anthropic-direct key would give."

  §6.1 currently concedes that the frontier effort settings are vendor labels
  that "can change under us without notice".  A pinned publisher model ID plus
  an integer budget is a versioned artefact.  That is the point of this file.

THE TEMPERATURE CONSTRAINT, WHICH IS LOAD-BEARING AND NOT A DETAIL

  Every API-served cell in `responses/` was run at `temperature = 0.0`.
  **Anthropic's extended thinking requires `temperature = 1.0`** -- the API
  rejects any other value when a thinking budget is enabled.  So the two cannot
  both hold, and the choice has to be made deliberately rather than discovered
  in a stack trace:

    THINK (default for Anthropic publishers)
        thinking budget set, temperature forced to 1.0.  Matches what the hand
        run was reaching for ("max effort") and replaces an unversioned vendor
        label with an integer.  NOT temperature-comparable with the open-weight
        replication tier -- but the frontier tier never was: §5.3 already says
        the tiers answer different questions and are not a capability ranking.

    COLD (`--no-thinking`)
        no thinking budget, temperature 0.0.  Parameter-identical to the rest
        of the API cells, at the cost of running a reasoning model with its
        reasoning off, which is not what any frontier row in the paper claims
        to measure.

  For **Gemini** publishers there is no such conflict: a thinking budget and
  `temperature = 0.0` coexist, so the Gemini arms keep 0.0 and stay comparable.
  That matters for the `gemini-3.5-flash` refill in particular, where §8 is
  explicit that a cell run at a different temperature is not comparable with
  the 1,800 it would be pooled against -- and where temperature zero is itself
  the trigger for the truncation in Appendix L.

  Whichever is used is recorded in the model label, so cells run under
  different regimes can never pool into one number.

DO NOT GUESS A MODEL ID

  `09_ENVIRONMENT.md`: "confirm the **exact publisher model ID** -- do not
  guess a version string."  A wrong-but-plausible ID either 404s (harmless) or
  silently resolves to a different snapshot (not harmless).  So this file
  ships no default model IDs.  Get them from Model Garden in the console, then
  verify before spending:

      python3 vertex.py --probe claude-sonnet-5,gemini-3-pro

  which sends a one-token request to each and reports which resolve.

  Claude IDs on Vertex are bare -- `claude-sonnet-5`, no `@date` suffix.

ACCESS IS NOT UNIFORM, AND THE DIFFERENCE SETS THE RUN ORDER

  **Claude is behind an Anthropic approval.**  Both `claude-opus-5` and
  `claude-sonnet-5` route their Model Garden *Enable* button to an enablement
  questionnaire; Google forwards it, plus the project number and billing
  account ID, to Anthropic, and access is granted on their decision,
  asynchronously.  `09_ENVIRONMENT.md` used to call this "a one-time
  click-through per model", which is wrong and is now corrected there.

  **Gemini is not gated.**  Google first-party models show no Enable button
  because nothing needs enabling once `aiplatform.googleapis.com` is on and
  billing is linked.  So the Gemini arms are runnable first, and they exercise
  everything here EXCEPT the Anthropic body shape -- `rawPredict`,
  `anthropic_version`, the `thinking` block, the temperature-1.0 forcing.
  Those are written from the spec and tested offline only, so run one cheap
  Claude cell on approval before committing to a full arm.

AUTH

  ADC first (`gcloud auth application-default print-access-token`), falling
  back to the CLI login, cached for 50 minutes (tokens last ~60).  No
  credential ever touches the process table or the cache -- the token is
  written to a curl `-K` header file exactly as the other providers' keys are.
"""
import json, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"

# Read from the environment so nothing about the account is committed.
PROJECT = (os.environ.get("VERTEX_PROJECT") or "").strip()
REGION = (os.environ.get("VERTEX_REGION") or "global").strip()

ANTHROPIC_VERTEX_VERSION = "vertex-2023-10-16"
_TOKEN = {"value": None, "at": 0.0}
TOKEN_TTL = 50 * 60

# Visible-output floor, in tokens, held BACK from the thinking budget.
#
# This number is not a guess and it is not conservative padding.  `rerun_
# truncated.py` records the corpus's own history: every campaign ran at
# max_tokens=4000, CRIME C6 on nemotron parsed **1 of 144 columns** after
# 67,868 characters of output, the first re-run raised it to 16,000 -- and
# 16,000 WAS STILL SHORT for CRIME.  That file settled on 32,000, with the
# comment "16,000 was never going to be enough for the widest dataset in the
# corpus."
#
# A thinking budget is spent BEFORE the first visible token, so a ceiling of
# `think + 4000` leaves exactly the budget that already failed here.  The cell
# would truncate, `runner.py` would cache it (it caches any non-empty
# completion), and it would be paid for at frontier rates and then silently
# depress recall.  That is the most expensive bug available in this file.
#
# Raising the ceiling is FREE: vendors bill emitted tokens, not the limit.
VISIBLE_FLOOR = 32000


# ------------------------------------------------------------------- auth
# The two gcloud logins are DIFFERENT credentials and this cost a debugging
# round: `gcloud auth login` authenticates the CLI, `gcloud auth
# application-default login` writes ADC, and each has its own token command.
# `09_ENVIRONMENT.md` specifies **ADC only**, so ADC is tried first; the CLI
# credential is a fallback rather than the default, and which one was used is
# reported, because "it authenticated" and "it authenticated as what you think"
# are different claims.
_TOKEN_CMDS = [
    (["gcloud", "auth", "application-default", "print-access-token"], "ADC"),
    (["gcloud", "auth", "print-access-token"], "gcloud CLI login"),
]


def token(force=False):
    """An access token, cached. Prefers ADC, falls back to the CLI login.

    Shelling out to gcloud rather than importing google-auth keeps the
    dependency list where `09_ENVIRONMENT.md` says it is -- pandas, numpy,
    scikit-learn, plus three named extras -- and makes the failure mode legible
    when ADC is not set up, which is the common case on a fresh machine.
    """
    now = time.time()
    if not force and _TOKEN["value"] and now - _TOKEN["at"] < TOKEN_TTL:
        return _TOKEN["value"]
    errs = []
    for cmd, what in _TOKEN_CMDS:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except FileNotFoundError:
            raise RuntimeError(
                "gcloud is not installed. Vertex uses ADC, not an API key:\n"
                "  brew install --cask google-cloud-sdk\n"
                "  gcloud auth application-default login\n"
                "  gcloud config set project <PROJECT_ID>")
        if r.returncode == 0 and r.stdout.strip():
            if _TOKEN.get("source") != what:
                print(f"    [vertex: authenticating with {what}]", flush=True)
            _TOKEN.update(value=r.stdout.strip(), at=now, source=what)
            return _TOKEN["value"]
        errs.append(f"{what}: {(r.stderr or '').strip()[:120]}")
    raise RuntimeError(
        "no usable credential. Tried both:\n    " + "\n    ".join(errs)
        + "\n  Fix with:\n"
        "    gcloud auth application-default login\n"
        "    gcloud auth application-default set-quota-project <PROJECT_ID>")


def _require_project():
    if not PROJECT:
        raise RuntimeError(
            "VERTEX_PROJECT is not set. export it (or put it in your shell "
            "profile); it is an account identifier, not a secret, but it is "
            "read from the environment so nothing about the account is "
            "committed.")


# ------------------------------------------------------------- endpoints
def publisher_of(model):
    """Which publisher serves this model, from the ID itself.

    Deliberately conservative: anything not recognised raises rather than
    defaulting, because a mis-routed request builds the WRONG BODY SHAPE and
    the error it returns is about JSON rather than about routing.
    """
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith("gemini"):
        return "google"
    if m.startswith("grok"):
        return "xai"
    raise RuntimeError(
        f"cannot route {model!r}: expected a publisher model ID beginning "
        f"'claude', 'gemini' or 'grok'. Pass the exact ID from Model Garden.")


def url(model, stream=False):
    _require_project()
    pub = publisher_of(model)
    host = ("aiplatform.googleapis.com" if REGION == "global"
            else f"{REGION}-aiplatform.googleapis.com")
    # Three publishers, three surfaces, and they are genuinely different.
    #
    #   anthropic  rawPredict on the publisher path, Anthropic's own body
    #   google     generateContent on the publisher path, Gemini's own body
    #   xai        the OPENAI-COMPATIBLE endpoint -- NOT the publisher path.
    #
    # xAI is "OpenMaaS", and a rawPredict against it returns
    # `400 FAILED_PRECONDITION: OpenMaaS model is not allowed to be called
    # from this method.`  Those models are served from
    # `endpoints/openapi/chat/completions`, where the model is named in the
    # BODY as a fully-qualified publisher path rather than in the URL.
    if pub == "xai":
        # /v1/, not /v1beta1/ -- this is the path Model Garden's own Grok
        # quick-start prints.  v1beta1 also answers, which is how it went
        # unnoticed: it returned 200s under hand testing and length-stops
        # under the runner, so the wrong version looked like a flaky model.
        return (f"https://{host}/v1/projects/{PROJECT}"
                f"/locations/{REGION}/endpoints/openapi/chat/completions")
    verb = ("rawPredict" if pub == "anthropic"
            else ("streamGenerateContent" if stream else "generateContent"))
    return (f"https://{host}/v1/projects/{PROJECT}/locations/{REGION}"
            f"/publishers/{pub}/models/{model}:{verb}")


# ------------------------------------------------------------------ body
def effective_temperature(model, think=None, temperature=None):
    """The temperature a request will ACTUALLY carry.

    Both `body()` and `label()` call this, and that is the point. The first
    version let the caller pass the temperature it assumed into the label while
    `body()` computed a different one -- so a Gemini cell with a thinking budget
    was labelled `t1.0` and sent `0.0`. A label that disagrees with the artefact
    it describes is the exact defect this project exists to catch, and the fix
    is not to be careful twice: it is to derive both from one function.
    """
    if publisher_of(model) == "anthropic" and think:
        return 1.0          # the API rejects anything else with thinking on
    return 0.0 if temperature is None else temperature


def body(model, system, user, max_tokens=16000, think=None, temperature=None):
    """Request body for one cell.

    `think` is an integer thinking-token budget, or None for no thinking.
    `temperature` of None means "whatever this regime requires", which is the
    only safe default: silently sending 0.0 alongside a thinking budget gets a
    400 from Anthropic, and silently sending 1.0 without one would break
    comparability with every other cell in the cache.
    """
    pub = publisher_of(model)
    if pub == "anthropic":
        if think and temperature not in (None, 1.0):
            raise RuntimeError(
                f"temperature={temperature} was requested with a thinking "
                f"budget of {think}. Anthropic extended thinking requires "
                f"temperature=1.0; the two cannot both hold. Either drop "
                f"--think-budget (and keep 0.0, comparable with the rest "
                f"of the cache) or accept 1.0 and record it in the label.")
        temp = effective_temperature(model, think, temperature)
        b = {
            "anthropic_version": ANTHROPIC_VERTEX_VERSION,
            "max_tokens": max_tokens,
            "temperature": temp,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if think:
            # The budget is spent before the first visible token, so the
            # ceiling has to clear it AND still leave a full answer's worth.
            # See VISIBLE_FLOOR: 4,000 is the budget that already truncated
            # CRIME to 1 of 144 columns on this corpus.
            b["max_tokens"] = max(max_tokens, int(think) + VISIBLE_FLOOR)
            b["thinking"] = {"type": "enabled", "budget_tokens": int(think)}
        return b

    if pub == "xai":
        # Grok on Vertex is a MaaS passthrough of xAI's own API, which is
        # OpenAI-compatible: system and user are MESSAGES, not separate fields.
        #
        # Reasoning is a PROPERTY OF THE MODEL ID here, not a request
        # parameter -- xAI ships `grok-4.20-reasoning` and
        # `grok-4.20-non-reasoning` as separate publisher models.  So a
        # thinking budget is meaningless and is deliberately NOT sent: passing
        # one would either 400 or, worse, be silently ignored while the label
        # claimed a budget the request never carried.  That matched pair is
        # exactly why these models are worth running -- it varies inference
        # -time reasoning while holding training data and architecture fixed,
        # which no other comparison in this benchmark can do.
        #
        # temperature 0.0, like every other API cell in the cache.
        return {
            # The openapi endpoint wants `<publisher>/<model>` here -- not the
            # bare id (the URL carries no model name) and NOT the full resource
            # path, which returns:
            #   "Malformed publisher model ... expected '<publisher>/<model>'"
            "model": f"xai/{model}",
            "temperature": effective_temperature(model, None, temperature),
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }

    # google / Gemini: thinking and temperature 0.0 coexist, so 0.0 is kept.
    # Gemini counts thinking tokens against maxOutputTokens too, so the same
    # floor applies -- the widest datasets truncate here for the same reason.
    gen = {
        "temperature": effective_temperature(model, think, temperature),
        "maxOutputTokens": (max(max_tokens, int(think) + VISIBLE_FLOOR)
                            if think else max_tokens),
    }
    if think is not None:
        gen["thinkingConfig"] = {"thinkingBudget": int(think)}
    return {
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": gen,
    }


def truncated(model, payload):
    """Did the vendor say it stopped because it ran out of room?

    Both publishers report this and nothing in the pipeline was reading it.
    Coverage is an INFERENCE about truncation -- a model that legitimately
    omits columns looks identical to one that was cut off -- whereas
    `stop_reason` / `finishReason` is the vendor stating it outright.

    This is worth having because `runner.py` caches any non-empty completion:
    a truncated cell is paid for, stored, and then silently depresses recall
    until `verify_paper.py` §17 finds it, which is weeks and one bill later.
    Appendix L is the write-up of exactly that going undiagnosed.
    """
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    if not isinstance(payload, dict):
        return False
    if publisher_of(model) == "xai":
        ch = payload.get("choices") or []
        return bool(ch) and ch[0].get("finish_reason") == "length"
    if publisher_of(model) == "anthropic":
        return payload.get("stop_reason") == "max_tokens"
    cands = payload.get("candidates") or []
    return bool(cands) and cands[0].get("finishReason") == "MAX_TOKENS"


def extract(model, payload):
    """Visible text from a Vertex response, or a raised error.

    Both publishers can return a well-formed response containing no text -- a
    reasoning model that spends its whole budget thinking, or a safety block.
    Returning "" for those is right: `runner.py` refuses to cache an empty
    completion, so the cell is retried rather than becoming a permanent
    zero-coverage answer the model never gave.
    """
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected response type "
                           f"{type(payload).__name__}: {str(payload)[:150]}")
    if "error" in payload:
        raise RuntimeError(str(payload["error"])[:300])
    if publisher_of(model) == "xai":
        ch = payload.get("choices") or []
        if not ch:
            raise RuntimeError(f"no choices in response: {str(payload)[:200]}")
        return (ch[0].get("message") or {}).get("content") or ""
    if publisher_of(model) == "anthropic":
        # thinking blocks carry type "thinking" and are NOT part of the answer
        return "".join(b.get("text", "") for b in payload.get("content", [])
                       if b.get("type") in (None, "text"))
    cands = payload.get("candidates") or []
    if not cands:
        raise RuntimeError(f"no candidates in response: {str(payload)[:200]}")
    parts = (cands[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if "text" in p)


# ------------------------------------------------------------------ call
def call(model, system, user, max_tokens=16000, think=None, temperature=None,
         timeout=900):
    """One cell against Vertex. Raises on transport or API error."""
    tok = token()
    payload = body(model, system, user, max_tokens, think, temperature)
    with tempfile.NamedTemporaryFile("w", suffix=".hdr", delete=False) as hf:
        # `x-goog-user-project` is REQUIRED with user-type ADC, and its absence
        # is a 403 that reads like a permissions problem rather than a missing
        # header: "requires a quota project, which is not set by default".
        # `gcloud auth application-default set-quota-project` writes the id
        # into the ADC file, but nothing forwards it when the token is used as
        # a raw bearer -- the client libraries add this header and curl does
        # not.  Found by a free listing call, before any billable one.
        hf.write(f"Authorization: Bearer {tok}\n"
                 f"content-type: application/json\n"
                 f"x-goog-user-project: {PROJECT}\n")
        hpath = hf.name
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as bf:
        json.dump(payload, bf)
        bpath = bf.name
    try:
        r = subprocess.run(
            ["curl", "-sS", "--max-time", str(timeout),
             "-H", f"@{hpath}", "-d", f"@{bpath}", url(model)],
            capture_output=True, text=True, timeout=timeout + 30)
        if r.returncode != 0:
            raise RuntimeError(f"curl exit {r.returncode}: {r.stderr[:150]}")
        try:
            d = json.loads(r.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"non-JSON response: {r.stdout[:200]}")
    finally:
        for p in (hpath, bpath):
            try:
                os.unlink(p)
            except OSError:
                pass
    if truncated(model, d):
        # RAISE, do not return.  `runner.py` caches any non-empty completion,
        # so returning a truncated body would store a cell with a fraction of
        # its columns answered -- paid for, and then silently depressing recall
        # until §17 finds it.  A raised call is never cached and is retried.
        #
        # Retrying is the right response because the fault is INTERMITTENT,
        # which this run demonstrated: cells reported MAX_TOKENS after ~1,500
        # visible tokens against a 48,000 ceiling, and the identical prompt
        # then completed normally at 5,627 total tokens.  That is Appendix L's
        # phenomenon -- "intermittently returns finish_reason='length' after a
        # few hundred visible tokens whatever max_tokens is" -- reproducing
        # here on VERTEX and on `gemini-3.1-pro-preview`, so it is neither
        # AI-Studio-specific nor `gemini-3.5-flash`-specific. Appendix L is
        # currently narrower than the truth.
        #
        # The word "truncated" is what runner.TRANSIENT matches on, so the
        # retry happens in-run rather than being deferred to a later pass.
        u = d.get("usageMetadata") or {}
        got = u.get("candidatesTokenCount", "?")
        thoughts = u.get("thoughtsTokenCount", "?")
        raise RuntimeError(
            f"truncated: {model} reported a length stop after "
            f"{got} visible tokens (thoughts {thoughts}); not cached, retrying")
    return extract(model, d)


def label(model, think=None, temperature=None):
    """The cache label for a Vertex cell.

    The regime is IN THE LABEL, not in a note somewhere, because cells run
    under different parameters must never pool into one number -- the same
    reason `runner.py` appends `::{reasoning}` for the OpenAI-compatible
    providers.  A reader of `NUMBERS.txt` can tell a hand-run
    `claude-opus-5-max` row from an API `claude-opus-5@...::vertex-think16000`
    row without opening the cache.

    The temperature written here is the one `body()` will actually send, taken
    from the same function, so the two cannot drift apart.
    """
    bits = ["vertex"]
    if think:
        bits.append(f"think{int(think)}")
    bits.append(f"t{effective_temperature(model, think, temperature)}")
    return model + "::" + "-".join(bits)


# ------------------------------------------------------------------ probe
def probe(ids, think=None):
    """Send a minimal request to each candidate ID and report what resolves.

    This exists because `09_ENVIRONMENT.md` forbids guessing a version string
    and because the two failure modes look nothing alike: a wrong ID 404s,
    while a model that is not click-through-enabled in Model Garden returns a
    permission error naming the model.  Both are cheap to discover and
    expensive to discover late.
    """
    print("=" * 78)
    print(f"VERTEX PROBE — project={PROJECT or '(VERTEX_PROJECT unset)'} "
          f"region={REGION}")
    print("=" * 78)
    ok = []
    for mid in ids:
        mid = mid.strip()
        if not mid:
            continue
        try:
            # 64 was too tight: a reasoning model spends that before emitting
            # a visible token, so the probe's own ceiling tripped the
            # truncation guard and reported a working model as FAILED.
            txt = call(mid, "Reply with the single word: ok.", "ok?",
                       max_tokens=(think + 2048) if think else 2048, think=think,
                       timeout=180)
            got = (txt or "").strip().replace("\n", " ")[:40]
            print(f"  RESOLVES  {mid:<44} -> {got!r}")
            print(f"            label would be: {label(mid, think)}")
            ok.append(mid)
        except Exception as e:
            msg = str(e).replace("\n", " ")[:150]
            print(f"  FAILED    {mid:<44} {msg}")
    print(f"\n  {len(ok)} of {len(ids)} resolved.")
    if not ok:
        print("  Nothing resolved. Check, in this order:")
        print("    1. gcloud auth application-default login --no-launch-browser")
        print("    2. export VERTEX_PROJECT=<project-id>")
        print("    3. the model is ENABLED in Model Garden (one click-through")
        print("       per model, per project)")
        print("    4. the ID is copied from the console, not typed from memory")
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="Probe Vertex publisher model IDs before spending on them.")
    ap.add_argument("--probe", required=True,
                    help="comma-separated publisher model IDs, copied from "
                         "Model Garden")
    ap.add_argument("--think-budget", type=int, default=None,
                    help="thinking-token budget; forces temperature=1.0 for "
                         "Anthropic publishers")
    a = ap.parse_args()
    sys.exit(probe(a.probe.split(","), a.think_budget))
