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
# (name, query_prefix).  e5 and bge were trained with an instruction prefix and
# score materially worse without it; using each encoder the way its authors
# specify is part of not building a strawman.
ENCODERS = [
    ("sentence-transformers/all-MiniLM-L6-v2",   ""),
    ("sentence-transformers/all-mpnet-base-v2",  ""),
    ("BAAI/bge-large-en-v1.5",                   ""),
    ("intfloat/e5-large-v2",                     "query: "),
    ("mixedbread-ai/mxbai-embed-large-v1",       ""),
    ("Qwen/Qwen3-Embedding-0.6B",                ""),
]

# A cross-encoder reads the PAIR jointly instead of embedding each string alone,
# so it is strictly more expressive than any cosine and is the strongest
# non-generative reading available off the shelf.
NLI_MODEL = "MoritzLaurer/deberta-v3-large-zeroshot-v2.0"

# The fine-tuned arm.  Small on purpose: the question is not how well a trained
# encoder fits 40 positives -- it is whether fitting them TRANSFERS.
FT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

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


def run(spec):
    from sentence_transformers import SentenceTransformer
    from sklearn.linear_model import LogisticRegression

    encoder_name, prefix = spec
    model = SentenceTransformer(encoder_name, device="cpu",
                                trust_remote_code=True)
    out = {"encoder": encoder_name}

    A = corpus("A")
    B = corpus("B")
    for tag, rows in (("A", A), ("B", B)):
        cols = [humanise(c) for _, c, _, _ in rows]
        tgts = [humanise(t) for _, _, t, _ in rows]
        y = np.array([p for *_, p in rows])
        C = encode(model, [prefix + c for c in cols])
        T = encode(model, [prefix + t for t in tgts])

        # ---- S1: similarity to the target ---------------------------------
        s1 = (C * T).sum(1)
        f, thr, (p, r, _) = best_threshold(s1, y)
        out[f"S1_{tag}"] = dict(P=p, R=r, F1=f, thr=thr,
                                n=len(rows), pos=int(y.sum()))

        # ---- S3: similarity to a probe ------------------------------------
        best = None
        for probe in PROBES:
            pv = encode(model, [prefix + probe])[0]
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

    # Per dataset, because the Stratum B aggregate hides the whole story: an
    # encoder recovers leaks whose NAMES are semantic neighbours of the target
    # (CRIME's murders/rapes/assaults against violentPerPop) and recovers none
    # whose names are opaque (MI's transliterated abbreviations against ZSN).
    # Those are different findings and averaging them makes one claim out of two.
    clf = LogisticRegression(C=best["C"], max_iter=4000,
                             class_weight="balanced",
                             random_state=SEED).fit(XA, yA)
    pred = clf.predict(XB)
    dsB = [r[0] for r in B]
    per = {}
    for d in sorted(set(dsB)):
        ix = [i for i, x in enumerate(dsB) if x == d]
        pp_, yy_ = pred[ix], yB[ix]
        tp = int((pp_ & yy_).sum()); fp = int((pp_ & ~yy_).sum())
        fn = int((~pp_ & yy_).sum())
        a, b_, c_ = prf(tp, fp, fn)
        per[d] = dict(P=a, R=b_, F1=c_, tp=tp, fp=fp, fn=fn, pos=int(yy_.sum()))
    out["S2_AtoB_per_dataset"] = per
    return out


# ==========================================================================
# S4 -- cross-encoder, zero-shot.  Reads the PAIR.
# ==========================================================================
HYPOTHESES = [
    "This column was used to decide the target.",
    "This column only exists because the outcome already happened.",
    "This column is recorded after the prediction is made.",
    "This column gives away the answer.",
]


