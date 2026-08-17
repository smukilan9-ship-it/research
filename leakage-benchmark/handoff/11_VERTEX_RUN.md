# The Vertex run — setup, grid, cost, and what it moves in the paper

Covers `05_OPEN_WORK.md` items 1 and 3, plus a roster extension decided after
that document was written: **`claude-sonnet-5` and Gemini Pro join the roster as
full members.**

Everything here needs credentials this repository does not and must not contain.
`vertex.py` is written and tested offline; nothing has been spent.

---

## 1. What has to be true before a single cell runs

```bash
# once per machine
brew install --cask google-cloud-sdk
gcloud auth login                                          # the CLI
gcloud auth application-default login                      # ADC — what the code wants
gcloud config set project <PROJECT_ID>
gcloud auth application-default set-quota-project <PROJECT_ID>
gcloud services enable aiplatform.googleapis.com

export VERTEX_PROJECT=<project-id>
export VERTEX_REGION=global             # Vertex's own Claude quick-start uses this
```

**Two logins, two credentials.** `gcloud auth login` authenticates the CLI;
`gcloud auth application-default login` writes ADC, which is what
`09_ENVIRONMENT.md` specifies. `vertex.py` prefers ADC and falls back to the
CLI credential, printing which it used.

`gcloud` is **not** preinstalled — install the SDK first. The ADC file it
writes (`~/.config/gcloud/application_default_credentials.json`) holds a refresh
token: **treat it exactly like an API key.** It is already `.gitignore`d.
Revoke with `gcloud auth application-default revoke`.

Then, in the console:

**Claude is behind an Anthropic approval, not a click-through.** Both
`claude-opus-5` and `claude-sonnet-5` route their Model Garden *Enable* button
to an enablement questionnaire — business name, website, contact, headquarters,
industry, intended users, intended use cases, Acceptable-Use-Policy
declaration. Google forwards it, plus the project number and billing account
ID, to Anthropic; access is granted on **their** approval, asynchronously.

Answer it as what the project is: an individual running an academic benchmark.
The repository URL is a truthful "business website" and shows the use case
directly. A misrepresented application is worse than a delayed one.

**Gemini is not gated.** Google first-party models show no Enable button
because nothing needs enabling once `aiplatform.googleapis.com` is on and
billing is linked. The missing button is the signal, not a missing step.

**This reorders the run.** The Gemini arms — Gemini Pro, and the
`gemini-3.5-flash` refill — are runnable as soon as ADC works, and they prove
auth, URL construction, the `global` region path, the thinking budget, the
token ceiling, parsing, caching and the runner integration. They do **not**
prove the Anthropic body shape (`rawPredict`, `anthropic_version`, the
`thinking` block, the temperature-1.0 forcing), which is written from the spec
and tested only offline. So when approval lands, run **one** cheap Claude cell
before the full arm rather than treating a green Gemini run as coverage.

Also confirm:

- the **exact publisher model ID**. Claude IDs on Vertex are bare —
  `claude-sonnet-5`, no `@date` suffix.

## 2. Do not guess a model ID — probe it

`09_ENVIRONMENT.md` says it and it is worth repeating: a wrong-but-plausible ID
either 404s, which is harmless, or resolves to a **different snapshot**, which
is not. Copy the IDs from the console, then:

```bash
python3 vertex.py --probe <opus-id>,<sonnet-id>,<gemini-pro-id> --think-budget 16000
```

Each gets a one-token request. The output names what resolved, what the cache
label will be, and — if nothing resolves — which of the four usual causes to
check. **Do not proceed until every ID you intend to spend on resolves.**

## 3. The temperature fork, which is a real methodological choice

Every API-served cell in `responses/` runs at **`temperature = 0.0`**.
**Anthropic extended thinking requires `temperature = 1.0`** — the API rejects
anything else with a thinking budget enabled. Both cannot hold.

| | regime | comparability |
|---|---|---|
| **Anthropic + `--think-budget`** *(default, recommended)* | thinking budget as an integer, temperature forced to 1.0 | not temperature-comparable with the open-weight tier — but the frontier tier never was. §5.3 already states the tiers answer different questions and are not a capability ranking, and §6.1 concedes the current effort settings are *vendor labels rather than versioned artefacts*. An integer budget against a pinned publisher ID is strictly better documented than what it replaces. |
| **Anthropic, no `--think-budget`** | temperature 0.0, no thinking | parameter-identical to the rest of the cache, at the cost of running a reasoning model with its reasoning off — which is not what any frontier row in the paper claims to measure. |
| **Gemini, either way** | thinking budget and `temperature = 0.0` coexist | no fork. Gemini arms keep 0.0 and stay comparable. |

The regime is written into the **model label**
(`<id>::vertex-think16000-t1.0`), derived from the same function that builds the
request body, so a label can never claim a temperature the request did not
carry. Cells under different regimes cannot pool into one number.

**This matters most for the `gemini-3.5-flash` refill.** §8 is explicit that a
cell run at a different temperature is not comparable with the 1,800 it pools
against — and temperature zero is itself the trigger for the truncation in
Appendix L. So the refill runs at **0.0, unchanged**, which means it is
attempting the call that fails for a reason more quota does not fix. Expect
partial success at best; that is the honest expectation, not pessimism.

## 4. The grid, taken from the cache rather than assumed

The hand-run frontier models hold **72 real-name cells each**, and the shape is
not what "C1/C2/C6/C9 across 15 datasets" would suggest:

