# Environment — what a fresh machine needs

## Getting to a working state

```bash
git clone https://github.com/smukilan9-ship-it/research
cd research/leakage-benchmark
./restore_caches.sh          # ungzip the four sweep caches
python3 missing_data.py      # see which raw CSVs are absent
python3 verify_datasets.py   # the 15 corpus tables are committed in datasets/
```

Then the one-minute state check in `00_START_HERE.md`. The five checkers need
**no raw data and no network**.

## Python

Pinned in `requirements.txt` — CPython **3.14.0**, numpy 2.4.6, pandas 3.0.3,
scikit-learn 1.9.0, scipy 1.18.0:

```bash
python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

The pin is load-bearing for **§20 only**, the one section that fits a model
live, and it is not cosmetic: scikit-learn 1.8 puts NHANES leak-removed F1 at
0.1848 where 1.9 puts it at 0.4037, and under pandas 2.x NHANES and CKD come
out `nan` and do not compute at all. `verify_paper.py` prints the live versions
into §10 on every run, so a mismatched stack shows up in a diff instead of
silently moving a published number. Sections 1–19 and 21–24 read frozen CSVs
and reproduce on any current stack.

Also used, and not version-sensitive:

- `tiktoken` — `api_cost.py` (falls back to 4 chars/token if absent)
- `markdown` + `playwright` — `pagecount.py` only
- `tabmemcheck` (Bordt et al., COLM 2024) — the memorisation control

`pagecount.py` pins a Chromium build path. On a local machine with a normal
Playwright install, drop the `executable_path` override or point it at your own
browser; the version pinning was a remote-container workaround.

## Credentials — handling rules

Every provider key lives in a `0600` file, `.gitignore`d, and is passed to
`curl` through a `-K` header file **so it never appears in the process table**.

| file | provider |
|---|---|
| `feather.env` | featherless |
| `nvidia.env` | NVIDIA NIM |
| `gemini.env` / `gemini.curl` | Google AI Studio |
| `kaggle.token` / `kaggle.curl` | Kaggle |

None are in the repository and none belong there.

> **Rotate the three Google AI Studio keys used in the remote session.** They
> were pasted into a chat transcript. This is outstanding.

## Google Cloud / Vertex — for the work in `05_OPEN_WORK.md`

Constraint: **ADC only, no API keys.**

```bash
gcloud auth application-default login --no-launch-browser
```

Produces `~/.config/gcloud/application_default_credentials.json`, which holds a
refresh token — treat it exactly like a key. Revoke with
`gcloud auth application-default revoke`.

`.gitignore` already covers `application_default_credentials.json` and
`service-account*.json`.

Two logins, and they are different credentials:

```bash
gcloud auth login                        # the CLI
gcloud auth application-default login    # ADC — this is the one the code wants
gcloud auth application-default set-quota-project <PROJECT_ID>
```

`vertex.py` prefers ADC and falls back to the CLI credential, reporting which
it used. An earlier version called `gcloud auth print-access-token` only, which
reads the **CLI** login — so a machine set up per this document's own
instruction (ADC) would have failed to authenticate.

Before starting, confirm in the console:

- **Claude access is an APPROVAL, not a click-through.** This document
  previously said "one-time click-through per model" and that is wrong. Both
  `claude-opus-5` and `claude-sonnet-5` route their Model Garden *Enable*
  button to an **Anthropic enablement questionnaire** — business name, website,
  contact, headquarters, industry, intended users, intended use cases, and an
  Acceptable-Use-Policy declaration. Google forwards the form, the project
  number and the billing account ID to Anthropic, and access is granted on
  **their** approval. It is asynchronous and cannot be scheduled. The request
  looks project-level rather than per-model, so one approval should unlock
  both — confirm rather than assume.
- **Gemini models are not gated this way.** They are Google first-party and
  show no Enable button, because nothing needs enabling once
  `aiplatform.googleapis.com` is on and billing is linked. The absence of the
  button is the signal, not a missing step.
- the **exact publisher model ID** — do not guess a version string. Claude IDs
  on Vertex are bare (`claude-sonnet-5`), with no `@date` suffix.
- **region: `global`.** Vertex's own Claude quick-start uses `region="global"`,
  which resolves to `aiplatform.googleapis.com` rather than a `<region>-`
  prefixed host. `us-central1` was recorded here as "the safe default"; it is
  not the documented one.

Verified from the remote container: Vertex endpoints are reachable
(`server: ESF` through the proxy). `gcloud` was **not** preinstalled there.

## Remote-container notes, if you go back to one

- Egress is via an agent proxy. **Never** disable TLS verification or unset
  `HTTPS_PROXY`; if a tool fails, read `/root/.ccr/README.md` and check
  `curl -sS "$HTTPS_PROXY/__agentproxy/status"`.
- arxiv, Cell and ScienceDirect are blocked — this is why the K&N verbatim quote
  for §3.2 is still outstanding and is trivial locally.
- **Containers are ephemeral.** Everything not committed is lost when the session
  is reclaimed. This repository exists because of that.

## Repository layout note

Scripts resolve paths relative to **their own file**, not the working directory,
so the flat layout inside `leakage-benchmark/` is load-bearing. Run them from
that directory. Moving files into tidy subfolders will break every loader.

## Long-running jobs

`verify_paper.py` refits forests, a cluster bootstrap and a perturbation
analysis on every run — minutes, deliberately. A cached result is a result
nobody re-derived. `watchdog.sh` and `guard.py` exist from the overnight sweeps
and are not needed for ordinary work.