def run_nli():
    """Zero-shot entailment with a cross-encoder.

    Every other arm here embeds the column and the target SEPARATELY and then
    compares two vectors.  A cross-encoder attends across both strings at once,
    so it can represent relations a cosine cannot -- "this name is a component
    OF that name" rather than "these names are similar".  It is the strongest
    non-generative reading of the pair available off the shelf, and if the
    finding were about language understanding this is where it should show.

    Best of four hypotheses, threshold swept: an upper bound, as everything
    else here is.
    """
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    torch.manual_seed(SEED)
    tok = AutoTokenizer.from_pretrained(NLI_MODEL)
    mdl = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL).eval()
    ent = 0                                   # entailment index for this model
    for i, lab in (mdl.config.id2label or {}).items():
        if str(lab).lower().startswith("entail"):
            ent = int(i)
    out = {"encoder": NLI_MODEL}
    for tag in ("A", "B"):
        rows = corpus(tag)
        y = np.array([p for *_, p in rows])
        prem = [f"A dataset has the prediction target {humanise(t)}. "
                f"One of its columns is named {humanise(c)}."
                for _, c, t, _ in rows]
        best = None
        for hyp in HYPOTHESES:
            scores = []
            with torch.no_grad():
                for i in range(0, len(prem), 16):
                    batch = tok(prem[i:i + 16], [hyp] * len(prem[i:i + 16]),
                                return_tensors="pt", padding=True,
                                truncation=True, max_length=128)
                    logits = mdl(**batch).logits
                    scores.extend(torch.softmax(logits, -1)[:, ent].tolist())
            f, thr, (pp, rr, _) = best_threshold(np.array(scores), y)
            if best is None or f > best["F1"]:
                best = dict(P=pp, R=rr, F1=f, thr=thr, hypothesis=hyp)
        out[f"S4_{tag}"] = best | dict(n=len(rows), pos=int(y.sum()),
                                       n_hypotheses=len(HYPOTHESES))
    return out


# ==========================================================================
# S5 -- fine-tuned.  The question is not whether it FITS.  It is whether the
#       fit TRANSFERS.
# ==========================================================================
# Swept, because the arm claims every figure is an upper bound and an
# un-swept fine-tune is the one place that claim would have been false.  S5 is
# also the arm that produces the most attackable number, so "you under-trained
# it" is the first thing a reader will say; the grid is the answer.
FT_GRID = [(e, lr) for e in (2, 4, 8) for lr in (3e-5, 1e-4)]


