> **SUPERSEDED — working note, not a deliverable.**
>
> The P1–P9 framing has been cut from the paper. It was written in a scratchpad
> markdown file with no external timestamp, no registry deposit and no third
> party, so calling the entries "registered predictions" in a submission would
> have been an overclaim — the first reviewer to ask *registered where?* gets an
> answer nobody wants to give. Every **measurement** underneath survived the cut
> and is reported in the paper as a measurement: the Kaggle trigger rates on
> both denominators (§6.4.7), the 17–30% anchoring loss in three populations
> (§6.4.2), the zero admissible Kaggle records (§6.4.2), and the
> cirrhosis/Klaverjas/Bike Sharing downstream deltas (§6.4.6).
>
> Nothing below has been reworded. It is kept as project history: it records
> what was expected before the sweeps ran, which is worth having even though it
> cannot be cited.

# Registered predictions P1–P9 — outcomes

*Scored against `REGISTERED_STRATUM_C.md`, written 2026-08-15 before the harvest
finished and before any dataset was coded, downloaded in full, or shown to a
model. No prediction below has been reworded. One is split, one fails, two are
void, and three **cannot be scored yet** — which is itself the most substantive
outcome and is reported as such rather than quietly omitted.*

Kaggle figures are FINAL (sweep complete 02:15). Regenerate from `kaggle_sieve.out`, `hf_anchor.py`, `openml_harvest.py`,
`stratc_report.py`, `stratc_downstream.py`.

---

## Summary

| | prediction | outcome |
|---|---|---|
| **P1** | sieve fires on a smaller fraction of Kaggle than UCI | **depends on the denominator — reported both ways** |
| **P2** | fewer than half of surviving sentences anchor to a column | **CONFIRMED**, in three independent populations |
| **P3** | 2–8 admissible Kaggle datasets | **FAILED** — zero |
| **P4** | frontier C6 F1 on Stratum C in [0.75, 0.92] | **NOT SCOREABLE YET** — frontier arms queued |
| **P5** | TIMING recall ≥ 90% at every condition, frontier | **NOT SCOREABLE YET** — same |
| **P6** | REASON recall does not fall C1→C6 | **NOT SCOREABLE YET** — same |
| **P7** | SURROGATE recall below REASON/TIMING at C6 | **VOID** — mechanism withdrawn |
| **P8** | C2 lowers SURROGATE recall vs C1 | **VOID** — mechanism withdrawn |
| **P9** | dropping C6-flagged columns lowers F1, mean drop positive | **HOLDS on cirrhosis, FAILS on Klaverjas** |

---

## P1 — the honest answer is "it depends which denominator", so both are given

UCI: **13 of 689 datasets = 1.89%** had a surviving sentence.

Kaggle, **complete at 8,693 enriched** (8,694 indexed, one unreachable):
**258 datasets = 2.97%** had a surviving sentence. After removing the 87
synthetic datasets and the 61 detected re-uploads of Stratum A/B, **130 =
1.50%** remain.

So P1 **holds on the post-exclusion reading (1.50% < 1.89%) and fails on the raw
one (2.97% > 1.89%)**. The registration did not say which, because when it was
written it was not obvious the two would fall on opposite sides of the UCI rate.

We report both and prefer neither. The raw comparison is the like-for-like one —
UCI's 13 were never filtered for synthetic tables or re-uploads, because UCI has
almost none — which argues the sieve fires *more* readily on Kaggle prose, not
less. The post-exclusion comparison is the one that describes the population a
reader would actually work with. Note also that the exclusion arithmetic is
itself uncertain: §6.4.7 reports the re-upload filter at **48% precision**, so
the 61 is roughly half wrong and the 130 is an undercount.

**Reading P1 as confirmed would require choosing the denominator after seeing
the result.** It is recorded as split.

## P2 — CONFIRMED, and it is the one prediction that transfers cleanly

Fewer than half of surviving sentences anchor to a real column name, in every
population swept:

| population | anchored | rate |
|---|---|---|
| OpenML (re-sweep) | 30 of 101 | 29.7% |
| **Kaggle** (complete) | **30 of 117 readable** | **25.6%** |
| Hugging Face | 34 of 195 | 17.4% |

