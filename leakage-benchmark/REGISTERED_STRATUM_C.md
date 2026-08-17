# Registered predictions — Stratum C (Kaggle validation set)

**Written 2026-08-15, before the harvest finished and before any dataset was
coded, downloaded in full, or shown to any model.** Nothing below is revised
after the fact. Where a prediction fails, the failure is reported in §7 beside
the C6/C9 registration that already failed once (§7.2).

---

## What this set is for

Stratum A and B both come from curated academic archives. Every result in the
paper therefore rests on one documentation culture: codebooks, written by
collectors, for archives with submission standards. Kaggle descriptions are
written by uploaders, in markdown, for competitors. **If the detection result
is a fact about archive prose rather than about columns, Stratum C is where
that shows.**

Stratum C is run **once**. No prompt is revised after seeing it, no dataset is
dropped after seeing a model's answer, and no sieve pattern is added to
improve its yield.

## Construction rules, fixed in advance

1. The frozen sieve only — `explicit_scan`'s WARN and DEFINE, `cond_scan`'s
   CONDSET. **No pattern is added, removed or tuned for Kaggle**, even where a
   miss is visible on inspection.
2. Admission requires the uploader's own sentence naming the column, verified
   against the real CSV header at build time. My reading of a column name is
   not evidence here, so Stratum C carries **no `INFERRED_FROM_DESCRIPTION`
   records at all**.
3. A dataset that duplicates one already in Stratum A or B is excluded, on the
   dataset's content and not its name — Kaggle is full of re-uploads of UCI
   tables, and Diabetes-130 is already in the search results.
4. Queries are generic ("classification", "risk", "outcome"), never
   leak-suggestive, so the population is not selected for the answer.

## Predictions

### On the sieve's yield

**P1.** The sieve will fire on a **smaller fraction of Kaggle datasets than of
UCI datasets**, because it was written against archive prose. UCI was 13 of 689
datasets with surviving sentences.

**P2.** The dominant failure will be **anchoring, not triggering**: Kaggle
listings rarely expose a column schema, so sentences will survive the language
test and then have no column name to attach to. I predict **fewer than half**
of surviving sentences will anchor to a named column.

**P3.** Stratum C will yield **between 2 and 8 admissible datasets**. Fewer
than 2 and the validation is uninformative; more than 8 would mean Kaggle
documents leakage far better than the archives, which I do not expect.

### On model performance

Frontier tier = `claude-opus-5`, `gpt-5.6-sol`, `gemini-3.7-flash`,
`gemini-3.5-flash`. Reference points: frontier C6 F1 was 0.854–0.894 on
Stratum A and 0.808–0.926 on Stratum B.

**P4.** Frontier C6 F1 on Stratum C lands in **[0.75, 0.92]**.

**P5.** TIMING recall is **≥ 90%** at every condition for every frontier model,
as it was on both existing strata.

**P6.** REASON recall rises from C1 to C6, or is already ≥ 90% at C1 with no
room to rise. It does **not** fall.

**P7.** SURROGATE recall at C6 is **below** REASON and TIMING recall in the
same cells — the blind spot is a property of the category, not of the corpus.
*If Stratum C contains no SURROGATE columns, P7 is untestable and is recorded
as such rather than quietly dropped.*

**P8.** Adding the prediction point (C2) lowers SURROGATE recall relative to
C1, replicating §7.4. Same untestability caveat as P7.

### On the downstream test

**P9.** On Stratum C datasets with a usable target, dropping what a frontier
model flags at C6 **lowers** F1 relative to keeping everything, and the mean
drop is positive. A negative mean would mean the flags are removing signal
rather than leakage.

## What would falsify the paper's central claims

Stated now so that a bad result cannot be reframed later as a partial success:

| result | what it falsifies |
|---|---|
| frontier C6 F1 **< 0.658** (B3's tuned Stratum-A score) | the detection claim does not generalise beyond archive prose. §6 becomes a negative result. |
| TIMING recall **< 80%** | the "models operationalise leakage as timing" mechanism is wrong, and §6.2, §7.3 and §9 all fall with it. |
| REASON recall **falls** C1 → C6 across the frontier tier | the derivation clause does not do what §6.2 says it does. |
| mean downstream ΔF1 **≤ 0** | model-based cleaning does not recover honest performance, and §7.5 does not generalise. |

## What this set cannot do

It cannot show the ground truth is complete — legitimate-by-default applies
here too, so precision on Stratum C is a lower bound exactly as it is
elsewhere (§4.6). It cannot control for memorisation: Kaggle datasets are
public and mostly pre-cutoff, so Bordt et al.'s finding applies to them as it
applies to Stratum A. And it is a convenience sample of a search API, not a
census of Kaggle — the yield figures describe what the queries reached, and
the queries are listed in `kaggle_harvest.py` so a reader can see their shape.
