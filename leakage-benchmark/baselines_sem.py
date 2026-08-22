"""S1-S3 -- non-generative SEMANTIC baselines.  Is this an LLM result, or a
language-understanding result?

THE OBJECTION THIS ANSWERS

  Every baseline in section 5 is one of two things: a statistic over VALUES
  (B2 univariate AUC, B3 |correlation|, B4 missingness) or a regular expression
  over NAMES (B1, and B1-tuned with a vocabulary fitted to the answers).  So
  the paper establishes

      language model  >  correlation          and
      language model  >  keyword rule

  and a referee is entitled to ask for the rung in between.  The models read
  column names and a target name; a sentence encoder reads exactly the same
  two strings.  If an encoder gets most of the way there, the finding is about
  language understanding and not about generative models, and the paper should
  say so.  If it does not, the claim that a reader is the right instrument
  stops resting on the absence of an alternative.

  Nothing here is generative.  These are frozen encoders producing vectors.

THREE VARIANTS, BECAUSE "SEMANTIC" MEANS THREE DIFFERENT THINGS

  S1  similarity to the TARGET.  cos(emb(column), emb(target)), thresholded.
      This is B3's idea moved out of value space into meaning space: B3 asks
      whether a column CORRELATES with the outcome, S1 asks whether it MEANS
      something close to the outcome.  ECHO's `still_alive` against a target of
      `alive_at_1` is the case it should find.

  S2  supervised.  Logistic regression on the encoded pair, trained on this
      corpus's own labels.  This is the one that speaks to section 10's claim
      that you cannot assemble a training set at this density -- we have 68
      labels, so we can at least ask what they buy.  Reported two ways, and the
      distinction is the whole point:
        LODO   leave one DATASET out within Stratum A.  Columns inside a table
               are not independent, so leaving out columns would leak the
               table's vocabulary into its own test fold.
        A->B   fit on all of Stratum A, test on Stratum B.  The out-of-sample
               number, and the one comparable with B1-tuned's 0.000.

  S3  similarity to a PROBE.  cos(emb(column), emb("a value recorded after the
      outcome is known")) and friends -- zero-shot, no labels.  Several probes
      are tried and the BEST is reported, which makes it an upper bound in the
      same way B3's swept threshold does.

EVERY THRESHOLD IS SWEPT ON THE ANSWERS

  Exactly as B3's is, and for the same stated reason: a baseline nobody tried to
  make work is a strawman.  So S1 and S3 are UPPER BOUNDS on what a frozen
  encoder achieves, and S2's regularisation strength is swept the same way.
  These numbers are generous to the baseline and therefore conservative for the
  paper's claim.

TWO ENCODERS

  all-MiniLM-L6-v2 and all-mpnet-base-v2 -- the two standard sentence-transformer
  baselines, small and large.  Both are reported so a result is not one model's
  artefact.  They are frozen, downloaded once, and run on CPU.

  This arm is OFF-ROSTER and runs in its own environment (.venv-sem, see
  requirements-semantic.txt).  requirements.txt and the pinned reproduction path
  for every other number in the paper are untouched.

    .venv-sem/bin/python baselines_sem.py
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)

# TWO ENVIRONMENTS, ON PURPOSE.
#
#   --export   runs under the PINNED interpreter (see requirements.txt), imports
#              runner, and writes sem_corpus.json.
#   default    runs under .venv-sem, reads that file, and never imports runner.
#
# The corpus this baseline scores must be the same object every other baseline
# scores, and runner reaches it through pandas -- which the paper REQUIRES at
# version 3, because under pandas 2 two datasets come out empty.  Importing
# runner under a second environment would put that guarantee at the mercy of
# whatever pandas a torch install happened to resolve.  So the pinned stack
# produces the corpus, this file consumes it, and the counts are asserted at
# both ends.
CORPUS = HERE + "sem_corpus.json"
EXPECT = {"A": (306, 40), "B": (298, 28)}      # NUMBERS.txt section 1

SEED = 20260816
ENCODERS = ("sentence-transformers/all-MiniLM-L6-v2",
            "sentence-transformers/all-mpnet-base-v2")

# Zero-shot probes for S3.  Written from section 2.2's mechanism definitions --
# derivation, consequence, timing -- and NOT from looking at which columns leak.
PROBES = [
    "a value that was used to decide the outcome",
    "a value that only exists because the outcome happened",
    "a value recorded after the outcome is known",
    "a column that reveals the answer",
    "information unavailable at prediction time",
]


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def humanise(name):
    """`koi_fpflag_nt` -> `koi fpflag nt`.  An encoder was trained on prose, and
    feeding it snake_case throws away the word boundaries it relies on.  Applied
    identically to every column and every target, so it favours nothing."""
    out = str(name).replace("_", " ").replace("-", " ")
    return " ".join(out.split())


def export():
    """Pinned interpreter only: freeze the corpus both strata are scored on."""
    import runner as RN
    out = {}
    for tag, keys in (("A", RN.ALLSETS), ("B", RN.EXPLICIT)):
        rows = []
        for k in keys:
            b = RN.spec_bundle(k)
            for col, pos in sorted(b["truth"].items()):
                rows.append([b["name"], str(col), str(b["target"]), bool(pos)])
        n, pos = len(rows), sum(r[3] for r in rows)
        want = EXPECT[tag]
        assert (n, pos) == want, (f"Stratum {tag}: corpus has {n}/{pos}, "
                                  f"NUMBERS.txt section 1 says {want[0]}/{want[1]}")
        out[tag] = rows
        print(f"  Stratum {tag}: {n} columns, {pos} positives  ok")
    json.dump(out, open(CORPUS, "w"), indent=1)
    print(f"wrote {os.path.basename(CORPUS)}")


def corpus(tag):
    """(dataset, column, target, is_positive) for one stratum, from the frozen
    export.  Re-asserted here so a stale file cannot be scored silently."""
    if not os.path.exists(CORPUS):
        sys.exit(f"{os.path.basename(CORPUS)} is missing. Run it under the "
                 f"pinned interpreter first:\n"
                 f"    python3 baselines_sem.py --export")
    rows = [tuple(r) for r in json.load(open(CORPUS))[tag]]
    n, pos = len(rows), sum(r[3] for r in rows)
    assert (n, pos) == EXPECT[tag], (f"Stratum {tag}: frozen corpus has "
                                     f"{n}/{pos}, expected {EXPECT[tag]}")
    return rows


def best_threshold(scores, y):
    """Sweep every achievable cut and keep the best F1 -- B3's protocol."""
    best = (0.0, None, (0.0, 0.0, 0.0))
    for t in sorted(set(scores)):
        pred = scores >= t
        tp = int((pred & y).sum()); fp = int((pred & ~y).sum())
        fn = int((~pred & y).sum())
        p, r, f = prf(tp, fp, fn)
        if f > best[0]:
            best = (f, float(t), (p, r, f))
    return best


