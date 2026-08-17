# Stratum C — external validation set

Live record. Written as the sweeps run, not after, so that a source which
yields nothing is recorded with the same weight as one that yields a dataset.

The registered protocol is `REGISTERED_STRATUM_C.md`, written before any
dataset was coded. Two of its predictions are now void for reasons that have
nothing to do with the results below, and both are recorded here rather than
quietly dropped:

* **P7 and P8 are void.** Both concern SURROGATE recall. The SURROGATE
  mechanism was withdrawn from the paper entirely (§2.2) after the G1/G2
  re-reading, which happened before Stratum C was run and for reasons
  independent of it. There is no SURROGATE category left to predict about.

---

## 1. Sources and what each one can give

| source | population | prose written by | schema exposed? | status |
|---|---|---|---|---|
| Kaggle datasets | 8,694 indexed | uploaders, markdown | no | enriching |
| Kaggle competitions | 605, complete | hosts, one line | no | **done, zero** |
| Hugging Face cards | keyword + tag sweep | model developers | no | running |
| OpenML | 6,420 | archive uploaders | **yes** | re-sweep |
| UCI | 689, complete | collectors | yes | already Stratum A/B |

**OpenML and UCI are not external validation.** Both were already swept to
build Stratum A and B (`EXPLICIT_SOURCES.md`). The OpenML pass now running is
a *re-sweep with full column schemas*, which the original pass did not fetch:
it re-measures the same population with anchoring available for every dataset
rather than only for datasets that hit. It verifies §4.3's numbers and measures
registered prediction P2's anchoring rate cleanly. It does not extend the
corpus, and no record from it may be counted as external.

---

## 1b. CORRECTION REQUIRED — §4.3's OpenML column is wrong, and why

**This is the most consequential thing Stratum C has produced and it is a
correction to the paper, not an addition to it.**

### The claim that fails

PAPER.md §4.3 reports:

| | UCI | OpenML |
|---|---|---|
| records swept | 689 | 6,420 |
| sentences surviving the sieve | 81 (13 datasets) | 89 (89 datasets; 10 distinct) |
| **feature-level target leakage** | **6** | **0** |

and states: *"Every OpenML sentence our sieve surfaced uses 'leakage' for splits
or identifiers, and none for a feature-level relationship."* The headline that
rests on it is **"6 in 7,109 — 0.084%."**

**The OpenML zero is false.** OpenML dataset **41228, Klaverjas2018**, documents
two leaking columns in its own uploader description:

> The fields `leaf_count` and `time_real` are meta-data as result from the
> $\alpha\beta$-search procedure, and **should not be used as predictors**.

Quote verified verbatim against the cached record. The same description names
the target (`outcome`) and the legitimate feature set (`card_{S,H,D,C}_*`, 32
columns) explicitly, so there is no interpretation left to do.

### Why the sweep never saw it

The two archive passes did **not** run the same sieve, and the table presents
them as though they did.

* `explicit_scan.py` (UCI) gates on **WARN | DEFINE**.
* `openml_scan.py` (OpenML) gates on its own narrower **STRONG** regex —
  `leaka?ge|leaky|should be (removed|dropped|discarded|excluded)|not known
  before|only known after|cheat|unrealistic|artificially`. WARN is recorded as
  a flag afterwards but never used as an admission gate:

  ```python
  s = STRONG.search(sent)
  w = WARN.search(sent) if s else None
  if not s:
      continue                     # <- WARN-only sentences are discarded here
  ```

"should not be used **as predictors**" is WARN vocabulary. It is not STRONG
vocabulary — STRONG requires *removed/dropped/discarded/excluded*, and the
uploader wrote *not be used*. So the sentence was thrown away before anything
classified it.

Re-running the **UCI sieve** over the same cached 6,420 OpenML descriptions:

| filter used | sentences | datasets |
|---|---|---|
| STRONG (what the paper reports) | 89 | 89 |
| **WARN \| DEFINE (what UCI used)** | **145** | **101** |

**137 sentences matched the UCI sieve and were never classified.** Both
sentence splitters were checked against each other and give identical counts, so
the gap is the filter and nothing else.

### What is in the 137

Most are noise the STRONG filter was right to skip — `circularity` matching a
warning pattern 9 times, `combination of the above` 24 times. But the WARN
vocabulary that carries real signal is in there too: *should be ignored* (13),
*should not be used* (8), *were removed from* (7), *strong correlation with*
(5). Reading those:

* **Klaverjas2018** — the record above. Admissible.
* `climate-model-simulation-crashes` (40994) — *"deactivated first two
  variables as they describe the batch of the experiments"*: batch metadata,
  closer to an identifier artefact than to feature-level leakage.
* `baseball` (185), `colic` (25) — *"is an identifier that should be ignored"*:
  identifier columns, an existing category.
* three copies of Student Performance's G1/G2 sentence — already withdrawn by
  the §4.7 audit.
* the rest are data-cleaning notes.

So the 137 yield **one** new admissible dataset, not a flood. The scarcity claim
survives; the specific number does not.

### The empirical check, and an honest nuance

981,541 rows, target `outcome`, 60,000-row sample, RandomForest(200), 5-fold,
seed 0:

| arm | F1 |
|---|---|
| cards + `leaf_count` + `time_real` + `index` | 0.885 |
| **cards only (oracle)** | **0.893** |
| `leaf_count` + `time_real` alone | 0.615 |

Single-column AUC: `leaf_count` **0.698**, `time_real` **0.699**, against 0.508–0.528
for the card columns.

Both columns carry substantial independent signal about the outcome — 0.70 AUC
each, and 0.615 F1 between them with no card information at all. But adding them
to the full card set *lowers* F1 by 0.008, because the 32 card columns are a
complete description of a perfect-play position and already saturate the signal.