def run_finetune(bs=16):
    """Fine-tune a small encoder on this corpus's labels.

    WHY THIS IS REPORTED WITH A CAVEAT ATTACHED, NOT AS A PEER

    A fine-tuned model and a never-trained reader are not the same kind of
    object, and the comparison only means something if the evaluation makes
    that visible.  So it is evaluated exactly where a trained model is
    vulnerable and a reader is not:

      LODO  leave one DATASET out inside Stratum A.  Twelve fits, each scoring
            a table whose vocabulary it never saw.
      A->B  fit on ALL of Stratum A, test on Stratum B -- a different corpus,
            different domains, different documentation culture.

    Fitting 40 positives is easy and proves nothing; the models in this paper
    were trained on none of them.  If the fine-tuned encoder scores well inside
    Stratum A and collapses on Stratum B, that is not a defect of the
    experiment, it is the measurement.
    """
    import torch
    from torch.utils.data import DataLoader, TensorDataset
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    tok = AutoTokenizer.from_pretrained(FT_MODEL)

    def enc(rows):
        a = [humanise(c) for _, c, _, _ in rows]
        b = [humanise(t) for _, _, t, _ in rows]
        e = tok(a, b, return_tensors="pt", padding="max_length",
                truncation=True, max_length=48)
        y = torch.tensor([int(p) for *_, p in rows])
        return e["input_ids"], e["attention_mask"], y

    def fit(rows, epochs, lr):
        torch.manual_seed(SEED)
        m = AutoModelForSequenceClassification.from_pretrained(
            FT_MODEL, num_labels=2)
        ids, am, y = enc(rows)
        # 11% prevalence: without the weight it learns to answer "legitimate"
        w = torch.tensor([1.0, float((y == 0).sum()) / max(int((y == 1).sum()), 1)])
        opt = torch.optim.AdamW(m.parameters(), lr=lr)
        lossf = torch.nn.CrossEntropyLoss(weight=w)
        dl = DataLoader(TensorDataset(ids, am, y), batch_size=bs, shuffle=True,
                        generator=torch.Generator().manual_seed(SEED))
        m.train()
        for _ in range(epochs):
            for bi, bm, by in dl:
                opt.zero_grad()
                lossf(m(input_ids=bi, attention_mask=bm).logits, by).backward()
                opt.step()
        return m.eval()

    def predict(m, rows):
        ids, am, y = enc(rows)
        with torch.no_grad():
            lg = m(input_ids=ids, attention_mask=am).logits
        return lg.argmax(-1).numpy().astype(bool), y.numpy().astype(bool)

    A, B = corpus("A"), corpus("B")
    out = {"encoder": FT_MODEL + " (fine-tuned)"}
    dsA = sorted({d for d, *_ in A})

    # LODO, best over the grid
    best, seen = None, []
    for epochs, lr in FT_GRID:
        tp = fp = fn = 0
        for d in dsA:
            tr = [r for r in A if r[0] != d]
            te = [r for r in A if r[0] == d]
            pred, yy = predict(fit(tr, epochs, lr), te)
            tp += int((pred & yy).sum()); fp += int((pred & ~yy).sum())
            fn += int((~pred & yy).sum())
        pp, rr, ff = prf(tp, fp, fn)
        seen.append((round(ff, 3), epochs, lr))
        if best is None or ff > best["F1"]:
            best = dict(P=pp, R=rr, F1=ff, epochs=epochs, lr=lr)
    out["S5_LODO"] = best | dict(n=len(A), pos=sum(r[3] for r in A),
                                 folds=len(dsA), grid=len(FT_GRID),
                                 grid_F1=sorted(seen, reverse=True))

    # A -> B, best over the same grid
    best, seen = None, []
    for epochs, lr in FT_GRID:
        pred, yy = predict(fit(A, epochs, lr), B)
        tp = int((pred & yy).sum()); fp = int((pred & ~yy).sum())
        fn = int((~pred & yy).sum())
        pp, rr, ff = prf(tp, fp, fn)
        seen.append((round(ff, 3), epochs, lr))
        if best is None or ff > best["F1"]:
            best = dict(P=pp, R=rr, F1=ff, epochs=epochs, lr=lr)
    out["S5_AtoB"] = best | dict(n=len(B), pos=sum(r[3] for r in B),
                                 grid=len(FT_GRID),
                                 grid_F1=sorted(seen, reverse=True))
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
    for spec in ENCODERS:
        try:
            r = run(spec)
        except Exception as e:
            print(f"--- {spec[0]}\n  UNAVAILABLE: "
                  f"{type(e).__name__}: {str(e)[:90]}\n")
            continue
        results.append(r)
        short = spec[0].split("/")[-1]
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

    for label, fnc in (("cross-encoder (zero-shot)", run_nli),
                       ("fine-tuned", run_finetune)):
        try:
            r = fnc()
        except Exception as e:
            print(f"--- {label}\n  UNAVAILABLE: {type(e).__name__}: "
                  f"{str(e)[:90]}\n")
            continue
        results.append(r)
        print(f"--- {r['encoder'].split('/')[-1]}")
        for k, v in r.items():
            if k in ("encoder", "floor") or not isinstance(v, dict):
                continue
            if "F1" not in v:
                continue
            fl = floors["B" if k.endswith("B") else "A"]
            extra = ""
            if "hypothesis" in v:
                extra = f'  best of {v["n_hypotheses"]}: "{v["hypothesis"]}"'
            if "epochs" in v:
                extra = (f'  best of {v["grid"]}: {v["epochs"]} epochs, '
                     f'lr {v["lr"]:.0e}')
            print(f"  {k:<9} P {v['P']:.3f}  R {v['R']:.3f}  F1 {v['F1']:.3f}"
                  f"  ({v['F1']-fl:+.3f} vs floor){extra}")
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