def encode(model, texts):
    uniq = sorted(set(texts))
    vecs = model.encode(uniq, batch_size=64, show_progress_bar=False,
                        normalize_embeddings=True, convert_to_numpy=True)
    table = {t: v for t, v in zip(uniq, vecs)}
    return np.stack([table[t] for t in texts])


def pair_features(C, T):
    """The standard sentence-pair encoding: both vectors, their absolute
    difference and their elementwise product."""
    return np.hstack([C, T, np.abs(C - T), C * T])


def run(encoder_name):
    from sentence_transformers import SentenceTransformer
    from sklearn.linear_model import LogisticRegression

    model = SentenceTransformer(encoder_name, device="cpu")
    out = {"encoder": encoder_name}

    A = corpus("A")
    B = corpus("B")
    for tag, rows in (("A", A), ("B", B)):
        cols = [humanise(c) for _, c, _, _ in rows]
        tgts = [humanise(t) for _, _, t, _ in rows]
        y = np.array([p for *_, p in rows])
        C, T = encode(model, cols), encode(model, tgts)

        # ---- S1: similarity to the target ---------------------------------
        s1 = (C * T).sum(1)
        f, thr, (p, r, _) = best_threshold(s1, y)
        out[f"S1_{tag}"] = dict(P=p, R=r, F1=f, thr=thr,
                                n=len(rows), pos=int(y.sum()))

        # ---- S3: similarity to a probe ------------------------------------
        best = None
        for probe in PROBES:
            pv = encode(model, [probe])[0]
            f, thr, (p, r, _) = best_threshold(C @ pv, y)
            if best is None or f > best["F1"]:
                best = dict(P=p, R=r, F1=f, thr=thr, probe=probe)
        out[f"S3_{tag}"] = best | dict(n=len(rows), pos=int(y.sum()),
                                       n_probes=len(PROBES))

        if tag == "A":
            XA, yA, dsA = pair_features(C, T), y, [d for d, *_ in rows]
        else:
            XB, yB = pair_features(C, T), y

    # ---- S2 LODO: leave one DATASET out, within Stratum A -----------------
    grid = (0.01, 0.1, 1.0, 10.0)
    best = None
    for Creg in grid:
        pred = np.zeros(len(yA), bool)
        for d in sorted(set(dsA)):
            te = np.array([x == d for x in dsA]); tr = ~te
            if yA[tr].sum() == 0:
                continue
            clf = LogisticRegression(C=Creg, max_iter=4000,
                                     class_weight="balanced",
                                     random_state=SEED).fit(XA[tr], yA[tr])
            pred[te] = clf.predict(XA[te])
        tp = int((pred & yA).sum()); fp = int((pred & ~yA).sum())
        fn = int((~pred & yA).sum())
        p, r, f = prf(tp, fp, fn)
        if best is None or f > best["F1"]:
            best = dict(P=p, R=r, F1=f, C=Creg, folds=len(set(dsA)))
    out["S2_LODO"] = best | dict(n=len(yA), pos=int(yA.sum()))

    # ---- S2 A->B: fit on all of Stratum A, test on Stratum B --------------
    best = None
    for Creg in grid:
        clf = LogisticRegression(C=Creg, max_iter=4000,
                                 class_weight="balanced",
                                 random_state=SEED).fit(XA, yA)
        pred = clf.predict(XB)
        tp = int((pred & yB).sum()); fp = int((pred & ~yB).sum())
        fn = int((~pred & yB).sum())
        p, r, f = prf(tp, fp, fn)
        if best is None or f > best["F1"]:
            best = dict(P=p, R=r, F1=f, C=Creg)
    out["S2_AtoB"] = best | dict(n=len(yB), pos=int(yB.sum()))
    return out


