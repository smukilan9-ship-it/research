"""The opaque-name control: strip column-name semantics, keep everything else.

WHY THIS EXISTS

  The paper's premise is that detecting feature-level leakage requires knowing
  what a column *means*, which is why a language model is a plausible
  instrument.  A referee flips that into the obvious attack: **then this is
  column-name classification, not leakage detection.**

  The paraphrase arm (paraphrase.py) does not answer it.  It renames columns
  to string-distinct aliases while PRESERVING transparency level -- that is its
  authoring rule, and it exists to rule out string-keyed recall, not semantic
  reasoning.  `koi_period` -> `tc_orbper` still means orbital period.

  This arm removes the semantics entirely.  Column names become col_1..col_n
  and nothing else changes.

WHAT IS AND IS NOT MASKED

  masked:     every feature column name, and the sample-row keys with them --
              a partial rename leaves the originals recoverable from the sample
  NOT masked: the dataset name, the target, the prediction point, the
              description, and every VALUE

  Only one variable moves.  Masking the target too would make the task nearly
  impossible and the result uninterpretable: with no target, there is nothing
  for a column to leak *about*.

WHY THE NUMBERING IS SHUFFLED

  Assigning col_1..col_n in the source column order would leak position, and
  positions are not random -- outcome-adjacent columns tend to sit at the end
  of a table.  The assignment is a fixed-seed shuffle so the index carries no
  information.

WHAT THIS DOES TO B1

  It zeroes it by construction: the name-regex baseline has no names to match.
  That is the point, not a defect.  The comparison this arm supports is
  model-with-names against model-without-names, not model against B1.

WHY IT CANNOT DISTURB ANY COMMITTED NUMBER

  Cells are recorded under `dataset` = "<NAME>__OPAQUE", which is in no bundle
  set anywhere.  Every existing scorer either filters on membership of a
  dataset list or looks the bundle up by name, so all of them skip these cells
  without a single line changing.  Checked, not assumed -- run the checker
  suite before and after.
"""
import random


def apply_to(bundle, seed=90210):
    """Return an opaque-named copy of a runner.spec_bundle() dict."""
    cols = list(bundle["columns"])
    idx = list(range(1, len(cols) + 1))
    random.Random(seed).shuffle(idx)
    cm = {c: f"col_{i}" for c, i in zip(cols, idx)}
    return dict(
        name=bundle["name"],                       # shown unchanged in the prompt
        orig_name=bundle["name"] + "__OPAQUE",     # recorded, so scorers skip
        columns=[cm[c] for c in cols],
        truth={cm[c]: v for c, v in bundle["truth"].items()},
        subtype={cm[c]: bundle.get("subtype", {}).get(c) for c in cols},
        alias={cm[c]: c for c in cols},            # for scoring back
        target=bundle["target"],
        prediction_point=bundle["prediction_point"],
        description=bundle.get("description", ""),
        sample=[{cm[k]: v for k, v in r.items() if k in cm}
                for r in bundle.get("sample", [])],
    )


def check(bundles):
    """Four properties, mirroring paraphrase.check()'s discipline."""
    bad = []
    for name, b in bundles.items():
        o = apply_to(b)
        if len(set(o["columns"])) != len(b["columns"]):
            bad.append(f"{name}: mapping not bijective")
        if any(c in o["columns"] for c in b["columns"]):
            bad.append(f"{name}: an original name survived")
        if set(o["truth"].values()) != set(b["truth"].values()):
            bad.append(f"{name}: truth values changed")
        for r in o["sample"]:
            if any(not str(k).startswith("col_") for k in r):
                bad.append(f"{name}: sample row leaked an original key")
                break
        if o["orig_name"] == b["name"]:
            bad.append(f"{name}: record key not distinct — would pool with real cells")
    return bad
