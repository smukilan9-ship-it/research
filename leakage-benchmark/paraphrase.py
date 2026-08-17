"""Memorisation control: rename dataset, target and columns to string-distinct aliases.

WHY THIS EXISTS
  A published warning holds that LLMs "may exhibit latent knowledge of public
  tabular datasets when semantic cues such as column names and interpretable
  values are preserved".  Every dataset in this benchmark is public and heavily
  studied.  Without this control we cannot separate semantic reasoning from
  retrieval of a memorised column list.

THE AUTHORING RULE
  Preserve the transparency level.  An opaque acronym maps to a different opaque
  acronym of the same expansion; a transparent word maps to a synonym.
  Expanding `TWF` to `tool_wear_failure` would ADD information the original never
  carried, and a gain under paraphrase would then be uninterpretable.

WHY IT IS CHECKED MECHANICALLY
  The map is authored by the same person who wants the result, on data whose
  answers are known.  Good intentions are not a control.  --check enforces four
  properties that would catch the ways this could be rigged:

    C1  bijective and total          -- no column silently dropped or merged
    C2  every alias differs          -- and does not contain the original
    C3  regex-marker status unchanged -- an alias must not acquire (or lose) a
        hit from the sieve vocabulary the baseline B1 uses.  This is the one
        that matters: renaming `recoveries` to `post_default_receipts` would
        hand the model the answer, and C3 refuses it.
    C4  a shared alias never carries conflicting truth

  C3 is checked in BOTH directions.  Making a positive harder is as much a
  distortion as making it easier; it just flatters a different conclusion.
  It fired twice on the first draft of the map: `discharge_disposition_id` ->
  `release_disposition_code` and `recoveries` -> `regained_amt` both dropped a
  marker, silently making two of the seventeen positives harder than the
  originals and inflating the paraphrase decrement.  Both were rewritten to
  carry a marker from the same vocabulary under a different word.

C2 EXEMPTION
  Twenty-three DIABETES columns are named for a drug (`metformin`, `pioglitazone`).
  A chemical name has no synonym, so the only available paraphrase is a prefix
  and the original survives as a substring.  These are listed explicitly in
  `_substring_exempt` rather than handled by softening C2, so the exemption is
  visible and countable.  They are all negatives, and a drug name is generic
  pharmacology rather than a dataset-specific string, so they are not the
  memorisation risk this control targets.

LIMITATION, STATED
  Domain is deliberately preserved -- a model must still be able to reason about
  what kind of process produced the table, or the semantic task is destroyed
  rather than controlled.  A determined model may therefore re-identify the
  source ("an ocean liner voyage, predicting survival").  This control breaks
  exact-string retrieval; it does not claim to break domain re-identification.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
MAP = json.load(open(HERE + "paraphrase.json"))


def apply_to(bundle):
    """Return a paraphrased copy of a runner.spec_bundle() dict.

    Renames columns, target, sample-row keys and the dataset name together --
    a partial rename would leave the original strings recoverable from the
    sample rows and defeat the control.
    """
    m = MAP.get(bundle["name"])
    if not m:
        raise KeyError(f"no paraphrase map for {bundle['name']}")
    cm = m["columns"]
    missing = [c for c in bundle["columns"] if c not in cm]
    if missing:
        raise KeyError(f"{bundle['name']}: unmapped columns {missing}")
    return dict(
        name=m["dataset"],
        orig_name=bundle["name"],
        columns=[cm[c] for c in bundle["columns"]],
        truth={cm[c]: v for c, v in bundle["truth"].items()},
        alias={cm[c]: c for c in bundle["columns"]},   # for scoring back
        target=m["target"],
        prediction_point=m["prediction_point"],
        description=bundle.get("description", ""),
        sample=[{cm[k]: v for k, v in r.items() if k in cm} for r in bundle["sample"]],
    )


def check():
    """C1-C4.  Returns the number of violations; prints each one."""
    from screen import PAT
    import runner as RN

    bad = 0
    seen = {}
    exempt = {(d, c) for d, cols in MAP.get("_substring_exempt", {}).items()
              for c in cols}
    n_exempt = 0
    for key in RN.ALLSETS:
        b = RN.spec_bundle(key)
        name = b["name"]
        m = MAP.get(name)
        if not m:
            print(f"  C1 FAIL {name}: no map"); bad += 1; continue
        cm = m["columns"]

        # C1 bijective and total
        miss = [c for c in b["columns"] if c not in cm]
        extra = [c for c in cm if c not in b["columns"]]
        if miss:
            print(f"  C1 FAIL {name}: unmapped {miss}"); bad += 1
        if extra:
            print(f"  C1 WARN {name}: map has columns not in data {extra}"); bad += 1
        vals = [cm[c] for c in b["columns"] if c in cm]
        if len(set(vals)) != len(vals):
            dup = [v for v in set(vals) if vals.count(v) > 1]
            print(f"  C1 FAIL {name}: aliases collide {dup}"); bad += 1

        for c in b["columns"]:
            if c not in cm:
                continue
            a = cm[c]
            pos = b["truth"][c]
            tag = "POSITIVE" if pos else "negative"

            # C2 distinct, and not containing the original
            if a == c:
                print(f"  C2 FAIL {name}.{c}: alias identical"); bad += 1
            elif c.lower() in a.lower() and len(c) > 3:
                if (name, c) in exempt:
                    n_exempt += 1
                    if pos:      # an exemption must never shelter a positive
                        print(f"  C2 FAIL {name}.{c}: POSITIVE cannot be exempt")
                        bad += 1
                else:
                    print(f"  C2 FAIL {name}.{c} -> {a}: alias contains original")
                    bad += 1

            # C3 sieve-marker status must not change, either direction
            o_hit = bool(PAT.search(str(c).replace("_", " ")))
            a_hit = bool(PAT.search(str(a).replace("_", " ")))
            if o_hit != a_hit:
                arrow = "GAINED" if a_hit else "LOST"
                print(f"  C3 FAIL {name}.{c} -> {a}: {tag} {arrow} a sieve marker")
                bad += 1

            # C4 a shared alias must not carry conflicting truth.  Sharing
            # itself is fine and realistic -- prompts are independent, and real
            # tables do share column names.  What breaks a per-alias analysis is
            # the same string being a positive in one dataset and a negative in
            # another.
            if a in seen and seen[a][1] != pos:
                print(f"  C4 FAIL alias {a!r}: positive in one dataset "
                      f"({seen[a][0]}) and negative in another ({name})")
                bad += 1
            seen[a] = (name, pos)

        # target and dataset name must also change
        if m["target"] == b["target"]:
            print(f"  C2 FAIL {name}: target unchanged"); bad += 1
        if m["dataset"] == name:
            print(f"  C2 FAIL {name}: dataset name unchanged"); bad += 1

    return bad


if __name__ == "__main__":
    import runner as RN
    n = check()
    total = sum(len(v["columns"]) for k, v in MAP.items() if not k.startswith("_"))
    nds = sum(1 for k in MAP if not k.startswith("_"))
    print(f"\n{total} columns across {nds} datasets checked -> {n} violation(s)")
    if n == 0:
        print("C1 total+bijective  C2 distinct  C3 marker-status preserved  "
              "C4 no truth conflicts")
        print("\npositive columns, original -> alias:")
        for key in RN.ALLSETS:
            b = RN.spec_bundle(key)
            cm = MAP[b["name"]]["columns"]
            for c, v in b["truth"].items():
                if v:
                    print(f"   {b['name']:<10}{c:<26}-> {cm[c]}")
    sys.exit(1 if n else 0)