| | conditions | seeds | cells |
|---|---|---|---|
| Stratum A (12 datasets) | **C1, C6, C9** — no C2 | 1 | 36 |
| Stratum B (3 datasets) | C1, C2, C6, C9 | 3 | 36 |
| | | | **72** |

Plus a **36-cell paraphrase arm** (§6.3d), giving the 108 cells `api_cost.py`
prices.

> **C2 was never run on Stratum A for the frontier tier.** Worth knowing before
> you read the ladder table. Running it for the new models would fill a gap the
> incumbents have — but it also means the new rows carry coverage the old ones
> lack. `verify_paper.py` matches on cells present in both arms, so nothing
> breaks; the `ds`/`sd` columns simply differ. Mirror the existing grid unless
> you want that gap filled deliberately.

**Run the paraphrase arm too, for any model that needs one.** §6.3(d)'s
decrement is a within-model comparison of real names against aliases. If Vertex
supplies the real-name arm and the hand run supplied the aliased arm, that
comparison is between two different provenances and means nothing.

## 5. Commands

```bash
# 1. opus — replaces the hand-run cells (OPEN_WORK item 1)
python3 runner.py --provider vertex --models <opus-id> --think-budget 16000 \
    --conditions 1,6,9 --datasets ai4i,bank,bonemarrow,compas,diabetes,echo,heartfail,koi,lc,steel,support2,titanic \
    --repeats 1 --max-tokens 20000 --http-timeout 900 --dry-run

python3 runner.py --provider vertex --models <opus-id> --think-budget 16000 \
    --conditions 1,2,6,9 --datasets crime,mi,student \
    --repeats 3 --max-tokens 20000 --http-timeout 900 --dry-run
```

Drop `--dry-run` when the counts look right. Repeat for `<sonnet-id>` and
`<gemini-pro-id>`. Add `--paraphrase` for the memorisation arm.

`--max-tokens` must exceed the thinking budget — the budget is spent before the
first visible token, so a ceiling below it guarantees an empty completion that
looks exactly like a model failure. `vertex.py` raises the ceiling for you, but
set it deliberately.

The runner's existing guarantees apply unchanged: **failures are never cached**,
cells under 90% coverage are discarded and retried, and a cell whose verdict
keys miss the truth keys is refused rather than scored.

## 6. Cost

Measured from the cache by `api_cost.py`, not estimated: each 108-cell model arm
is **~42k input and ~232k visible output tokens**, and reasoning tokens — which
neither vendor emits into the transcript and both bill for — are entered as an
explicit **3×–8×** multiplier rather than hidden in a point estimate.

| model | 108 cells |
|---|---|
| `claude-opus-5` | **$17.61 – 46.61** (measured) |
| `claude-sonnet-5` | cheaper per output token than opus — **confirm current list price** |
| Gemini Pro | cheaper again — **confirm current list price** |
| `gemini-3.5-flash` refill | 7 cells, negligible |

`api_cost.py` holds prices in a single `PRICES` dict: add the two new models
there with prices confirmed against current vendor pricing, then re-run it.
**Do not take the two figures above on trust** — they are the shape of the bill,
not a quote.

Against ~₹28,000 (~$320) of credit this is comfortable. Budget **$150** for
retries and parse failures, per `05_OPEN_WORK.md`.

## 7. What this moves in the paper — read before spending

Adding two models to `MODELS` in `verify_paper.py` changes every
**mean-over-models** statistic. This is the system working, not a problem, but
it is work and it lands after the cells do:

- **§24 complete rosters: n = 9 → 11**; the frontier tier goes **n = 4 → 6**
- the abstract's **96% TIMING / 85% CONSEQUENCE / 62% REASON**, and the **88%**
  lift, all move
- **"Seven of nine"** models scoring REASON below their own CONSEQUENCE
- **"Nine of ten"** exceeding the baseline at C6, **"eight of ten"** at C1
- both **tier means** (+0.063 replication / +0.040 frontier), and the
  **+0.100** figure that excludes the one negative model
- §6.5's forest plot and the claim that *every interval excluding zero belongs
  to a model scoring under 0.66 at C1* — two new frontier models are a genuine
  test of that, not decoration

**Several `prose_pins` will fail until the prose is updated.** That is the
checker doing its job. The order is: cells land → `verify_paper.py > NUMBERS.txt`
→ read the diff → update prose → re-run all six checkers on **both**
manuscripts.

**Snapshot `NUMBERS.txt` before any operation that moves cache files**, and diff
after. `07_MISTAKES.md` records why: a filename collision once overwrote a
complete cell with its truncated original, and only a pre-run snapshot caught it.

## 8. The opus question the numbers may force

`05_OPEN_WORK.md` already settled this and it is restated because it is about to
become concrete: **if the API run returns different numbers, the paper reports
the API run.** Reproducible beats flattering. The exact 84/0/0 Stratum B result
was a hand run on a given day.

The hand-run cells are **not deleted** — they carry a distinct label
(`claude-opus-5-max`) from the Vertex cells, so both survive in the cache and
`verify_paper.py` can report both. That turns §6.1's disclosed weakness into a
measurable one: same prompts, same seeds, hand-run against API, and the delta is
a number rather than a promise. Decide whether to report it that way once the
delta is known; keeping both labels preserves the option, and collapsing them
later is a one-line change while un-collapsing is not.
