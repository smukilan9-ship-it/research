# Mistakes made building this, and what each one cost

Kept because several of them are still live hazards, and because the pattern
across them is the paper's own thesis: *a plausible claim that nobody checked
against the artefact.*

## Data destruction — the worst one

**The response cache was damaged.** Moving files between `responses/` and
`responses_truncated/` caused a filename collision that **overwrote LC C1 s1001's
complete version with its truncated original**. Detected only by diffing against
a pre-run `NUMBERS.txt` snapshot; restored file-by-file, then the destroyed cell
was re-fetched.

**Standing rule from this**: snapshot `NUMBERS.txt` before any operation that
moves cache files, and diff after. `responses/` is irreplaceable — 216 of its
cells cannot be re-fetched at any price.

## Errors invisible to every checker at the time

**`8 of 64` IS `12.5%`.** The paper said "8 of 64 positives (12.5%)" while the
corpus had moved to 8 of 56. Internally perfect, externally wrong, and passed
clean by three checkers. → created `prose_pins.py`.

**The abstract credited C6's 0.918 to C1.** Both numbers are real, both appear
in `NUMBERS.txt`, and no arithmetic relation was stated between them. Best C1 is
0.905. → pinned.

**A dangling `[N §22]`.** `NUMBERS.txt` numbering runs 21, 23 — there is no §22.
The citation was written from the section's *position* rather than its number,
and read as sourced. → `claim_audit.py` now validates every `[N §x]` against the
sections `NUMBERS.txt` actually emits.

**Fabricated restore instructions.** `MANIFEST.md` told readers to run
`fetch_uci.py` and `fetch_stratc.py`. Neither exists — written from how the data
*ought* to be restored rather than from the repository. → replaced with
`missing_data.py`, which parses the loaders out of `harness.py` and refuses to
invent download URLs.

**A fabricated detail in §5.4.** "TITANIC's `body`-adjacent survivors" was
listed among B1-tuned's false positives; it is not in the output. Corrected to
the actual list.

## Reproducibility bugs in our own analysis

**`subtype_sensitivity.py` was not reproducible.** It drew a *different*
adversarial subset on every run despite a fixed seed, because the population
list was built from set-iteration order, which follows Python's string hash. Two
regenerations of §21 disagreed in the third digit. → `sorted()`, and the fix is
verified across `PYTHONHASHSEED`, not assumed.

**Python's `round()` is banker's.** `round(96.5)` is 96. A pin on a correctly
rounded 97% reported a failure on a right number. → `r0()` rounds half-up.

## Wrong diagnoses, corrected on the record

**The gemini truncation was blamed on our token budget, twice.** First on our
own `max_tokens`, then on a provider quota. The actual cause: at
`temperature=0.0` the model returns `finish_reason: "length"` after a few hundred
visible tokens **regardless of budget** — 12 of 40 columns at a 16,000-token
budget on KOI, while removing the temperature field alone returns all 40. It is
prompt-specific: CRIME at 144 columns never truncates at the same setting. This
is now Appendix L, and §8 says the attribution we first recorded was wrong.

**Seven cells reported as permanently stuck** when they were HTTP 429s — the
retry code classified rate limits as errors.

**Quarantined cells miscounted.** A claim that the paper's "11" was stale and
really 6 was itself wrong; §17 said 11 and the paper said 11. Corrected. (Four
have since been refilled; **seven** remain, and that count is now pinned because
it moves.)

## Instrument-fitting errors

**`openml_candidates.jsonl` was overwritten** by the Stratum C harvest, leaving
§4.3's table row with no source on disk. → harvest output moved to
`openml_wider_candidates.jsonl`.

**`openml_scan.py` silently returned 0 anchored** on re-run: the API was blocked
by the proxy and `features()` swallowed the exception. → now reads
`openml_meta/features.json` first, and a missing cache fails loudly.

**`verify_tables.py` mis-filed `B1-tuned` as `B1`** by truncating the label to
two characters, and reported the fitted rule as a mismatched frozen one. The
checker was right that the numbers disagreed and wrong about which claim it was
reading.

**A dagger broke label matching.** Marking `gemini-3.5-flash` rows with † would
have reported every one `UNMAPPED MODEL LABEL`; a footnote marker is not part of
a model's name.

## Argument errors

**§7.3 rested on a precision *rise* that the audited numbers reversed**
(0.627→0.457, fp 19→38). Rewritten to rest on the stated reason
(*"measured concurrently"*).

**A duplicate paragraph in §9** — a "why no such tool exists" passage added
without noticing the existing one. Caught by a referee simulation.

**`DIABETES.discharge_disposition_id`**: the corpus disagreed with itself.
Resolved to CONSEQUENCE — terminal dispositions record the outcome, but the
label was not computed from the column — which moved REASON 60→63, CONSEQUENCE
89→85, and reverted an earlier "ten of ten" to "eight of ten".

## UI bug worth remembering

The HTML coding page **inferred the current card from scroll position**, so a
keystroke could silently answer the wrong item. Caught by a Playwright test and
replaced with an explicit, visible current card. (A later smoke test that seemed
to show a failure was itself wrong — the code was right.)