All three are far below 50%, and the mechanism is the predicted one: listings
rarely expose a schema, so a sentence survives the language test and then has
nothing to attach to. This is the prediction the sieve's design was most exposed
on, and it is the one that held.

## P3 — FAILED

Predicted 2–8 admissible Kaggle datasets. The answer is **zero**, across the
**complete** sweep of 8,693 enriched datasets and 130 real, new candidates. Not
"few" — none. All 30 anchored candidates fall into categories §2.1 excludes:
identifier warnings (`patient_id`, `plate`), derivations among features with no
designated target (`Total attendances`, `Total Renewable Energy`), admission- or
enrolment-time notes (`Stay`, `Age at enrollment`), data-vintage removals
(`carbon_intensity_elec`), and the target column itself (`HEATWAVE`, `Defects`).

Reported as a failed prediction. The registration says explicitly that "fewer
than 2 … and the validation is uninformative", and that judgement stands: the
Kaggle arm of Stratum C validates the *sieve's* behaviour and contributes no
records to the corpus. The two admissible Stratum C records both come from
Hugging Face (ChessFraud, Bike Sharing), which P3 did not cover.

The near-misses are documented in §6.4.3 — two datasets with a named column, a
stated derivation and an explicit exclusion instruction, which are still not
leakage because the dataset has no designated target. A sieve can locate
derivations; only a target turns one into leakage.

## P4, P5, P6 — NOT SCOREABLE YET, and this is the important entry

All three were registered over **frontier-tier models on Stratum C datasets**,
with frontier defined in the registration as `claude-opus-5`, `gpt-5.6-sol`,
`gemini-3.7-flash`, `gemini-3.5-flash`.

Neither half was in place when this was first written, and one half has since
been repaired:

* **The population was empty, and is no longer.** P3 failed, so there are no
  admissible *Kaggle* datasets. The Stratum C datasets first run were cirrhosis
  — hand-nominated, deliberately excluded from every yield denominator, and
  reported as a diagnostic case — and Klaverjas2018, from OpenML. **Bike
  Sharing has since been added** (17,379 × 14, positives `casual` and
  `registered`, provenance `SIEVE`, yield-eligible), so an admissible Stratum C
  record is now in the sweep. ChessFraud is deliberately still out, because its
  coding is open and choosing one to enable a sweep would be choosing it for
  the answer.
* **No frontier model has cells on them yet.** The ten models with cirrhosis
  cells are Athene-V2, Qwen2-72B, Qwen3-Next-80B, deepseek-v4-flash, gemma-4,
  Mistral-Large, Kimi-K3, nemotron-3-super, Llama-3.3-70B and GLM-5.2. This is
  a *queue* state, not an exclusion: `sweep_stratc` imports the full roster,
  which ends with `gemini-3.7-flash` and `gemini-3.5-flash`, and those arms are
  pending behind Google's daily quota. Opus and GPT have provider `ui`, no
  background arm, and need a foreground pass.

So the entry stands as **not scoreable yet**, and the reason has narrowed from
"the experiment cannot be run" to "half of it has not finished running". When
the two Gemini arms land, P4–P6 become scoreable over half the registered
frontier tier, and the paper must say *which* half — scoring them against the
ten non-frontier models instead would answer a different question with the
registration's authority attached.

**What the available data shows anyway**, offered as observation and not as a
scored prediction:

*Cirrhosis* (1 positive, `N_Days`, among 18 columns): **7 of 10 models flag it
at C1 and 7 of 10 at C6**; five have zero false positives at C1. Kimi-K3, GLM-5.2
and nemotron are exact at both conditions.

*Klaverjas2018* (2 positives, `leaf_count` and `time_real`, among 34): **three of
four models miss both at C1, and three of four miss at C6.** Only Mistral-Large
finds them, at C6 only. This is a genuine negative and it matters: Klaverjas is
the dataset that breaks §4.3's OpenML zero, its documentation states plainly
that the two columns *"should not be used as predictors"*, and the models
largely do not flag them. It is reported in §6.4 rather than left out.

## P7, P8 — VOID

Both were registered over the SURROGATE mechanism. SURROGATE was **withdrawn**
during the ground-truth audit, along with eight of the original 76 labels, on
the ground that the sources do not say what we had them saying. A prediction
about a category that no longer exists cannot pass or fail.

The registration anticipated untestability and required it be "recorded as such
rather than quietly dropped". That is what this entry is.

