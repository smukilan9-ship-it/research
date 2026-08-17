# Draft paper section — Stratum C

*Paper-ready prose distilled from `STRATUM_C.md` (1,012 lines of working
record). Numbers regenerate from `kaggle_sieve.py`, `hf_anchor.py`,
`openml_harvest.py` and `stratc_downstream.py`. Nothing here is settled coding:
ChessFraud's ground truth is deliberately left open (§ below).*

---

## 6.4 Stratum C: does the result depend on where we looked?

Stratum A and B are drawn from two curated archives. Every number in §6
therefore rests on one documentation culture — codebooks written by collectors
for archives with submission standards — and on fifteen tables this project
chose. Stratum C tests both dependencies at once, against three populations
that share no curation process with the archives and were not chosen by us.

**The sieve is frozen throughout.** No pattern was added, removed or tuned for
any population, and no dataset was dropped after a model saw it.

### 6.4.1 What was swept

| population | prose written by | schema exposed? | datasets reaching the sieve |
|---|---|---|---|
| Kaggle datasets | uploaders, in markdown | no | 8,693 of 8,694 indexed |
| Kaggle competitions | hosts, one line | no | 605, complete |
| Hugging Face cards | model developers | yes, via datasets-server | 14,420 |
| OpenML (re-sweep) | archive uploaders | yes, for every dataset | 6,418 |

### 6.4.2 The trigger rate transfers; the precision does not

| | Kaggle | Hugging Face | OpenML |
|---|---|---|---|
| datasets with a surviving sentence | 258 (2.97%) | 233 (1.6%) | 101 (1.6%) |
| — after removing synthetic tables and re-uploads | **130 (1.50%)** | 197 | 101 |
| readable schema, so anchoring is possible at all | 117 | 195 | 101 |
| **anchored to a real column** | 30 (**25.6%**) | 34 (**17.4%**) | 30 (**29.7%**) |
| **admissible after reading the sentence** | **0** | **2** | 0 |

The Kaggle sweep is **complete**: 8,693 of 8,694 indexed datasets enriched, one
unreachable, 1,104 with an empty description. Of its 258 triggering datasets, 87
are synthetic and 61 are detected re-uploads of Stratum A/B — the latter count
being roughly half wrong in the direction of over-exclusion (§6.4.7).

Registered prediction P2 — that fewer than half of surviving sentences would
anchor to a named column — **holds in all three populations**, at 17–30%.

The rate at which the sieve *fires* is broadly stable across four documentation
cultures — **1.5–1.6% after exclusions, against 1.9% of UCI** — though the
comparison is denominator-sensitive and we do not lean on it. UCI's 1.9% was
never filtered for synthetic tables or re-uploads, because UCI has almost none;
compared like for like against Kaggle's unfiltered 2.97%, the sieve fires
*more* readily on uploader prose, not less. Registered prediction P1 asked
which way this would go and the two readings fall on opposite sides of the UCI
rate, so both are reported and neither is preferred. Its **precision**,
however, is unambiguous — and it does not transfer. On archive prose the surviving sentences are mostly about
columns; elsewhere they are about markets, fields, soil cores, revenue,
training-set hygiene, and in one case a paper's acknowledgements section:

> *"must be removed from EU market"* · *"the soil core was removed from the
> field"* · *"items … are removed from the process and inspected"* ·
> *"`deletedOn`: when it was removed from Happyforce"* · *"This data **would not
> be available** without the full collaboration from our customers"*

**Registered prediction P3 fails.** It forecast 2–8 admissible datasets from
Kaggle; the answer is **zero** across all 8,693 enriched datasets. This is reported as a
failed prediction rather than reframed.

### 6.4.3 Leakage needs a target, demonstrated twice

Two Kaggle datasets produced a named column, a stated derivation, and an
explicit instruction to exclude it — and are still not leakage:

* **A&E attendances England**: *"Total attendances: the total of the above."*
  Verified exactly — `Total = Type 1 + Type 2 + Type 3` on all 27,112 rows,
  maximum deviation 0.
* **U.S. Renewable Energy Consumption**: *"You most likely want to exclude the
  column titled `Total Renewable Energy` … it represents the sum of the
  others."*

Both are derivations **among features** in datasets with no designated outcome.
§2.1 defines leakage as a property of the triple (column, target, prediction
point); here two of the three are present and verified, and the absence of the
third makes the whole thing a non-finding. A sieve can locate derivations. Only
a target turns one into leakage.

A related result from the OpenML re-sweep: its 30 anchored sentences are
**overwhelmingly identifier warnings** — `Hospital_Number`, `Instance_name`,
`animal`, `Player`, *"molecule_name and conformation_name should not be used to
predict the class"*. When archive uploaders warn about a column, they are
usually warning about an identifier, which §2.1 files as a separate category.
The vocabulary of leakage documentation is dominated by a failure mode this
paper does not measure.

