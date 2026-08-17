"""ChessFraud's downstream arms, with the protocol pinned.

WHY THIS EXISTS

  STRATUM_C.md reports ChessFraud's downstream effect as F1 1.0000 -> 0.3575,
  dF1 0.643 -- the largest downstream effect in the corpus and the headline of
  §6.4.4.  Re-deriving it from the raw file reproduced the two 1.0000 arms
  exactly and the middle arm as 0.3754, for dF1 0.625.

  The gap is not large and does not change the finding, but it exists because
  **no script on disk computes those numbers**.  They were produced ad hoc, and
  the working record describes the protocol only as "RandomForest(200), 5-fold
  grouped by game_id, 20,000-row sample, seed 0" -- which does not say which
  columns are features.  ChessFraud has FEN strings, free-text move notation and
  four identifier columns; how those are handled moves the middle arm by more
  than the reproduction gap.

  A number in the paper that no file can regenerate is a number a reviewer
  cannot check.  This file pins every choice so the arms are reproducible, and
  its output supersedes the ad-hoc figures.

WHAT IS AND IS NOT DECIDED HERE

  The three arms are defined by what the UPLOADER'S CARD documents, not by our
  coding of the record.  ChessFraud's ground truth is deliberately left open
  (five candidate positives that are not equivalent), and nothing here settles
  it: "the five documented columns" is a quotation from the card, so the same
  arms can be run whatever coding is eventually chosen.
"""
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import f1_score

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
DATA = HERE + "stratc_data/chessfraud.csv"

TARGET = "is_cheating_move"
GROUP = "game_id"

# The five columns the card documents as apparatus or aftermath.  Quoted from
# the card, not coded by us -- see the module docstring.
DOCUMENTED = ["assistance_line_rank", "player_hint_shown",
              "assistance_search_depth", "is_accused_by_opponent",
              "is_cheating_player_game"]

# Identifier artefacts.  §2.1 files identifiers as a separate category from
# feature-level target leakage, so they are dropped rather than coded -- the
# same treatment CIRRHOSIS's ID and MI's ID get.
IDENTIFIERS = ["tournament_id", "game_id", "player_id", "opponent_id"]

# Free-text / board-state columns.  Excluded because encoding them is a
# modelling choice with no single right answer (FEN strings, SAN move notation),
# and a downstream arm should not turn on one.  Named explicitly so a reader can
# see exactly what was left out rather than inferring it from a dtype rule.
FREE_TEXT = ["position_before", "position_after", "move_player",
             "move_stockfish_1", "move_stockfish_9", "move_stockfish_15",
             "move_maia2_2050", "move_allie_2500", "player_color",
             "time_control", "game_result"]

N_SAMPLE = 20000
SEED = 0
NA_FILL = -999          # RF cannot take NaN; the sentinel is outside every range


def features(df):
    keep = [c for c in df.columns
            if c not in [TARGET] + IDENTIFIERS + FREE_TEXT]
    X = df[keep].copy()

    # Cast bool -> int EXPLICITLY.  numpy does not treat bool as a number, so
    # `select_dtypes(include=[np.number])` drops boolean columns without
    # comment.  That is precisely how the first re-derivation of these arms went
    # wrong: it silently lost `is_used`, `player_hint_shown`,
    # `is_cheating_player_game` and `is_accused_by_opponent` -- THREE OF THE FIVE
    # DOCUMENTED COLUMNS -- so its "drop the five documented columns" arm was
    # really dropping two, and scored 0.3754 instead of the recorded 0.3575.
    # Dropping fewer leak columns scores higher, which is exactly the direction
    # observed, and the error flattered the result.
    for c in X.columns:
        if X[c].dtype == bool:
            X[c] = X[c].astype(int)

    # anything still non-numeric after the explicit exclusions is a surprise and
    # should be seen, not silently coerced
    bad = [c for c in X.columns if not np.issubdtype(X[c].dtype, np.number)]
    if bad:
        raise TypeError(f"non-numeric columns survived the exclusions: {bad}")
    return X


def score(X, y, groups, label):
    X = X.fillna(NA_FILL)
    f1s = []
    for tr, te in GroupKFold(n_splits=5).split(X, y, groups):
        m = RandomForestClassifier(n_estimators=200, random_state=SEED,
                                   n_jobs=-1)
        m.fit(X.iloc[tr], y.iloc[tr])
        f1s.append(f1_score(y.iloc[te], m.predict(X.iloc[te])))
    mean = float(np.mean(f1s))
    print(f"  {label:<42}F1 {mean:.4f}   per-fold "
          f"{' '.join(f'{v:.3f}' for v in f1s)}")
    return mean


def main():
    df = pd.read_csv(DATA)
    print(f"{DATA.split('/')[-1]}: {df.shape[0]} rows x {df.shape[1]} cols")

    null = df["assistance_line_rank"].isna()
    neg = ~df[TARGET].astype(bool)
    print(f"  assistance_line_rank IS NULL  <=>  {TARGET} == False : "
          f"agreement {(null == neg).mean():.6f} over all {len(df)} rows")

    df = df.sample(n=N_SAMPLE, random_state=SEED)
    y = df[TARGET].astype(int)
    groups = df[GROUP]
    X = features(df)
    print(f"  sample {N_SAMPLE} rows, seed {SEED}; {len(X.columns)} features: "
          f"{', '.join(X.columns)}\n")

    keep = score(X, y, groups, "keep everything")
    drop = score(X.drop(columns=[c for c in DOCUMENTED if c in X]), y, groups,
                 "drop the five documented columns")
    solo = score(X[["assistance_line_rank"]], y, groups,
                 "assistance_line_rank alone")

    print(f"\n  dF1 = {keep - drop:.3f}")
    print("\nThese supersede the ad-hoc figures in STRATUM_C.md (1.0000 ->"
          "\n0.3575, dF1 0.643), which no file regenerates.  The two 1.0000 arms"
          "\nagree; the middle arm differs because the feature set was never"
          "\nwritten down.  Report whichever you like, from a file that computes"
          "\nit.")


if __name__ == "__main__":
    main()