**This is a case worth keeping precisely because it is awkward**: the columns
are unambiguously leakage by the definition in §2.1 — produced by the procedure
that produces the label, absent at the prediction point, and the source says so
— and dropping them does not improve a downstream score. Leakage does not always
inflate. It inflates when the honest features are incomplete, which is the usual
case and is not this one.

One caveat recorded rather than buried: this table is *computed*, not observed —
exhaustive game-theoretic values, about 2 CPU-years of search. It is not
synthetic in the sense the sweep excludes (nobody planted a leak and then
documented it); the leakage is incidental solver metadata, which is exactly the
real-world condition. It is flagged as computed-not-observational wherever it
appears.

### What has to change in the paper

1. §4.3's table row **`feature-level target leakage | 6 | 0`** becomes **`| 6 | 1
   dataset, 2 columns |`**.
2. The sentence *"none for a feature-level relationship"* must go.
3. **"6 in 7,109 — 0.084%"** becomes **7 in 7,109 — 0.098%**.
4. The row label *"sentences surviving the sieve"* must say which sieve, or both
   columns must be recomputed on one filter. Reporting 81 (WARN|DEFINE) beside
   89 (STRONG) under a shared label is the actual defect; the wrong zero is its
   symptom.
5. §4.3.2 already records one sieve miss (AI4I) and §5 records a second
   (cirrhosis). This is a **third**, and unlike the others it is not a limit of
   the vocabulary — it is two passes using different vocabularies and being
   reported as one.

Fixing this strengthens the paper. An unexplained zero in a table invites a
reviewer to find the counterexample; a documented filter gap with the
counterexample already in hand is a methods contribution about how hard this
class of measurement is.

---

## 2. Kaggle competitions — complete, and the answer is zero

Swept exhaustively: 9 category filters × 30 pages, 605 unique competitions,
every one of them through the frozen sieve on title, subtitle and description.

**Zero surviving sentences.**

This is not evidence that competition hosts fail to document leakage. It is a
fact about the API's description field:

* median description length **88 characters**
* competitions with more than 200 characters of prose: **0 of 605**

Representative in full: *"Create an AI capable of fluid intelligence."*

The prose that would matter — the Overview and Data tabs, where hosts document
columns and announce mid-competition leakage patches — is rendered
client-side. Fetching `/competitions/<slug>/data` returns a 5 KB JavaScript
shell containing no content. `competitions/data/list/<slug>` returns file names
with an empty `description` on every file. `datasets/list/<owner>/<slug>`,
which would reach any data-dictionary file shipped inside a dataset, returns
`403 Permission 'datasets.get' was denied` for this token.

Competitions are, on the face of it, where feature-level leakage is discussed
most seriously anywhere in practice — a leaking column decides a leaderboard.
That the public API exposes none of that discussion is worth one sentence in
the paper's limitations and no more. **The yield is reported against the
denominator "competitions with more than 200 characters of prose" (zero), not
"competitions" (605)**, because the second framing would turn an API ceiling
into a finding about practitioners.

---

## 3. Re-upload detection had to be rebuilt

Registered construction rule 3 excludes any Kaggle dataset that duplicates one
already in Stratum A or B, **on content and not on name**. The original
implementation compared column names but considered only names of **four or
more characters**. That filter passed a verbatim re-upload of UCI Student
Performance into the candidate list, because the columns that identify that
dataset are `G1`, `G2` and `G3` — every identifying string was discarded before
the comparison ran. The sentence it fired on was the G1/G2 one this project
withdrew in §4.7. Scoring a model on it would have been scoring it on Stratum B
and reporting the result as external validation.

`mirror2.py` replaces it with three signals, any one sufficient:

1. **column overlap**, now including 2–3 character names, which count only when
   at least six line up together — short tokens collide by accident;
2. **target name plus any two columns** — a re-upload almost always keeps the
   target's name, and the target is the column a description most often
   mentions;
3. **credited source name** in the title or description — an uploader crediting
   "Student Performance" or "Bank Marketing" gives the strongest signal there
   is.

This can only remove candidates, never add them, so it makes the yield strictly
more conservative. It is rule 3 implemented properly, not a new rule, and it is
**not** a change to the frozen sieve — the sieve decides which sentences
survive, this decides which datasets are thrown out.

On the 3,832 datasets enriched at the time of writing, 36 candidate datasets
are re-uploads:

| signal | datasets caught |
|---|---|
| long column overlap (original detector) | 19 |
| target name + two columns (new) | 10 |
| credited source name (new) | 7 |

**17 of 36 — nearly half — would have entered the validation set under the old
detector.** They mirror BANK (14), STUDENT (6), AI4I (4), CIRRHOSIS (4),
SUPPORT2 (3), LC (2), DIABETES (2) and COMPAS (1).

That CIRRHOSIS appears four times over is worth noting on its own. It is the
Mayo Clinic PBC trial, it ships as `pbc` in R's `survival` package, and Kaggle
alone carries four further copies — which is why the aliased arm on §4's record
is not a formality but the most interpretable memorisation signal in the
corpus.

---

## 4. Anchoring: P2 confirmed, and the sieve's precision collapses on Kaggle

`datasets/download/<ref>` works even though `datasets/list/<owner>/<slug>`
returns 403, so the real CSV header can be read for every candidate and
registered rule 2 can be enforced properly rather than by my reading.
`kaggle_anchor.py` downloads each real, non-mirror candidate, reads headers
straight out of the zip without unpacking, and checks which surviving sentences
name a column that exists.

**Registered prediction P2 is confirmed.** It predicted that under half of
surviving sentences would anchor to a named column. Of 49 candidates, 40 had a
readable header and **8 anchored — 20.0%**. Nine were skipped for exceeding the
250 MB cap and are listed as skips, never folded into "no anchor"; that is the
same error as the 29 undownloaded UCI records reported as though the archive
were 660 (§4.3.2).

**The more interesting result is what anchoring alone does not buy.** Seven of
the eight anchored sentences fail the semantic check, and they fail the same
way: the sieve's WARN vocabulary is *homonymous* in Kaggle prose.

| dataset | column | sentence | why it fails |
|---|---|---|---|
| EU AI Act Risk Register | `market_withdrawal_required` | "must be removed from EU market" | removed from a *market*, not from the feature set |
| Tree Survival | `Core` | "Year the soil core was removed from the field" | removed from a *field* |
| World Energy Consumption | `carbon_intensity_elec` | "was removed from the energy dataset (no updated data)" | removed for *availability*, not leakage |
| AV Healthcare II ×3 | `Stay` | "identify patients of high LOS risk … at the time of admission" | describes the prediction *task*; `Stay` is the target |
| Student Dropout | `Age at enrollment` | "Age of the student at the time of enrollment" | a plain definition of a legitimate feature |

On UCI prose, "removed" in a dataset description nearly always means removed
from the analysis. On Kaggle it means removed from a market, a field, or a
release. **The sieve's trigger rate transfers across documentation cultures;
its precision does not.** That is a cleaner statement of the same point §4.3
makes and it is only visible because Stratum C exists.

### Two later anchors, and the one that shows what "leakage" needs to exist

At 4,157 enriched the anchoring rate held at **21.7%** (10 of 46 readable) and
two new anchors appeared. Both are instructive and neither is admissible.

**COVID-19 Hospitals Treatment Plan** — `Illness_Severity`: *"Severity of the
illness recorded at the time of admission."* The sieve's `at the time of
admission` pattern fires, and the sentence says the **opposite** of leakage: the
value is recorded **at** the prediction point, which makes the column
legitimate. Another homonym, and the clearest one — the same string that marks a
positive in a codebook marks a negative here.

**A&E attendances England** — `Total attendances`: *"The total of the above."*
This is a real DEFINE hit on a real derivation, and the arithmetic confirms it
perfectly: `Total attendances == Type 1 + Type 2 + Type 3` holds **exactly on
all 27,112 rows**, maximum absolute deviation 0.0.

And it is still not target leakage. It is a derivation **among features**. The
dataset is a monthly NHS statistics series with no designated target, so there
is no outcome for the derivation to run into. The obvious candidate,
`Percentage in 4 hours or less (all)`, does not survive contact with the data:
it ranges to 5.0 with a median of 1.0, and the numerator/denominator identity
holds on only 32.8% of testable rows, so it is not a clean rate and cannot be
treated as a target derived from those columns.

**This is the paper's own definition arriving as an empirical result.** §2.1
says leakage is a property of the triple (column, target, prediction point).
Here two of the three are present and verified — a column, and a derivation
proven exactly on 27,112 rows — and the absence of the third makes the whole
thing a non-finding. A sieve can locate derivations; only a designated target
turns one into leakage. Worth a sentence in §2.1 as a worked case rather than a
definitional aside.

### Registered prediction P3 is on course to FAIL, and the failure is the finding

P3, written before the sweep: *"Stratum C will yield between 2 and 8 admissible
datasets. Fewer than 2 and the validation is uninformative; more than 8 would
mean Kaggle documents leakage far better than the archives, which I do not
expect."*

At **6,557 of 8,694** Kaggle datasets enriched (75% of the sweep) [as-of];
the completed sweep is reported in `STRATUM_C_SECTION.md` §6.4.2:

| stage | count |
|---|---|
| surviving sentences | 262 |
| datasets with a surviving sentence | 193 |
| synthetic (excluded) | 72 |
| re-uploads of Stratum A/B (excluded) | 52 |
| real and new | 86 (1.31% of enriched) |
| with a readable CSV header | 75 |
| **anchored to a real column** | **21 (28.0%)** |
| **admissible after reading the sentence** | **0** |

The trigger rate is stable as the denominator grows — 1.33% at 58% of the
sweep, 1.31% at 75% — which is what makes it quotable.

**Not one anchored sentence on Kaggle has survived the semantic check.** All
twenty-one fail for one of five reasons, and the pattern is the result:

1. **Homonym** — the sieve's WARN vocabulary means something else in this
   prose. *"must be removed from EU market"*, *"the soil core was removed from
   the field"*, *"removed from the dataset (no updated data)"*, and a `plate`
   matched because a spectrograph uses a *"circular metal plate"*.
2. **Describes the prediction task, not a column** — *"identify patients of
   high LOS risk at the time of admission"*, where `Stay` is the target.
3. **Places the value AT the prediction point** — *"severity recorded at the
   time of admission"*, which makes the column legitimate; the sieve's pattern
   fires on the sentence that says the opposite of leakage.
4. **Identifier column** — `patient_id`, *"an identifier and should not be used
   as a predictive feature"*. A real warning, and §2.1 files it as a separate
   category.
5. **Generic definitional phrase** — `INDICATOR`, *"Indicator for the data
   type"*, where DEFINE matched ordinary dictionary prose.

The homonyms get funnier as the population grows, and each one is a real
uploader writing carefully about something else:

> *"Items at various stages of production are **removed from** the process and
> inspected for defects"* · *"`deletedOn`: when it was **removed from**
> Happyforce"* · and, matching the WARN pattern `would not be available`, an
> **acknowledgements sentence**: *"This data **would not be available** without
> the full collaboration from our customers."*

**A second instance of the missing-target case (§4, A&E attendances) turned
up**, and it is the closest Kaggle has come to admissible:

> `alistairking/renewable-energy-consumption-in-the-u-s` —
> *"You most likely want to **exclude** the column titled `Total Renewable
> Energy` from your comparative analysis across fuel types as it represents the
> **sum of the others**."*

A named column, a stated derivation, and an explicit instruction to exclude it —
everything except a target. The dataset is a consumption time series with no
designated outcome, so the derivation runs among features and stops there.
Two independent instances of the same shape now support the §2.1 point: a sieve
finds derivations, and only a designated target turns one into leakage.

If the remaining 25% of the sweep behaves like the first 75%, **P3 fails**. The
registration says a failed prediction is reported rather than reframed, so:
Kaggle, as reached by these queries and this sieve, yields **no** admissible
feature-level target leakage record.

That is not a null result about Kaggle. It is a measurement of the same thing
§4.3 measures — how rarely anyone writes feature-level leakage down in a form a
scanner can catch — replicated in a population that shares no curation process
with the archives. The trigger rate transfers (1.33% of Kaggle datasets against
1.9% of UCI). The **precision** does not, and that is the part worth reporting.

### The one that survives, and how far it survives

**Twitter User Gender Classification** (crowdflower), 20,050 rows, 26 columns,
target `gender`. Not synthetic, not a re-upload, and from a genuinely different
documentation culture — a crowdsourcing vendor's release note.

The dataset is full of annotation-process artefacts, and the uploader documents
them by name:

> **gender_gold**: if the profile is golden, what is the gender?
> **gender:confidence**: a float representing confidence in the provided gender

`gender_gold` holds the target's own value. It is feature-level target leakage
by the definition in §2.1 with no interpretation required. `gender:confidence`,
`profile_yn:confidence`, `_trusted_judgments`, `_last_judgment_at`,
`_unit_state` and `_golden` are all produced by the labelling process, at the
moment the target is produced — CONSEQUENCE.

**Two things have to be said about it, and neither is flattering.**

*First, provenance splits.* The sieve found the **dataset**, by firing on the
`profile_yn` sentence. It did **not** fire on the `gender_gold` sentence — that
one has no warning verb and no derivation verb, exactly like cirrhosis. So the
dataset is `SIEVE`-found and the admissible **column** is `HAND_NOMINATED`. The
column is excluded from column-level yield denominators on the same rule that
excludes cirrhosis.

*Second, it is empirically inert.* Random forest, 5-fold, one-vs-rest on
`gender == female` (18,836 rows, 6,700 positive):

| arm | F1 |
|---|---|
| all columns | 0.510 |
| content columns only, all annotation dropped | 0.504 |
| annotation columns only | 0.151 |

Single-column AUC is **0.500** for every annotation column except
`gender:confidence` at **0.553**. `gender_gold` is non-null for **50 of 20,050
rows** and agrees with `gender` 90% of the time where present.

So this is AI4I in reverse: there the documentation named five flags and only
four held; here the documentation names a column that genuinely contains the
target and the column is 99.75% missing, so it moves nothing. It is
**definitionally** leakage and **practically** negligible, and it is recorded
that way. A downstream drop-and-refit on it would show approximately zero, and
reporting it without that number attached would oversell the only Kaggle record
Stratum C has so far.

---

## 4b. ChessFraud (Hugging Face) — the record Stratum C was built to find

**Found 22:00. The only source-licensed, empirically decisive Stratum C record
in the sweep so far, and it comes from the fourth documentation culture.**

`artemlepin/chess-fraud` — a 2026 tabular benchmark for cheating detection in
online chess, accompanying *"Exploring the Capabilities of Human-Aligned Models
for Cheating Detection in Online Chess"*. The `chess_fraud` configuration is
**real**: 505 controlled games from two tournaments, 38,510 half-move rows, 33
columns, in which a plugin showed some players Stockfish lines. Not a re-upload
of anything in Stratum A, B or C.

### What the source says

Five columns are documented as belonging to the cheating apparatus or to what
happened after the game:

| column | the card's own words |
|---|---|
| `assistance_line_rank` | *"One-based rank of the displayed engine line **followed by the player**"* |
| `player_hint_shown` | *"Whether a Stockfish hint was shown to the current player on this half-move"* |
| `assistance_search_depth` | *"Search depth assigned to the player in the tournament plugin"* |
| `is_accused_by_opponent` | *"Whether the opponent accused `player_id` of cheating **after the game**"* |
| `is_cheating_player_game` | *"Player-game cheating label used for game-level evaluation"* |

The move-level target is `is_cheating_move`: *"Whether the move belongs to a
followed Stockfish line under the tournament annotation protocol."*

### What the data says

| check | result |
|---|---|
| `assistance_line_rank IS NULL` ⟺ `is_cheating_move == False` | **1.000000 agreement, 38,510 rows** |
| `player_hint_shown == is_cheating_move` | 0.9776 |
| `is_accused_by_opponent` AUC on the game-level label | 0.617 |

`assistance_line_rank` is null on precisely the 29,105 non-cheating rows. **The
column's missingness alone is the label.** Nothing else in this project comes
close: it is a perfect determinant, and it is documented by the uploader in a
sentence that names it.

Downstream — RandomForest(200), 5-fold **grouped by `game_id`** so no game
spans a split, 20,000-row sample, seed 0:

| arm | F1 |
|---|---|
| keep everything | **1.0000** |
| drop the five documented columns | **0.3575** |
| `assistance_line_rank` alone | 1.0000 |

**ΔF1 = 0.643.** Cirrhosis was 0.051; Klaverjas was −0.008.

### Two things this record teaches beyond itself

**The synthetic filter would have thrown it away, and the filter is wrong.**
The card contains the word *"synthetic"* because the dataset ships **two**
configurations — `chess_fraud` (real tournaments) and `chess_fraud_synth`
(engine-generated alternatives for training). `kaggle_deep.SYNTH` matches
per-DATASET, so one word in a section about the *other* configuration would have
excluded a real record carrying a perfect leak. **Exclusion has to be
per-configuration.**

*The Kaggle exclusions were then re-audited for the same mistake, and the honest
answer is that it barely occurs there.* Of the **58** Kaggle datasets excluded
as synthetic, **57** carry the trigger word in a context that describes the
whole table; only **1** has it scoped — and that one is a different bug
entirely:

> `jeannkouagou/aimo3-tool-integrated-reasoning`: *"Contains actual Python code
> execution results from a stateful Jupyter kernel, **not synthetic** traces"*

The filter matched "synthetic" inside a sentence declaring the data is **not**
synthetic. That is negation blindness, not a scoping error, and it is a real
flaw in the exclusion rule. It cost nothing here: the dataset's only surviving
sentence is *"Hints are excluded from final training data to prevent solution
leakage"*, which names no column and concerns training-set construction rather
than a feature. Recorded because a filter flaw whose impact happened to be zero
is still a filter flaw, and the next sweep may not be so lucky.

**It is post-cutoff for most of the roster.** A 2026 dataset cannot have been
memorised by a model trained before it existed, which makes this the cleanest
memorisation control in the corpus — cleaner than paraphrasing, because there is
nothing to recall rather than a renamed thing to fail to recall.

### Open coding question — deliberately NOT resolved

Five candidate positives, and they are not equivalent:

* `assistance_line_rank`, `player_hint_shown`, `assistance_search_depth` are the
  **apparatus that produces the label**. CONSEQUENCE, and unambiguous.
* `is_accused_by_opponent` is **post-game**. TIMING, and it depends on where the
  prediction point sits: if the task is "given the finished game record, decide
  whether the player cheated", an accusation arrives at roughly the same moment
  and the column is arguably contested rather than leaking.
* `is_cheating_player_game` is plausibly a **second target**, not a feature at
  all. Coding it as a positive feature would be a choice, not a reading.

The corpus already carries 2 CONTESTED positives, so there is precedent for the
middle case. This is left open for the user rather than settled unilaterally,
because a 0.643 ΔF1 record is exactly the one where a self-serving coding
decision would do the most damage.

Cached: `stratc_data/chessfraud.csv` (38,510 × 33) and
`hf_meta/chess_fraud_card.json` (20,981 chars, the licensing source).

---

## 4c. Bike Sharing — the same table documented as leaking in one archive and
not the other

**This is the result Stratum C was registered to look for**, stated in the
protocol as: *"If the detection result is a fact about archive prose rather than
about columns, Stratum C is where that shows."*

`t22000t/bike-sharing-tabular` on Hugging Face is UCI 275, Bike Sharing —
17,379 hourly records, 17 columns. Its uploader's feature dictionary reads:

| feature | type | description |
|---|---|---|
| `casual` | int | **Leakage** — non-registered user count (excluded from features) |
| `registered` | int | **Leakage** — registered user count (excluded from features) |
| `cnt` | int | **Target** — total rentals (`casual + registered`) |

and, in prose: *"`casual` and `registered` sum to `cnt` and must be excluded
from the [features]."* The word **Leakage** is the uploader's, in the column
table, beside the column.

### The same table on UCI

The frozen sieve returns **zero surviving sentences** on the entire UCI 275
record. UCI's own variable descriptions:

| column | role | UCI's description |
|---|---|---|
| `casual` | Other | *"count of casual users"* |
| `registered` | Other | *"count of registered users"* |
| `cnt` | **Target** | *"count of total rental bikes including both casual and registered"* |

UCI **does** state the derivation — *"including both casual and registered"* —
and never says leakage, never says exclude, and phrases it in a form no pattern
in the sieve catches. The role field marks both as `Other` rather than
`Feature`, exactly as it marks cirrhosis's `N_Days`, which corroborates and does
not license.

**Two archives, one table, two columns: documented as leakage in one and not in
the other.** Nothing else in this project separates "what is in the data" from
"what somebody wrote down" so cleanly. The measurement in §4.3 is a measurement
of documentation culture, and this is the control that proves it rather than
asserting it.

### Verified

| check | result |
|---|---|
| `casual + registered == cnt` | **1.000000 on 17,379 rows**, max deviation 0 |

Downstream, RandomForest(200), 5-fold stratified, seed 0, target `cnt > median`:

| arm | F1 |
|---|---|
| keep everything | 0.9953 |
| drop `casual` and `registered` | 0.9274 |
| the two columns alone | **0.9983** |

ΔF1 **0.068** — smaller than ChessFraud's 0.643 because hourly bike demand is
already highly predictable from hour, season and weather. The two columns alone
scoring 0.9983 is the number that matters: they *are* the target, and the modest
delta is a fact about how much honest signal the rest of the table carries, not
about how badly they leak.

### Provenance and caveats

* Provenance `SIEVE` — the frozen sieve fired on the HF card, the anchor
  matched real column names, and the sentence survived the semantic check. It is
  **yield-eligible**, unlike cirrhosis.
* `cnt` is a count, so a classification target requires binarisation. The
  median split above is this project's choice and is stated as one; the
  derivation `casual + registered = cnt` is exact regardless of it.
* The table is UCI-origin, so as with cirrhosis it tests dataset **selection**
  rather than prose culture — except that the leakage annotation is the HF
  uploader's own and exists nowhere in UCI's record, which is precisely the
  point of the section.

---

## 4d. The Hugging Face sweep, complete

Fourth documentation culture: a dataset card is a README written by a model
developer for people who will `load_dataset` the table.

| stage | count |
|---|---|
| datasets indexed (tag filters + the Kaggle query list) | 18,107 |
| cards fetched | 14,420 |
| no README at all | 3,864 |
| surviving sentences | 400 |
| datasets with a surviving sentence | 233 |
| re-uploads of the corpus (excluded) | 2 |
| schema unreadable (**not** counted as "no anchor") | 36 |
| with a readable schema | 195 |
| **anchored to a real column** | **34 (17.4%)** |
| of those: wholly generated | 12 |
| of those: real config with a synthetic sibling — **kept** | 1 |
| **admissible after reading the sentence** | **2** |

Anchoring rate 17.4%, against Kaggle's 20.0%. Registered P2 predicted under
50% and holds in both populations.

**The per-configuration synthetic verdict caught exactly the case it was built
for.** Of the 34 anchors, the pipeline flags 12 as wholly generated and **1 as
scoped** — and the scoped one is `artemlepin/chess-fraud`, configs
`['chess_fraud', 'chess_fraud_synth']`. A per-dataset exclusion would have
dropped the record with the largest downstream effect in the project (§4b). The
mechanism is not hypothetical insurance; it fired once, on the one case that
mattered.

### Why the other 19 non-generated anchors fail

The same five categories as Kaggle (§4), plus two that only appear here:

6. **"Leakage" as a business term.** *"significant revenue leakage"* in a churn
   dataset; *"an alarmingly high baseline churn rate of 56.7%"*.
7. **Leakage as something the uploader already removed.** *"de-duplicated,
   leakage-filtered, and label-balanced"*; *"A second LLM pass audited each
   input for diagnosis leakage"*; two independent re-uploads of `bank_churners`
   both saying *"two model-generated columns were removed to avoid leaking
   predictive information"* — removed, so there is nothing left to flag.

Two were read closely and rejected on substance rather than pattern:

* **`nexar-ai/nexar_collision_prediction`** — `time_to_accident`, *"how much
  time before the event the video was clipped (this column is **not available
  in the training set**)"*. Out of scope twice over: it is a video-folder
  dataset rather than a tabular feature table, and the column is test-set clip
  metadata that cannot leak into training because it does not exist there.
* **`saget-antoine/francecrops`** — `parcel_id` *"should be treated as a
  potential source of label leakage"*. A real warning about a real risk, and an
  identifier, which §2.1 files as a separate category.

### What the two populations say together

| | Kaggle | Hugging Face |
|---|---|---|
| datasets reaching the sieve | 5,032 (58% of sweep) | 14,420 |
| trigger rate | 1.33% | 1.6% |
| anchoring rate | 20.0% | 17.4% |
| **admissible records** | **0** | **2** |

The **trigger** rate is stable across four documentation cultures — archives,
competition uploaders, model developers. The **precision** is not: on archive
prose the surviving sentences are mostly about columns, and everywhere else
they are mostly about markets, fields, soil cores, revenue, and training-set
hygiene. Stratum C's real result is that the scarcity measured in §4.3 is not an
artefact of where we looked.

---

## 4e. The OpenML re-sweep — P2 measured cleanly, in a third population

Not external validation (§1 says why: OpenML built Stratum A and B). This pass
exists because the original one **never fetched column schemas** — it anchored
only the datasets that hit — so the anchoring rate could not be measured. With
`/data/features/{id}` pulled for every description, it can.

| | count |
|---|---|
| descriptions scanned | 6,418 |
| with a machine-readable schema | 5,491 |
| **surviving sentences (WARN \| DEFINE)** | **145 across 101 datasets** |
| mirrors of Stratum A/B (excluded) | 7 |
| **anchored to a real column name** | **30 (29.7%)** |

Two things this settles.

**The 6,420-record denominator re-verifies**, and so does the §1b discrepancy:
145 sentences under the UCI sieve against the 89 `openml_scan.py` reports under
its narrower STRONG filter. The gap is the filter, measured twice now.

**Registered P2 holds in every population measured.** It predicted under half of
surviving sentences would anchor to a named column:

| source | schema available? | anchoring rate |
|---|---|---|
| OpenML | yes, for every dataset | **29.7%** |
| Kaggle | no — required downloading each candidate | 20.0% |
| Hugging Face | yes, via datasets-server | 17.4% |

OpenML anchors highest, which is what having the schema for free should do, and
it is still nowhere near 50%.

### What the 30 OpenML anchors actually are

Overwhelmingly **identifier warnings** — and they are good ones, written by
people being careful:

> `colic`: *"Hospital_Number is an identifier and should be ignored when
> modelling"* · `splice`: *"Instance_name is an identifier and should be ignored
> for modelling"* · `zoo`: *"feature 'animal' is an identifier … should be
> ignored"* · `baseball`: *"Player is an identifier that should be ignored"* ·
> `musk`: *"the molecule_name and conformation_name attributes should not be
> used to predict the class"*

§2.1 files identifier artefacts as a separate category from feature-level target
leakage, so none is admissible here — but their prevalence is itself a result:
**when archive uploaders warn about a column, they are usually warning about an
identifier.** The vocabulary of leakage documentation is dominated by a failure
mode that is not the one this paper measures.

The remainder are the same homonyms and definitional phrases the other two
populations produced: `CIRCULARITY` in the vehicle-silhouette datasets,
`cheating` in the Munich rent index (it abbreviates *central heating*, and it is
a **column name**), `Indicator for the fan actuator`, `1 if any triangles
present`.

One anchor is a near-miss worth naming: `us_crime` (did 315) fires on *"The per
capita violent crimes variable was calculated using population and the sum of
crime variables … murder, rape, robbery, and assault"* — the same sentence that
licenses seventeen Stratum B positives in Communities and Crime. It is the
**normalized** release, a sibling of our unnormalized one, and it slipped past
the content-based mirror check because normalisation renamed the columns. Not
admitted; recorded because it is the closest the mirror filter came to letting a
corpus relative back in.

---

## 5. Cirrhosis (UCI 878) — a hard case the sieve misses

Nominated by hand, not found by the sieve. Recorded with that provenance
because the difference matters for the yield statistics.

### The record

**Dataset**: Cirrhosis Patient Survival Prediction, UCI id 878,
DOI 10.24432/C5R02G. Mayo Clinic PBC trial, 1974–1984. 418 rows, 20 columns.

**Target**: `Status` — C (censored), CL (censored due to liver transplant),
D (death).

**Positive**: `N_Days`, licensed by UCI's own `variable_info`:

> *2. N_Days: number of days between registration and the earlier of death,
> transplantation, or study analysis time in July 1986*

The column's value is an interval whose endpoint is **the target event itself**.
At the natural prediction point — registration — it does not exist. This is the
paper's construct exactly: the triple (`N_Days`, `Status`, registration).

**Mechanism**: TIMING by the definition in §2.2, with a REASON component — the
sentence does not say "do not use this", it says what the number measures, and
the leak follows from reading the definition.

**Independent corroboration**: UCI marks `N_Days` with role `Other`, not
`Feature` — the only non-target column in the dataset so marked. That is role
metadata rather than a leakage statement, so it corroborates and does not
license.

### Verified against the data

Documentation has been contradicted by data once already in this project
(AI4I's `RNF`), so the claim is checked rather than assumed. Random forest,
5-fold stratified, target `Status == D`:

| arm | F1 |
|---|---|
| all columns | 0.771 |
| drop `N_Days` | 0.720 |
| drop `N_Days` and `ID` | 0.703 |

`N_Days` single-column AUC **0.745**, second only to `Bilirubin` (0.788), a
legitimate clinical marker. Dropping it costs **0.051 F1**.

So the leak is **real and moderate**, not catastrophic. Reported as such.

`ID` has AUC 0.676 but costs only 0.003 F1 on its own — an identifier
artefact, which §2.1 excludes from feature-level target leakage as a separate
category. It is **not** coded positive.

### The sieve misses it, and that is the point

The frozen sieve — `explicit_scan`'s WARN and DEFINE, `cond_scan`'s CONDSET —
returns **zero surviving sentences** on the entire UCI 878 record: abstract,
summary, purpose, preprocessing description, variable info, and all twenty
variable descriptions.

It misses because there is nothing to catch. The sentence carries no warning
verb (*should be dropped*, *leaks*), no derivation verb (*computed from*,
*derived from*), and no conditional-assignment pattern. It is a plain
definition by measurement interval. The leak is visible only to a reader who
notices that the interval's endpoint is the outcome — which is REASON-mechanism
inference, the category where models were weakest (62% recall at C1, rising to
81% at C6).

This is the **second documented sieve miss**, after AI4I (§4.3.2). Both point
the same way and the paper should say so plainly: **the sieve measures
documentation, not leakage.** Its yield is a lower bound on how often leakage
exists and a direct measurement only of how often someone writes it down in a
form a regular expression can catch.

### How it is admitted, and how it is not counted

* Provenance: `HAND_NOMINATED / SIEVE_MISS`. It is **excluded from every yield
  denominator**, because a record found by a person looking for it cannot be
  counted in a rate that describes what a sieve finds at random.
* Admission is still source-licensed: UCI's sentence names the column and
  defines its value in terms of the target event. No `INFERRED_FROM_DESCRIPTION`
  reading is involved, so registered construction rule 2 holds.
* It is a **hard case**, and its value is diagnostic: a model that flags
  `N_Days` at C1 is doing the REASON inference the sieve could not.

### First results, and a suspicion that did not survive more data

Eight API-served models, conditions C1 (column names only) and C6 (derivation
clause). HIT means `N_Days` was flagged UNAVAILABLE; `fp` counts how many of
the seventeen negatives were flagged alongside it. Opus and GPT are absent —
they run through the agent loop rather than an HTTP endpoint, so they are a
foreground pass.

| model | C1 | C6 |
|---|---|---|
| moonshotai/Kimi-K3 | **HIT fp=0** | **HIT fp=0** |
| zai-org/GLM-5.2 | **HIT fp=0** | **HIT fp=0** |
| Nexusflow/Athene-V2-Chat | HIT fp=0 | HIT fp=1 |
| mistralai/Mistral-Large-2411 | HIT fp=0 | HIT fp=6 |
| unsloth/Llama-3.3-70B | HIT fp=5 | HIT fp=1 |
| Qwen3-Next-80B-A3B | HIT fp=0 | **miss** fp=1 |
| google/gemma-4-E4B-it | miss fp=0 | miss fp=1 |
| Qwen/Qwen2-72B-Instruct | miss fp=5 | miss fp=5 |

**A retraction, recorded rather than quietly dropped.** On the first two models
this looked like a C1→C6 *regression* — Qwen3-Next found `N_Days` from the bare
column name and lost it once the derivation clause was added — and that would
have contradicted the direction §6.2 reports. Three more models dissolved it:
only Qwen3-Next regressed, two models hit at both conditions, and one improved
its precision from C1 to C6. There is no regression here, and the earlier
suspicion was two data points.

**What does look real, on 8 models, is worth stating carefully.** Six of eight
flag `N_Days` at C1, and five of those do it with **zero false positives** out
of seventeen available. The frozen sieve returns nothing at all on this record
— no warning verb, no derivation verb, nothing a regular expression can catch —
yet most models identify the right column from its name alone. That is the
paper's central claim in miniature, on a table nobody in this project chose,
and it is the reason a one-positive dataset earns its place.

**Two models are exact at both conditions.** Kimi-K3 and GLM-5.2 flag `N_Days`
and nothing else, at C1 and again at C6 — perfect precision and perfect recall
on a record no scanner in this project can reach.

The failures line up with the tier story rather than cutting across it: the two
models that miss at both conditions are gemma-4-E4B and Qwen2-72B, the smallest
and the oldest in the roster, and Qwen2-72B misses *while* flagging five
negatives.

The C6 cost is the other half and it is not uniform: Mistral-Large goes from 0
to **6** false positives when the derivation clause is added, while Llama-3.3
goes the other way, 5 down to 1. Averaged across the eight, C6 neither helps nor
hurts here — which is itself worth reporting, because §6.2's C6 gain is a
pooled result and this is one dataset where it does not appear.

### The memorisation control, on the table most likely to be memorised

This is the Mayo Clinic PBC trial. It ships as `pbc` in R's `survival`
package, it is in most survival-analysis textbooks, and the Kaggle sweep found
**four further copies** of it. If memorisation drives detection anywhere in
this corpus, it drives it here. Every column was renamed to a string-distinct
alias (`N_Days` → `day_total`, target `Status` → `patient_outcome_state`,
dataset shown as `LIVER_TRIAL_COHORT`), and the map passes the C1–C4 checks
with zero violations.

C1, real column names against aliases:

| model | real | aliased |
|---|---|---|
| moonshotai/Kimi-K3 | HIT fp=0 | HIT fp=0 |
| zai-org/GLM-5.2 | HIT fp=0 | HIT fp=0 |
| Qwen3-Next-80B-A3B | HIT fp=0 | HIT fp=0 |
| mistralai/Mistral-Large-2411 | HIT fp=0 | HIT fp=0 |
| google/gemma-4-E4B-it | miss fp=0 | miss fp=0 |
| Qwen/Qwen2-72B-Instruct | miss fp=5 | miss fp=0 |
| unsloth/Llama-3.3-70B | HIT fp=5 | **miss fp=12** |

**Six of seven are unchanged.** Four models that find `N_Days` under its real
name still find `day_total` after every string in the table has been replaced,
with the same zero false positives. On the corpus's most redistributed table,
renaming costs them nothing.

**Llama-3.3-70B is the exception and it fails in the shape a memorised model
should**: HIT becomes miss, and false positives rise from 5 to 12 — it does not
merely lose the answer, it loses its bearings. One model showing a memorisation
signature while six do not is a more useful result than a uniform answer in
either direction, and it is reported per model rather than averaged, because
averaging would hide the only case that carries information.

Three cells failed on the provider rather than the model — Featherless
concurrency limits and one empty completion, while the main sweep was running
against the same keys. They were **not** cached (the runner refuses to store an
empty completion) and are being retried serially. Until they land, GLM-5.2 at
C6 and Athene-V2-Chat in both aliased cells are missing, not negative.

### Registered prediction P9: the downstream test, and five exact hits

P9, written before any dataset was coded: *"dropping what a frontier model
flags at C6 LOWERS F1 relative to keeping everything, and the mean drop is
positive. A negative mean would mean the flags are removing signal rather than
leakage."*

A positive delta is **not a good score** — it is the inflation the leaking
column was supplying, now removed. The quantity that matters is how close a
model's delta lands to the **oracle**, the delta from dropping exactly the coded
positive and nothing else.

RandomForest(300), 5-fold stratified, seed 0, `Status == 'D'`, `ID` dropped as
an identifier artefact:

| arm | F1 | delta |
|---|---|---|
| keep everything | 0.768 | — |
| **oracle** (drop `N_Days`) | **0.703** | **+0.065** |

| model | cond | dropped | F1 | delta | vs oracle |
|---|---|---|---|---|---|
| moonshotai/Kimi-K3 | C1 | 1 | 0.703 | +0.065 | **+0.000** |
| zai-org/GLM-5.2 | C1 | 1 | 0.703 | +0.065 | **+0.000** |
| Nexusflow/Athene-V2-Chat | C1 | 1 | 0.703 | +0.065 | **+0.000** |
| Qwen3-Next-80B-A3B | C1 | 1 | 0.703 | +0.065 | **+0.000** |
| mistralai/Mistral-Large-2411 | C1 | 1 | 0.703 | +0.065 | **+0.000** |
| moonshotai/Kimi-K3 | C6 | 1 | 0.703 | +0.065 | **+0.000** |
| zai-org/GLM-5.2 | C6 | 1 | 0.703 | +0.065 | **+0.000** |
| unsloth/Llama-3.3-70B | C1 | 6 | 0.713 | +0.056 | −0.009 |
| Nexusflow/Athene-V2-Chat | C6 | 2 | 0.714 | +0.054 | −0.011 |
| unsloth/Llama-3.3-70B | C6 | 2 | 0.714 | +0.054 | −0.011 |
| mistralai/Mistral-Large-2411 | C6 | 7 | 0.718 | +0.051 | −0.015 |
| google/gemma-4-E4B-it | C1 | 0 | 0.768 | +0.000 | −0.065 |
| Qwen3-Next-80B-A3B | C6 | 1 | 0.791 | −0.023 | −0.088 |
| google/gemma-4-E4B-it | C6 | 1 | 0.791 | −0.023 | −0.088 |
| Qwen/Qwen2-72B-Instruct | C1 | 5 | 0.795 | −0.027 | −0.092 |
| Qwen/Qwen2-72B-Instruct | C6 | 5 | 0.795 | −0.027 | −0.092 |

**Mean delta +0.036 across 16 model-condition cells, 11 of 16 positive. P9
holds.**

**Seven cells reproduce the oracle exactly.** Five models at C1 drop one column
— `N_Days`, the right one — and land on 0.703 to three decimals, which is the
oracle by construction. Kimi-K3 and GLM-5.2 do it at C6 as well. On a record the
frozen sieve cannot reach at all, five of eight models independently recover
precisely the honest baseline.

**The failures are legible rather than random.** Qwen2-72B drops five columns,
misses `N_Days` among them, and ends *above* the keep-all baseline — it removed
noise while leaving the leak in, which is the worst of both outcomes and the
clearest case in the corpus of a model that is not doing the task. Mistral-Large
at C6 drops seven columns for a delta of +0.051: it beats several models on
delta while discarding six legitimate features, which is exactly why `dropped`
is printed beside every delta and no ranking is offered on delta alone.

### Caveat on where it sits

UCI is the archive Stratum A and B come from, so cirrhosis does **not** test a
different documentation culture — the thing Stratum C was registered to test.
What it does test is **dataset selection**: it is a table this project did not
choose, and it was inside the 689-record sweep the whole time. Treated as
external on selection, not on prose, and labelled that way wherever it appears.
