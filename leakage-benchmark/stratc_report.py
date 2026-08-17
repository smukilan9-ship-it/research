"""Score Stratum C — both arms, every model, per condition.

WHY THIS IS NOT A ROW IN THE MAIN MODEL TABLE

  Stratum C has one dataset and one positive.  Pooling it into the headline
  would change §6's denominators for no gain and would let a single column
  move a number that fourteen datasets currently support.  It is reported
  beside the frozen result, never inside it, which is the same rule the
  post-hoc sieve extension follows.

WHAT A SINGLE-POSITIVE CELL CAN AND CANNOT SAY

  CANNOT: a pooled F1.  With one positive, recall is 0 or 1 and precision is
  1/(1+however many negatives the model also flagged).  Averaging that across
  models produces a number with the shape of an F1 and none of its stability.

  CAN: whether the positive was found, at which condition, and how many of the
  seventeen negatives were flagged alongside it.  That is what this prints --
  a hit/miss ladder and a false-positive count, not a summary statistic
  pretending the sample supports one.

  The question it exists to answer is narrow and real: does the derivation
  clause (C6) recover a column that the frozen sieve returned zero on?

THE PARAPHRASE ARM IS THE INTERESTING HALF

  This table is the Mayo Clinic PBC trial -- it ships as `pbc` in R's survival
  package and appears in most survival-analysis textbooks.  If anything in this
  project is memorised verbatim, it is this.  A model that finds N_Days under
  its real name and loses it as `day_total` was recalling, not reasoning.
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)

import runner as RN
import verify_paper as VP
import paraphrase as PP

CONDS = [0, 1, 2, 3, 4, 5, 6]


def bundles(para):
    """One bundle per Stratum C dataset, keyed by the JOIN key in the cache.

    That key is `orig_name` for a paraphrased bundle, not the aliased name the
    model saw: runner records `dataset=orig_name` and `shown_as=name`, and
    `cells_for` joins on `dataset`.  Keying on the aliased name instead made the
    entire paraphrase arm report "no responses yet" while 16 cells sat in the
    cache -- the same join bug, in the same direction, that made the paraphrase
    arm score 0.000 the first time it was built.

    Datasets with no paraphrase map are SKIPPED in the aliased arm rather than
    raising: Stratum C grows one dataset at a time and a missing map must not
    take down the report for the datasets that have one."""
    out, skipped = {}, []
    for k in RN.STRATC:
        b = RN.spec_bundle(k)
        if para:
            try:
                b = PP.apply_to(b)
            except KeyError:
                skipped.append(b["name"])
                continue
        out[b.get("orig_name", b["name"])] = b
    return out, skipped


def arm(bs, para):
    """Per-DATASET ladders.

    The first version kept one ladder per model and wrote every dataset's
    verdict into it, so with two Stratum C datasets the second silently
    overwrote the first and the table showed one dataset's numbers under both
    names.  Ladders are keyed by (model, dataset) now."""
    rows = collections.defaultdict(dict)
    models = sorted({json.load(open(f))["model"]
                     for f in glob.glob(HERE + "responses/*.json")})
    for m in models:
        for (d, cond, seed), got in sorted(VP.cells_for(m, para=para).items()):
            b = bs.get(d)
            if b is None:
                continue
            if got and not (set(got) & set(b["truth"])):
                rows[(m, d)][cond] = "JOIN-ERR"
                continue
            pos = [c for c, v in b["truth"].items() if v]
            flagged = {c for c in b["truth"]
                       if got.get(c, {}).get("verdict") == "UNAVAILABLE"}
            hit = sum(1 for c in pos if c in flagged)
            nfp = len(flagged - set(pos))
            tag = "HIT " if hit == len(pos) else (
                f"{hit}/{len(pos)}" if hit else "miss")
            rows[(m, d)][cond] = f"{tag} fp={nfp}"
    return rows


def main():
    for para in (False, True):
        label = "PARAPHRASED (aliased columns)" if para else "REAL column names"
        print(f"\n{'='*72}\nSTRATUM C — {label}")
        bs, skipped = bundles(para)
        if skipped:
            print(f"  no paraphrase map, omitted from this arm: {skipped}")
        rows = arm(bs, para)
        for name, b in bs.items():
            pos = [c for c, v in b["truth"].items() if v]
            nneg = len(b["columns"]) - len(pos)
            sub = {k: v for k, v in rows.items() if k[1] == name}
            # `name` is the JOIN key (the original dataset name); b["name"] is
            # what the model actually saw, which differs in the aliased arm.
            shown = b["name"]
            print(f"\n  {shown}: {len(b['columns'])} columns, {len(pos)} "
                  f"positive {pos}, {nneg} negative, target={b['target']}")
            if not sub:
                print("    no responses yet")
                continue
            cs = sorted({c for l in sub.values() for c in l})
            print(f"    {'model':<42}" + "".join(f"C{c:<11}" for c in cs))
            for (m, _), l in sorted(sub.items()):
                print(f"    {m:<42}"
                      + "".join(f"{l.get(c,'-'):<12}" for c in cs))
    print("\nHIT = every positive flagged UNAVAILABLE; k/n = partial; "
          "fp = negatives also flagged.\nNo pooled F1 is printed: one or two "
          "positives do not support one.")


if __name__ == "__main__":
    main()