### 6.4.4 The two admissible records

**ChessFraud** (`artemlepin/chess-fraud`, Hugging Face). A 2026 benchmark for
cheating detection built from 505 controlled online-chess tournament games in
which a plugin showed some players engine lines; 38,510 half-move rows, 33
columns. The card documents five columns as belonging to the cheating apparatus
or to what happened afterwards, including *"`assistance_line_rank`: one-based
rank of the displayed engine line **followed by the player**"* and
*"`is_accused_by_opponent`: whether the opponent accused `player_id` of cheating
**after the game**"*.

`assistance_line_rank` is null on precisely the 29,105 rows where
`is_cheating_move` is false — **agreement 1.000000 across all 38,510 rows**. The
column's missingness alone is the label.

RandomForest(200), 5-fold **grouped by game** so no game spans a split, 20,000
rows at seed 0, 17 numeric features (`chessfraud_downstream.py`):

| arm | F1 | per fold |
|---|---|---|
| keep everything | **1.0000** | 1.000 ×5 |
| drop the five documented columns | **0.3683** | 0.307 – 0.406 |
| `assistance_line_rank` alone | **1.0000** | 1.000 ×5 |

**ΔF1 = 0.632**, the largest downstream effect in the corpus. Being a 2026
dataset, it is also post-cutoff for most of the roster and therefore the only
memorisation control in the paper with nothing to recall.

*Reproducibility note.* An earlier ad-hoc derivation gave 0.3575 for the middle
arm (ΔF1 0.643); it was computed before any script existed and the feature set
was never recorded. The two 1.0000 arms reproduce exactly, and the middle arm
moves by ~0.01 depending on which of ChessFraud's free-text and board-state
columns are admitted — a choice with no single right answer, now stated
explicitly in the script rather than left implicit. **The finding is
insensitive to it**: ΔF1 is 0.63 ± 0.01 under any reasonable encoding, and the
perfect-determinant result does not depend on the model at all.

**Bike Sharing** (`t22000t/bike-sharing-tabular`, Hugging Face; UCI 275
re-hosted). The uploader's feature dictionary reads:

| feature | description |
|---|---|
| `casual` | **Leakage** — non-registered user count (excluded from features) |
| `registered` | **Leakage** — registered user count (excluded from features) |
| `cnt` | **Target** — total rentals (`casual + registered`) |

`casual + registered == cnt` exactly on all 17,379 rows. Dropping the two moves
F1 from 0.9953 to 0.9274; the two alone score 0.9983.

**The same table on UCI produces zero surviving sentences.** UCI's own
descriptions are *"count of casual users"*, *"count of registered users"* and
*"count of total rental bikes including both casual and registered"* — the
derivation is stated, never as a warning, and in a form no pattern catches.

Two archives, one table, two columns: documented as leakage in one and not the
other. This is the cleanest available separation of *what is in the data* from
*what somebody wrote down*, and it is what §4.3's scarcity measurement is
actually measuring.

### 6.4.5 Documented, undetected, and inert — the case that separates three things

**Klaverjas2018** (OpenML 41228) is the record that breaks §4.3's OpenML zero.
Its documentation states plainly that `leaf_count` and `time_real` are
αβ-search metadata that *"should not be used as predictors"*: the number of
nodes the solver expanded, and how long it took, on the very position whose
game-theoretic value is the target. The leak is real and the source names it.

Three things are true of it at once, and they are usually assumed to travel
together:

| | result |
|---|---|
| **documented?** | yes — the source says the columns should not be predictors |
| **detected?** | **no** — 3 of 4 models miss both positives at C1, and 3 of 4 miss at C6; only Mistral-Large finds them, at C6 only |
| **consequential?** | **no** — keep-all F1 0.891, oracle 0.894, **ΔF1 −0.003** |

Dropping the two columns *slightly improves* the model. On a 100,000-row
subsample of an exhaustively solved game, the honest features already determine
the outcome, so search metadata adds nothing a tree cannot get elsewhere.

This is the cleanest evidence in the corpus that **"documented as leakage" and
"consequential leakage" are different properties**, and that a detector's job is
the first, not the second. §4.3 measures how often leakage is written down; §7.5
measures what removing it costs. Klaverjas scores at the extremes of both and in
opposite directions, which is why the two are reported separately throughout and
never combined into a single quality score.

It also tempers §6.4.4. ChessFraud's ΔF1 of 0.632 is what leakage can cost;
Klaverjas's −0.003 is what it can cost instead. Two documented leaks, three
orders of magnitude apart in downstream effect, and the corpus contains both
because the coding follows the source rather than the consequence.

### 6.4.6 A hard case the sieve cannot reach