## P9 — HOLDS on cirrhosis, FAILS on Klaverjas

Run per dataset by `stratc_downstream.py`, which is the script that had stopped
executing at all (it read a spec key that no longer exists, so the previously
cited P9 figures came from a version that could not be run).

| dataset | keep-all | oracle | oracle Δ | mean model Δ | positive cells | P9 |
|---|---|---|---|---|---|---|
| CIRRHOSIS | 0.768 | 0.703 | **+0.065** | **+0.038** | 14 of 20 | **HOLDS** |
| KLAVERJAS | 0.891 | 0.894 | **−0.003** | −0.000 | **0 of 6** | **FAILS** |
| BIKESHARING | 0.995 | 0.927 | **+0.068** | — | no model cells yet | pending |

**The Klaverjas failure is reported as a failure**, and then diagnosed, in that
order. By the registered criterion — "the mean drop is positive" — P9 does not
hold there. The diagnosis is that **the oracle is negative too**: dropping the
two genuinely leaking columns *improves* F1 by 0.003, so no flagging behaviour
could have produced a positive mean. Five of the six cells dropped **zero**
columns (the models flagged nothing) and scored exactly +0.000; the sixth,
Mistral-Large at C6, dropped precisely the two correct columns and landed on the
oracle. So the models did not fail P9 on Klaverjas so much as the dataset lies
outside what P9 can test.

We state both halves because stating only the second would be choosing the
interpretation that suits us. The registration did not carve out datasets whose
leakage is downstream-inert, and it should have; §6.4.5 makes that case on its
merits rather than retroactively.

**Bike Sharing reproduces the recorded figure.** Its oracle delta of +0.068
matches the previously reported 0.9953 → 0.9274 (0.0679) to within rounding —
so the median threshold now pinned in the source is the one originally used,
even though it was never written down. That number was reproducible after all;
it simply could not be *shown* to be.

---

## P9 — the original entry, for the cirrhosis detail

On cirrhosis, dropping what a model flags at C6 moves F1 in the predicted
direction: **mean ΔF1 +0.036 across 16 model-condition cells, 11 of 16
positive**, against an oracle delta of +0.065. **Seven cells reproduce the
oracle exactly** — five models at C1 drop one column, the right one, and land on
the honest baseline to three decimals.

The failures are legible rather than noisy. Qwen2-72B drops five columns, misses
`N_Days` among them, and ends *above* the keep-all baseline — it removed noise
and left the leak. Mistral-Large at C6 drops seven columns for +0.051, beating
several models while discarding six legitimate features. This is why the number
of columns dropped is printed beside every delta and no ranking is offered on
delta alone.

Scored on one hand-nominated dataset, so it is weaker evidence than the
registration envisaged.

---

## The falsification table

`REGISTERED_STRATUM_C.md` listed four results that would falsify central claims.
**None triggered** — but three of the four are conditioned on frontier
performance over Stratum C and cannot be evaluated until those arms run, for the
same reason P4–P6 cannot.

| falsifier | status |
|---|---|
| frontier C6 F1 < 0.658 | not yet evaluable — frontier arms queued |
| TIMING recall < 80% | not yet evaluable — same |
| REASON recall falls C1→C6 across the frontier tier | not yet evaluable — same |
| mean downstream ΔF1 ≤ 0 | **not triggered** — +0.036 on cirrhosis |

A falsification test that cannot be run is not a test passed. The paper should
say so in those words.

---

## What to write in the paper

The registration's own framing is the right one and it survives: Stratum C was
built to find out whether the result is a fact about columns or a fact about
archive prose. The answer it gives is narrower than hoped and is still an
answer.

* **The sieve's trigger rate transfers** across four documentation cultures.
* **Its precision does not**, and P2 predicted exactly that.
* **The Kaggle arm yields nothing admissible**, which is a failed prediction and
  is reported as one.
* **The model-performance predictions could not be scored at the time of
  writing** — the Kaggle population came up empty, and the frontier arms on the
  records that do exist are still queued behind a provider quota.

Reporting three unscoreable predictions is less satisfying than reporting three
confirmations, and it is what happened. The alternative — rescoring P4–P6
against whichever models and datasets are to hand — would convert a
pre-registration into a post-hoc analysis wearing its clothes.