def main():
    print("=" * 78)
    print("SEMANTIC BASELINES -- frozen sentence encoders, nothing generative")
    print("=" * 78)
    print("  Every threshold swept on the answers -> UPPER bounds, as B3 is.")
    print("  FLOOR is B0-with-recall: flag every column.  A swept threshold can")
    print("  always reach it, so a score near the floor is a score near nothing.\n")
    floors = {}
    for tag in ("A", "B"):
        rows = corpus(tag)
        n, pos = len(rows), sum(p for *_, p in rows)
        pr = pos / n
        floors[tag] = 2 * pr / (pr + 1)
        print(f"  Stratum {tag} {n} columns, {pos} positives"
              f"   flag-everything F1 {floors[tag]:.3f}")
    print()

    results = []
    for enc in ENCODERS:
        r = run(enc)
        results.append(r)
        short = enc.split("/")[-1]
        print(f"--- {short}")
        for k in ("S1_A", "S1_B", "S3_A", "S3_B", "S2_LODO", "S2_AtoB"):
            v = r[k]
            extra = ""
            if "probe" in v:
                extra = f'  best of {v["n_probes"]} probes: "{v["probe"]}"'
            if "C" in v:
                extra = f'  C={v["C"]}'
            fl = floors["B" if k.endswith("B") else "A"]
            over = v["F1"] - fl
            print(f"  {k:<9} P {v['P']:.3f}  R {v['R']:.3f}  F1 {v['F1']:.3f}"
                  f"  ({over:+.3f} vs floor){extra}")
        print()

    for r in results:
        r["floor"] = floors
    json.dump(results, open(HERE + "semantic_baselines.json", "w"), indent=1)
    print("wrote semantic_baselines.json")


if __name__ == "__main__":
    if "--export" in sys.argv:
        export()
    else:
        main()