**Cirrhosis** (UCI 878, Mayo Clinic PBC trial). `N_Days` is documented as *"the
number of days between registration and the earlier of death, transplantation,
or study analysis time"* — an interval whose endpoint is the target event.
Single-column AUC 0.745; dropping it costs 0.051 F1.

The frozen sieve returns **zero** surviving sentences on the entire record: no
warning verb, no derivation verb, nothing a regular expression can catch. It is
a plain definition by measurement interval, and the leak is visible only to a
reader who notices what the interval ends at.

Eight API-served models were run on it at C1 (column names only) and C6
(derivation clause). **Six of eight flag `N_Days` at C1, five of them with zero
false positives out of seventeen**; Kimi-K3 and GLM-5.2 are exact at both
conditions. The two that miss at both are the smallest and the oldest models in
the roster.

Registered prediction **P9 holds**: mean ΔF1 **+0.036** across 16
model-condition cells, 11 of 16 positive, against an oracle delta of +0.065.
**Seven cells reproduce the oracle exactly** — five models at C1 drop one
column, the right one, and land on the honest baseline to three decimals.

The failures are legible. Qwen2-72B drops five columns, misses `N_Days` among
them, and ends *above* the keep-all baseline — it removed noise while leaving
the leak in. Mistral-Large at C6 drops seven columns for a delta of +0.051,
beating several models while discarding six legitimate features, which is why
the number of columns dropped is reported beside every delta and no ranking is
offered on delta alone.

Because it is hand-nominated rather than sieve-found, cirrhosis is **excluded
from every yield denominator** and is reported as a diagnostic case.

### 6.4.7 What Stratum C does and does not establish

It establishes that **§4.3's scarcity is not an artefact of where we looked**:
the sieve fires at the same rate in four documentation cultures and yields
almost nothing admissible in any of them. It establishes that detection
survives on tables this project did not choose, including one the sieve cannot
reach at all.

It does not establish completeness. Legitimate-by-default applies here as
everywhere, so precision remains a lower bound (§4.6). The Kaggle sweep is a
convenience sample of a search API rather than a census, and the queries are
listed in `kaggle_harvest.py` so a reader can see their shape. And two
admissible records cannot carry a pooled F1; they are reported per record, with
the per-column evidence, and not averaged into anything.

**The denominator is a lower bound too.** The Kaggle table above excludes
datasets detected as re-uploads of Stratum A/B, on the ground that a hit on a
re-hosted UCI Bank Marketing is the corpus finding itself rather than an
independent observation. We audited every excluded dataset by hand. The filter
is **19/40 ≈ 48% precise**: it catches verbatim re-uploads reliably — each of
the fifteen datasets matching BANK on 12 or 13 of 13 columns is titled some
variant of *"Bank Marketing"* — and mis-fires in two ways that share a cause.
A rule firing on a corpus table's **target name plus any two columns** excludes
*US Death Rates* and *Global suicide data* as re-uploads of SUPPORT2, whose
target is `death`; a four-column overlap floor excludes a UK property-price
table and a Polish railway-delay table as re-uploads of BANK, whose thirteen
columns are ordinary English words (`duration`, `month`, `day`, `previous`).
Both rules fail on exactly the corpus tables whose vocabulary is least
distinctive.

We report the rate rather than repairing it. The thresholds were fixed before
the sweep, and by the time the audit was run we knew which datasets each one
admits — including one, a railway-delay table warning about *"potential target
leakage if used as an input feature for real-time target prediction"*, that we
would have liked to keep. Moving a threshold at that point is choosing a filter
by its output. The exclusion list is given in full in Appendix G so a reader can
apply their own judgement to it; the effect of ours is that the **"real and
new" population is undercounted**, which makes the scarcity in §4.3 an
underestimate of the population and not an overestimate.

One bug was fixed, because it is not a threshold: the source-name test compared
by plain substring, so `compas` matched the word *"encompass"*. Correcting it to
a token-boundary comparison moved exactly three datasets and changed no other
number.

---

## Open coding question, for the author rather than the reader

ChessFraud has **five candidate positives and they are not equivalent**:

* `assistance_line_rank`, `player_hint_shown`, `assistance_search_depth` are the
  apparatus that produces the label — CONSEQUENCE, unambiguous.
* `is_accused_by_opponent` is post-game. Whether it leaks depends on where the
  prediction point sits; if the task is "given the finished game record, decide
  whether the player cheated", an accusation arrives at roughly the same moment.
  The corpus already carries 2 CONTESTED positives, so there is precedent.
* `is_cheating_player_game` is plausibly a **second target**, not a feature.

Coding it is a choice, not a reading, and on a 0.643-ΔF1 record a self-serving
choice would do more damage than anywhere else in the corpus. It is left open.
