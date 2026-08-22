# KOI vetting-field leakage — the §H experiment

Working files for the second paper: a techniques paper on vetting-derived
features in Kepler Object of Interest machine-learning studies. The dossier it
belongs to is `docs/research/koi-leakage-citation-dossier.md` in the
`celesta-exoplanet-flagship` repo.

## What was blocked, and why it no longer is

Dossier §H — "the one experiment that has to be run" — states the delta cannot
be produced because `exoplanetarchive.ipac.caltech.edu` returns 403 at the
proxy. That is still true of the archive, but irrelevant: all three KOI tables
were downloaded on **2026-08-08** and remain in the session uploads
(`cumulative`, `q1_q17_dr24_koi`, `q1_q17_dr25_koi`), carrying every column the
experiment needs — `koi_disposition`, `koi_pdisposition`, `koi_score`, and the
four `koi_fpflag_*`.

## The prediction, and what actually happened

> §H, step 4: *"Run a flags-only arm — the six leakage columns and nothing else.
> If this alone reaches ~0.98, it proves label reconstruction rather than
> astrophysics. This is the decisive experiment and the paper's strongest
> single figure."*

**It does not reach ~0.98. It reaches 0.7814 — below the clean arm.** That
specific prediction is falsified and must not survive into a manuscript.

| arm | accuracy | weighted F1 |
|---|---|---|
| clean, 98 astrophysical features (published) | 0.8618 | 0.8624 |
| flags only — the 4 `koi_fpflag_*` | 0.7814 | 0.7076 |
| `koi_score` alone | 0.7854 | 0.7548 |
| `koi_pdisposition` alone | 0.7921 | 0.7162 |
| **flags + `koi_score`** | **0.8715** | 0.8704 |
| **flags + score + pdisposition** | **0.8829** | 0.8805 |

## What replaced it, which is sharper

Per-class, the flags-only arm:

| class | precision | recall | F1 |
|---|---|---|---|
| `FALSE POSITIVE` | 0.996 | 0.980 | **0.988** |
| `CONFIRMED` | 0.569 | 0.993 | 0.723 |
| `CANDIDATE` | **0.000** | **0.000** | **0.000** |

Four columns that exist *only* as the Robovetter's stated reasons for an FP call
reconstruct the FP class almost perfectly, and carry no information separating
CONFIRMED from CANDIDATE — the flags are zero for both. The label is not one
thing: one third of it is a Robovetter artifact the flags trivially invert, and
the rest is a human disposition they say nothing about. That is dossier §B's
ontology argument, measured.

The headline for §H is therefore **six vetting columns beat ninety-eight
astrophysical ones** (0.8715 vs 0.8618), with `koi_score` alone — the
Robovetter's own disposition confidence — nearly matching the entire clean
pipeline.

## Matching

Scored on the clean arm's **own folds**. `data/koi-index.json` in the flagship
repo carries the fold assignment for all 9,564 KOIs in the published 0.8618 run
(5-fold `StratifiedGroupKFold` grouped on `kepid`), so these arms sit on the
same partition rather than a fresh split. All 9,564 objects joined on
`kepoi_name`.

## The caveat that must be stated in the paper

**The learner does not match.** These arms use
`HistGradientBoostingClassifier`; the published clean arm is a LightGBM+CatBoost
ensemble. Folds match, learner does not, so the delta carries some learner
effect. Closing this needs `celesta-exoplanet-reproducible-model`, which holds
the 98-feature pipeline and is not attached to this session — an `add_repo`
away, and the only genuinely blocked step remaining.

## Files

- `flags_only.py` — the experiment; reads the cumulative table from session
  uploads and `data/koi-index.json` from the flagship repo
- `RESULT_flags_only.txt` — its output, as run
