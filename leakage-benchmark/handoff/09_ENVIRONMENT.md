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

Standard scientific stack: `pandas`, `numpy`, `scikit-learn`. Plus:

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

Before starting, confirm in the console:
- Claude Opus is **enabled in Model Garden** for the project (one-time
  click-through per model)
- the **exact publisher model ID** — do not guess a version string
- region (`us-central1` is the safe default)

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
