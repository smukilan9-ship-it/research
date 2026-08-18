"""Freeze the generated tables to disk and expose them as runner bundles.

WHY FREEZE AT ALL

  The generator is deterministic, so the tables could be rebuilt on demand.
  They are written out anyway, because a cell answered against a table that was
  later regenerated slightly differently is a cell scored against ground truth
  it never saw -- the same class of defect as the stale-prompt cache entry that
  moved the paper's C4 figure.  Frozen CSV plus a SHA256 makes that detectable
  instead of invisible.

WHY THEY ARE NOT PUBLISHED YET

  PREREG.md section 3: the novelty guarantee is that these tables have never
  left this machine.  `synth/tables/` is written to `.gitignore` until all
  model runs are complete.  Publishing them before the run would destroy the
  only thing that makes the experiment worth running.

THE BUNDLE CONTRACT

  `bundle(name)` returns the same shape `runner.spec_bundle()` returns, so the
  prompts, the cache keys, the scorer and the coverage audit all treat these
  exactly as they treat Stratum A -- no parallel code path, and therefore no
  chance of the two diverging.
"""
import hashlib
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "tables/"
sys.path.insert(0, HERE)


def freeze():
    from tables import BUILDERS
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    for fn in BUILDERS:
        t = fn()
        d = OUT + t["name"] + "/"
        os.makedirs(d, exist_ok=True)
        t["df"].to_csv(d + "data.csv", index=False)
        meta = dict(name=t["name"], target=t["target"],
                    prediction_point=t["prediction_point"],
                    truth={k: v for k, v in t["truth"].items()},
                    rows=len(t["df"]),
                    columns=[c for c in t["df"].columns if c != t["target"]])
        json.dump(meta, open(d + "meta.json", "w"), indent=1)
        h = hashlib.sha256(open(d + "data.csv", "rb").read()).hexdigest()
        manifest.append(dict(name=t["name"], sha256=h, rows=len(t["df"]),
                             columns=len(meta["columns"]),
                             positives=sum(1 for v in t["truth"].values() if v)))
    json.dump(manifest, open(OUT + "MANIFEST.json", "w"), indent=1)
    return manifest


def available():
    return os.path.isdir(OUT) and os.path.exists(OUT + "MANIFEST.json")


def names():
    if not available():
        return []
    return [r["name"] for r in json.load(open(OUT + "MANIFEST.json"))]


def bundle(name, want_sample=True):
    """runner.spec_bundle-compatible dict for one frozen synthetic table."""
    d = OUT + name + "/"
    meta = json.load(open(d + "meta.json"))
    df = pd.read_csv(d + "data.csv")
    cols = meta["columns"]
    # description is EMPTY on purpose.  C1 and C6 are the only conditions this
    # experiment runs, and neither shows a description; supplying one would
    # make C3 silently runnable on tables whose documentation we invented.
    return dict(
        name=meta["name"],
        columns=cols,
        truth={c: bool(meta["truth"].get(c)) for c in cols},
        subtype={c: meta["truth"].get(c) for c in cols},
        target=meta["target"],
        prediction_point=meta["prediction_point"],
        description="",
        sample=(df[cols].head(5).to_dict("records") if want_sample else []),
    )


def verify_frozen():
    """Re-hash every frozen table against MANIFEST.json."""
    problems = []
    man = json.load(open(OUT + "MANIFEST.json"))
    for r in man:
        p = OUT + r["name"] + "/data.csv"
        if not os.path.exists(p):
            problems.append(f'{r["name"]}: data.csv missing')
            continue
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if h != r["sha256"]:
            problems.append(f'{r["name"]}: sha256 mismatch — the table changed '
                            f'after it was frozen')
    return problems


if __name__ == "__main__":
    m = freeze()
    print(f'froze {len(m)} tables to {OUT}')
    print(f'{"table":<24}{"rows":>7}{"cols":>6}{"pos":>5}  sha256')
    for r in m:
        print(f'{r["name"]:<24}{r["rows"]:>7}{r["columns"]:>6}{r["positives"]:>5}  '
              f'{r["sha256"][:16]}')
    probs = verify_frozen()
    print(f'\nre-hash check: {"clean" if not probs else probs}')
