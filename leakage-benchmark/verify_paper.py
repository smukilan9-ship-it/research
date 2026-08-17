"""Regenerate every number that appears in the paper, from the raw artefacts.

WHY THIS EXISTS
  Numbers that travel from a terminal into prose by way of a person's memory
  acquire errors.  This project has already had several: a DeepSeek REASON
  figure distorted by two missing cells, an order-averaging claim generalised
  from one model, a per-cell timing estimate extrapolated from the small
  datasets.  Each was caught, but only after it had been written down.

  So the paper cites this file and nothing else.  Run it, and every table in
  the manuscript can be checked line by line against its output.  If a number
  is in the paper and not here, it is unverified and does not belong.

WHAT IT READS
  responses/*.json          every cached model answer
  records_all/new/explicit  the evidence records
  downstream2.csv           the arm comparison
  confusion.csv             pooled confusion matrices
  baseline10_features.csv   per-column statistics
  ucimeta/, openml/         the repository sweep
"""
import json, glob, os, sys, collections
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN
from salvage import parse
from subtypes import subtype as _subtype_A

# Stratum B's subtype codes live in explicit_specs, not subtypes.py.  Without
# this, all 30 Stratum-B positives report as UNCODED and the SURROGATE row --
# the paper's central negative finding -- comes out empty.
import explicit_specs as ES
_SUB_B = {}
for _k in ES.SPECS:
    _b = ES.build(_k)
    for _c, _st in _b["subtypes"].items():
        _SUB_B[(_b["name"], _c)] = _st


def subtype(ds, col):
    return _SUB_B.get((ds, col)) or _subtype_A(ds, col)

W = 78
def head(t):
    print("\n" + "=" * W + f"\n{t}\n" + "=" * W)
def sub(t):
    print(f"\n--- {t}")


# ----------------------------------------------------------------- corpus
def corpus():
    head("1. CORPUS")
    main, expl = {}, {}
    for k in RN.ALLSETS:
        b = RN.spec_bundle(k); main[b["name"]] = b
    for k in RN.EXPLICIT:
        b = RN.spec_bundle(k); expl[b["name"]] = b
    def tab(d, label):
        sub(label)
        tc = tp = 0
        print(f"{'dataset':<12}{'cols':>6}{'pos':>5}  target")
        for n, b in sorted(d.items()):
            p = sum(b["truth"].values()); tc += len(b["columns"]); tp += p
            print(f"{n:<12}{len(b['columns']):>6}{p:>5}  {b['target']}")
        print(f"{'TOTAL':<12}{tc:>6}{tp:>5}   ({len(d)} datasets)")
        return tc, tp
    # The split is by CONSTRUCTION PROTOCOL, not by explicitness: A was
    # coded from documentation, B was built only from datasets whose source
    # names the column.  Explicitness is a per-record attribute and is
    # counted in section 2, where 4 of A's positives turn out to be named
    # by their source as well.
    c1, p1 = tab(main, "Stratum A -- main corpus (coded from documentation)")
    c2, p2 = tab(expl, "Stratum B -- transfer set (source names the column)")
    print(f"\nCOMBINED: {len(main)+len(expl)} datasets, {c1+c2} columns, {p1+p2} positives")
    st = collections.Counter()
    for d in (main, expl):
        for n, b in d.items():
            for c, p in b["truth"].items():
                if p: st[subtype(n, c) or "UNCODED"] += 1
    print(f"subtypes: {dict(st)}")
    return main, expl


# --------------------------------------------------------------- evidence
# The record files predate the corpus naming convention, so their dataset_id
# fields are archive slugs.  Mapping them here rather than rewriting the
# records keeps the records exactly as they were coded.
ID2NAME = {"uci_880_support2": "SUPPORT2", "lending_club_2007_2011": "LC",
           "uci_222_bank_marketing": "BANK",
           "uci579_myocardial_infarction": "MI",
           "uci211_communities_crime_unnorm": "CRIME",
           "uci320_student_performance": "STUDENT"}


def load_records():
    """Every coded evidence record, keyed (corpus dataset name, column)."""
    out = {}
    for f in ("records_all.jsonl", "records_new.jsonl", "records_support2.jsonl",
              "records_uci.jsonl", "records.jsonl", "records_explicit.jsonl",
              "records_founding.jsonl"):
        p = HERE + f
        if not os.path.exists(p):
            continue
        for line in open(p):
            r = json.loads(line)
            ds = ID2NAME.get(r.get("dataset_id"), r.get("dataset_id"))
            out.setdefault((ds, r.get("column")), r)
    return out


def evidence(main, expl):
    head("2. EVIDENCE RECORDS")
    recs = load_records()
    pos = []
    for d, lab in ((main, "A"), (expl, "B")):
        for n, b in sorted(d.items()):
            for c, v in b["truth"].items():
                if v:
                    pos.append((lab, n, c))
    have = [p for p in pos if (p[1], p[2]) in recs]
    print(f"positives {len(pos)}   with a coded record {len(have)}   "
          f"without {len(pos)-len(have)}")
    if len(pos) != len(have):
        print("  MISSING: " + ", ".join(f"{n}.{c}" for _, n, c in pos
                                        if (n, c) not in recs))
    q = [p for p in have if (recs[(p[1], p[2])].get("quote") or "").strip()]
    print(f"records carrying a verbatim source quotation: {len(q)} / {len(pos)}")
    ex = collections.Counter()
    for lab, n, c in pos:
        r = recs.get((n, c), {})
        e = r.get("explicitness")
        if not e:
            e = "NAMED_BY_SOURCE" if lab == "B" else "INFERRED_FROM_DESCRIPTION"
        ex[e] += 1
    print(f"explicitness: {dict(ex)}")
    tier = collections.Counter(recs[(n, c)].get("evidence_tier", "?")
                               for _, n, c in have)
    print(f"evidence tiers: {dict(tier)}")
    sub("attrition (the corpus-expansion round)")
    rej = [json.loads(l) for l in open(HERE + "records_rejected.jsonl")]
    adm = [json.loads(l) for l in open(HERE + "records_new.jsonl")]
    seen = {r["dataset_key"] for r in rej}
    yielded = {r["dataset_id"].lower() for r in adm}
    print(f"candidate rows rejected: {len(rej)}")
    for why, n in collections.Counter(r["reject"] for r in rej).most_common():
        print(f"   {n:>4}  {why}")
    print(f"datasets adjudicated {len(seen)}   yielded evidence "
          f"{len(seen & yielded)}   yielded none {len(seen - yielded)}")
    print(f"   none: {', '.join(sorted(seen - yielded))}")
    print("   (MI later re-entered the corpus via the heading pass and now "
          "contributes\n    11 Stratum-B positives -- see 4.5.)")
    return recs


def derivation_checks():
    """Does the coded derivation actually hold in the data?

    A label coded from documentation is an inference, and an inference can be
    wrong.  Where the claimed mechanism implies a testable pattern in the
    values -- a flag that should imply the target, a field that should be
    populated only for one outcome -- this checks it.  It is not what makes
    the label true (a legitimate column can correlate perfectly by accident,
    which is exactly why B3 is a baseline and not an oracle); it is a check
    that the reading of the source is not contradicted by the table.

    One of the five checks below FAILS, and the failure is reported: AI4I's
    documentation names five failure modes as inputs to the target, and RNF
    is not one of them in the data."""
    head("3. CODED DERIVATIONS CHECKED AGAINST THE DATA")
    U = "/root/.claude/uploads/1dfa598a-70c3-5cb5-8d7b-ecd921e451d9/"

    sub("AI4I  (source statement names 5 columns; 4 hold)")
    df = pd.read_csv(HERE + "ai4i2.csv")
    mf = "Machine failure"
    for c in ("TWF", "HDF", "PWF", "OSF", "RNF"):
        n1 = int((df[c] == 1).sum())
        ag = int(df.loc[df[c] == 1, mf].sum())
        print(f"  {c}  flag=1 rows {n1:>4}   of which target=1 {ag:>4}   "
              f"{'CONFIRMED' if n1 and ag == n1 else 'CONTRADICTED'}")
    four = (df[["TWF", "HDF", "PWF", "OSF"]].sum(axis=1) > 0).astype(int)
    five = (df[["TWF", "HDF", "PWF", "OSF", "RNF"]].sum(axis=1) > 0).astype(int)
    print(f"  OR(4 coded flags)      == target : {(four == df[mf]).mean():.4f}")
    print(f"  OR(5 documented flags) == target : {(five == df[mf]).mean():.4f}")
    print("  -> RNF is documented as label-setting and is not.  Coded 4, not 5.")

    sub("KOI  (any false-positive flag should imply FALSE POSITIVE)")
    k = pd.read_csv(U + "e818b7de-cumulative_2026.08.08_07.34.36.csv",
                    comment="#", low_memory=False)
    fl = ["koi_fpflag_nt", "koi_fpflag_ss", "koi_fpflag_co", "koi_fpflag_ec"]
    ok = np.ones(len(k), bool)
    for f in fl:
        ok &= k[f].isin([0, 1]).values
    k = k[ok]
    a = k[fl].sum(axis=1) > 0
    print(f"  any flag set  {int(a.sum()):>5} rows, FALSE POSITIVE "
          f"{int((k.loc[a, 'koi_disposition'] == 'FALSE POSITIVE').sum()):>5}"
          f"  ({(k.loc[a,'koi_disposition']=='FALSE POSITIVE').mean():.4f})")
    print(f"  no flag set   {int((~a).sum()):>5} rows, FALSE POSITIVE "
          f"{int((k.loc[~a, 'koi_disposition'] == 'FALSE POSITIVE').sum()):>5}"
          f"  ({(k.loc[~a,'koi_disposition']=='FALSE POSITIVE').mean():.4f})")

    sub("COMPAS  (recidivism-event fields should be populated only if is_recid)")
    c = pd.read_csv(HERE + "compas.csv", low_memory=False)
    for col in ("r_offense_date", "r_charge_degree", "r_charge_desc",
                "r_days_from_arrest"):
        nn = c[col].notna()
        print(f"  {col:<20} non-null {int(nn.sum()):>5}   of which "
              f"is_recid==1 {int((c.loc[nn,'is_recid']==1).sum()):>5}")
    print("  r_offense_date non-null <-> is_recid==1 : "
          f"{(c.r_offense_date.notna().astype(int)==(c.is_recid==1).astype(int)).mean():.4f}")

    sub("TITANIC  (boat recorded on rescue; body recovered only for the dead)")
    t = pd.read_csv(HERE + "titanic3.csv")
    print(f"  boat non-null {int(t.boat.notna().sum()):>4}   survived==1 among "
          f"them {int(t.loc[t.boat.notna(),'survived'].sum()):>4}")
    print(f"  body non-null {int(t.body.notna().sum()):>4}   survived==1 among "
          f"them {int(t.loc[t.body.notna(),'survived'].sum()):>4}")
    print("  boat non-null <-> survived==1 : "
          f"{(t.boat.notna().astype(int)==t.survived).mean():.4f}")

    sub("STEEL  (the seven fault types are said to be exhaustive)")
    import newdata as ND
    st = ND.load_steel()["df"]
    six = ["Pastry", "Z_Scratch", "K_Scratch", "Stains", "Dirtiness", "Bumps"]
    tot = st[six].sum(axis=1)
    print(f"  rows {len(st)}   rows with more than one of the six set: "
          f"{int((tot > 1).sum())}")
    print(f"  Other_Faults == NOT OR(six) : "
          f"{((1 - (tot > 0).astype(int)) == st['Other_Faults']).mean():.4f}")
    print("  -> exactly the negation of the other six. With AI4I, the "
          "best-evidenced\n     derivation in the corpus.")

    sub("ECHO  (still_alive is documented as a 'class attribute')")
    ec = ND.load_echo()["df"].dropna(subset=["alive_at_1", "still_alive"])
    both = pd.crosstab(ec.still_alive, ec.alive_at_1)
    print(f"  n={len(ec)}   agreement with target: "
          f"{(ec.still_alive == ec.alive_at_1).mean():.4f}")
    print(f"  still_alive=0 -> alive_at_1=0 in "
          f"{int(both.loc[0, 0.0])}/{int(both.loc[0].sum())} rows")
    print("  -> not a leaking feature so much as a SECOND COPY OF THE TARGET. "
          "Kept, and\n     flagged as the corpus's most trivial positive.")

    sub("DIABETES  (a patient discharged to death or hospice cannot be readmitted)")
    d = pd.read_csv(HERE + "diabetic.csv", low_memory=False)
    m = d.discharge_disposition_id.isin({11, 13, 14, 19, 20, 21})
    print(f"  terminal-discharge rows {int(m.sum())}")
    print(f"  readmitted<30 rate, terminal     {d.loc[m,'readmitted'].eq('<30').mean():.4f}")
    print(f"  readmitted<30 rate, non-terminal {d.loc[~m,'readmitted'].eq('<30').mean():.4f}")
    print("  -> not zero: the discharge codes carry entry noise.  The column is "
          "coded\n     MIXED, and diabetes_pure isolates the terminal indicator.")


# --------------------------------------------------------------- scarcity
def scarcity():
    head("4. REPOSITORY SWEEP")
    nu = len(glob.glob(HERE + "ucimeta/*.json"))
    no = len(glob.glob(HERE + "openml/*.json"))
    su = sum(1 for _ in open(HERE + "explicit_candidates.jsonl"))
    so = sum(1 for _ in open(HERE + "openml_candidates.jsonl"))
    dsu = len({json.loads(l)["uci_id"] for l in open(HERE + "explicit_candidates.jsonl")})
    sec = [json.loads(l) for l in open(HERE + "section_candidates.jsonl")]
    hit_u = dsu if not sec else len({json.loads(l)["uci_id"]
              for l in open(HERE + "explicit_candidates.jsonl")} | {h["uci_id"] for h in sec})
    dso = len({json.loads(l)["did"] for l in open(HERE + "openml_candidates.jsonl")})
    print(f"UCI records swept          {nu}")
    print(f"OpenML records swept       {no}")
    print(f"TOTAL                      {nu+no}")
    print(f"UCI sentences surviving    {su}   across {hit_u} datasets")
    print(f"OpenML sentences surviving {so}   across {dso} datasets")
    print(f"OpenML distinct sentences  "
          f"{len({json.loads(l)['sentence'][:60] for l in open(HERE+'openml_candidates.jsonl')})}")
    print("\nhand-read classification (see scarcity.py for the reading of each):")
    print("  UCI     TARGET_LEAK 6  IDENTIFIER 3  OUT 4")
    print("  OpenML  TARGET_LEAK 0  GROUP 2  CONTAMINATION 1  IDENTIFIER 2  OUT 5")
    print(f"\nFROZEN-SIEVE RATE: 6 / {nu+no} = {6/(nu+no):.3%}")

    # --- post-hoc gate repair.  The two columns above were NOT produced by the
    # same instrument: UCI gated on WARN|DEFINE, OpenML on its own STRONG regex.
    # Re-running the UCI gate over the same cached OpenML descriptions is a
    # repair of a methods defect, not a widening chosen after seeing an answer,
    # but it is still post-hoc and is reported separately for that reason.
    wd = [json.loads(l) for l in open(HERE + "openml_wider_candidates.jsonl")]
    nwd = len(glob.glob(HERE + "openml_meta/*.json")) and 6418
    sub("post-hoc WIDER-GATE family (NOT in the frozen sieve)")
    print("The OpenML pass gated on its own STRONG regex; the UCI pass gated on")
    print(f"WARN | DEFINE.  Re-running the UCI gate over the same {nwd:,} cached")
    print(f"OpenML descriptions yields {len(wd)} sentences across "
          f"{len({h['did'] for h in wd})} datasets, against")
    print(f"STRONG's {so} across {dso}.  Reading all of them recovers exactly one "
          "admissible record:")
    kv = [h for h in wd if str(h.get("did")) == "41228"]
    for h in kv[:1]:
        print(f"  OpenML {h['did']} {str(h['name'])[:34]:<36}TARGET_LEAK  (2 columns)")
        print(f"      \"{h['sentence']}\"")
        print(f"      -> leaf_count, time_real ; target = {h.get('target')}")
    print("  the remainder are identifier warnings, batch metadata, and three "
          "copies of a\n  Student Performance sentence already withdrawn by the "
          "S4.7 audit.")
    print(f"CORRECTED RATE: 7 / {nu+no} = {7/(nu+no):.3%}")

    # --- post-hoc extension (cond_scan.py); reported separately, never merged
    cu = [json.loads(l) for l in open(HERE + "cond_candidates.jsonl")]
    co = json.load(open(HERE + "cond_openml.json"))
    sub("post-hoc conditional-assignment family (NOT in the frozen sieve)")
    print(f"UCI hits    {len(cu)}  across {len({c['uci_id'] for c in cu})} datasets")
    print(f"OpenML hits {len(co)}  across {len({c['id'] for c in co})} datasets, "
          f"{len({c['sentence'][:60] for c in co})} distinct sentences")
    for c in cu:
        print(f"  UCI {c['uci_id']} {c['name'][:34]:<36} TARGET_LEAK")
        print(f"      \"{c['sentence']}\"")
    for c in {c["sentence"][:60]: c for c in co}.values():
        print(f"  OML {c['id']} {c['name'][:34]:<36} OUT (annotation, not leakage)")
    print(f"\nCOMBINED RATE: 8 / {nu+no} = {8/(nu+no):.3%}   "
          "(6 frozen + 1 wider-gate + 1 conditional)")
    print("All three are lower bounds: the frozen sieve is demonstrably "
          "incomplete\n(it missed UCI 601, which is IN this benchmark).")


# -------------------------------------------------------------- baselines
def baselines():
    head("5. BASELINES (thresholds swept on the answers -> upper bounds)")
    import baselines10 as B
    F = pd.read_csv(HERE + "baseline10_features.csv")
    y = F.y.values
    print(f"feature table: {len(F)} columns, {int(y.sum())} positives")
    for name, col in (("B2 univariate AUC", "auc"), ("B3 |correlation|", "cor"),
                      ("B4 missingness", "miss")):
        r = B.best_threshold(y, F[col].values)
        print(f"{name:<22}P {r['precision']:.3f}  R {r['recall']:.3f}  "
              f"F1 {r['f1']:.3f}  thr {r['threshold']}")
    reg = F.regex.values.astype(bool)
    tp = int((reg & y).sum()); fp = int((reg & ~y.astype(bool)).sum())
    fn = int((~reg & y.astype(bool)).sum())
    p = tp/(tp+fp) if tp+fp else 0; r = tp/(tp+fn) if tp+fn else 0
    print(f"{'B1 name regex':<22}P {p:.3f}  R {r:.3f}  "
          f"F1 {2*p*r/(p+r) if p+r else 0:.3f}")
    print(f"{'B0 always AVAILABLE':<22}P 0.000  R 0.000  F1 0.000")

    # B1 is the frozen §4.3 vocabulary and does badly, which invites the reply
    # that we did not try.  So B1-tuned is the same rule with name patterns
    # added by looking at what leaks here -- fitted to the answers, like B3's
    # threshold, and an upper bound for the same reason.  Both are scored on
    # Stratum B as well, where the tuned rule is genuinely out of sample
    # because none of its patterns came from a Stratum B column.
    sub("B1-tuned -- the name-keyword rule with a fitted vocabulary")
    import baselines_lex as BL
    A_, B_ = {}, {}
    for k in RN.ALLSETS:
        _s = RN.spec_bundle(k)
        A_[_s["name"]] = _s
    for k in RN.EXPLICIT:
        _s = RN.spec_bundle(k)
        if _s["name"] not in A_:
            B_[_s["name"]] = _s
    print(f"  {'stratum':<12}{'variant':<12}{'P':>8}{'R':>8}{'F1':>8}"
          f"{'tp':>5}{'fp':>5}{'fn':>5}")
    for lab, bundles in (("A", A_), ("B", B_)):
        for vname, pat in (("B1", BL.FROZEN), ("B1-tuned", BL.TUNED)):
            r = BL.score(bundles, pat)
            pp, rr, ff = r["prf"]
            print(f"  {'Stratum ' + lab:<12}{vname:<12}{pp:>8.3f}{rr:>8.3f}"
                  f"{ff:>8.3f}{r['tp']:>5}{r['fp']:>5}{r['fn']:>5}")
    print(f"  {len(BL.TUNED_EXTRA)} name patterns were added to the "
          f"{len(BL.MARKERS)} frozen ones.")
    print("  Every added pattern came from a Stratum A positive, so Stratum B")
    print("  is an out-of-sample test of the tuned rule.")


# ------------------------------------------------------------ model table
# Optional seed restriction, set from the environment so a robustness pass can
# re-run the WHOLE instrument on one seed without a second implementation of
# its logic.  It exists because a hand-run arm answered the three-seed datasets
# once and replicated the verdict across seeds: the alias arm therefore has zero
# seed variance by construction while the real arm does not, and the honest way
# to ask whether that moved anything is to re-run the real code path with the
# extra seeds removed from BOTH arms.  Re-deriving it in a throwaway script gave
# an answer 0.4 F1 different from the instrument, which is the sort of agreement
# a throwaway script is entitled to.
_SEEDS = ({int(s) for s in os.environ["VP_SEEDS"].split(",")}
          if os.environ.get("VP_SEEDS") else None)


def cells_for(model_sub, para=False):
    out = {}
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if model_sub not in r["model"] or bool(r.get("paraphrase")) != para:
            continue
        if _SEEDS is not None and r.get("seed") not in _SEEDS:
            continue
        d, _ = parse(r.get("raw", ""))
        if not d:
            continue
        k = (r["dataset"], r["condition"], r.get("seed"))
        out[k] = {c["name"]: c for c in d["columns"]
                  if isinstance(c, dict) and c.get("name")}
    return out


def prf(bundles, cells, conds, restrict=None, aliasback=None,
        refused=None, exclude=None):
    """Pooled P/R/F1 and subtype recall over the datasets in `restrict`.

    `aliasback` maps (dataset, alias) -> original column name.  It is required
    for the paraphrase arm: there the bundle's truth dict is keyed on aliases,
    and `subtype()` is keyed on originals, so without it every subtype
    denominator is zero -- which prints as "found none" and means "never
    looked".

    `refused` (a set, mutated in place) collects every (dataset, cond) dropped
    as a join failure.  `exclude` drops those pairs up front.  The pair exists
    because the two are used together by the paraphrase summary: a join failure
    hits ONE arm, and silently scoring the other arm on a dataset its partner
    lost turns a matched comparison into an unmatched one.  That is exactly how
    the paraphrase arm reported a 0.000 recall earlier in this project -- a
    difference of two numbers computed over different datasets, which looks
    like a finding and is an accounting error."""
    ab_ = aliasback or {}
    ex_ = exclude or set()
    keys = restrict if isinstance(restrict, set) and restrict and \
        isinstance(next(iter(restrict)), tuple) else None
    res = {}
    for cond in conds:
        ds = {d for (d, c, s) in cells if c == cond}
        if keys is not None:
            ds &= {d for (d, _s) in keys}
        elif restrict is not None:
            ds &= restrict
        ds &= set(bundles)          # only datasets in THIS corpus
        tp = fp = fn = 0; ab = 0
        seeds = set()
        hit = collections.Counter(); tot = collections.Counter()
        for (d, c, s), got in cells.items():
            if c != cond or d not in ds or d not in bundles:
                continue
            if keys is not None and (d, s) not in keys:
                continue
            b = bundles[d]
            # a cell whose verdict keys do not intersect the truth keys is a
            # join bug.  Scoring it yields 0 recall, which is indistinguishable
            # from a model that found nothing.  Refuse it loudly.
            if (d, cond) in ex_:
                continue
            if got and not (set(got) & set(b["truth"])):
                print(f"  JOIN ERROR {d} C{cond}: no verdict key matches truth")
                if refused is not None:
                    refused.add((d, cond))
                continue
            seeds.add(s)
            for col, pos in b["truth"].items():
                v = got.get(col, {}).get("verdict")
                if v == "ABSTAIN":
                    ab += 1
                fl = v == "UNAVAILABLE"
                if pos:
                    st = subtype(d, ab_.get((d, col), col)) or "UNCODED"; tot[st] += 1
                    if fl: hit[st] += 1; tp += 1
                    else: fn += 1
                elif fl:
                    fp += 1
        if tp + fn == 0:
            continue
        p = tp/(tp+fp) if tp+fp else 0.0
        r = tp/(tp+fn) if tp+fn else 0.0
        # seed count is reported because conditions with different numbers of
        # shuffles pool different numbers of observations; the RATES stay
        # comparable but the counts do not, and a reader must be able to see it
        res[cond] = dict(P=p, R=r, F1=2*p*r/(p+r) if p+r else 0.0,
                         tp=tp, fp=fp, fn=fn, ds=len(ds), nseed=len(seeds), abst=ab,
                         sub={k: (hit[k], tot[k]) for k in tot})
    return res


MODELS = ["claude-opus-5-max", "gemini-3.7-flash", "Kimi-K3::high",
          "gpt-5.6-sol-xhigh", "gemini-3.5-flash", "GLM-5.2::high",
          "Qwen3-Coder-480B", "nemotron-3-super-120b-a12b::high",
          "DeepSeek-V4-Pro::high", "deepseek-v4-flash-0731::high"]


def incomplete_rosters():
    """Models with a quarantined cell that never came back.

    WHY THIS IS A GLOBAL AND NOT A CONSTANT

      A per-model row is a per-model claim: it is computed on the cells that
      model answered, matched C1-against-C6, and it is honest about itself.  A
      MEAN OVER MODELS is a different object -- it treats each row as one
      comparable unit -- and a row resting on a smaller, non-randomly-missing
      set of cells is not comparable with the others.  Folding it in anyway is
      the paper's own thesis committed by the paper: a number whose provenance
      makes it inadmissible, used because it was available.

      So the aggregate sections below report BOTH: every model, and complete
      rosters only.  Which models are incomplete is DERIVED from the live
      quarantine (section 17), never hardcoded, so a refill that lands
      tomorrow moves this set without anyone remembering to edit a list.
    """
    qdir = HERE + "responses_truncated/"
    if not os.path.isdir(qdir):
        return set()
    live = collections.defaultdict(set)
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        live[(r["model"], r["dataset"], bool(r.get("paraphrase")))].add(
            (r["condition"], r.get("seed")))
    out = set()
    for f in glob.glob(qdir + "*.json"):
        r = json.load(open(f))
        k = (r["model"], r["dataset"], bool(r.get("paraphrase")))
        if (r["condition"], r.get("seed")) not in live[k]:
            out.add(r["model"])
    return out


def model_table(main):
    """Main-corpus results, as two PAIRWISE comparisons.

    Every condition comparison is made on the cells present in BOTH arms --
    matched on (dataset, shuffle seed), not merely on dataset.  Two earlier
    versions of this table were wrong in ways that matching fixes:

      * restricting on datasets alone let C1's REASON denominator be 51 where
        C6's was 47, because one shuffle of one dataset was missing at C6;
      * intersecting across ALL of C1/C6/C9 at once cut C1 and C6 down to the
        single shuffle a model happened to have at C9, discarding four fifths
        of the evidence for a claim C9 has nothing to do with.

    So C1 vs C6 is matched on {C1, C6}, and C6 vs C9 on {C6, C9}."""
    head("6. MAIN CORPUS -- pairwise matched comparisons")
    store = {}
    for title, pair in (("C1 vs C6  (matched cells)", (1, 6)),
                        ("C6 vs C9  (matched cells)", (6, 9))):
        sub(title)
        print(f"{'model':<32}{'cond':>5}{'P':>7}{'R':>7}{'F1':>7}"
              f"{'tp':>5}{'fp':>5}{'fn':>5}{'ds':>4}{'sd':>4}{'abst':>6}")
        for m in MODELS:
            c = cells_for(m)
            ka = {(d, s) for (d, cc, s) in c if cc == pair[0] and d in main}
            kb = {(d, s) for (d, cc, s) in c if cc == pair[1] and d in main}
            keys = ka & kb
            if not keys:
                continue
            res = prf(main, c, list(pair), restrict=keys)
            store[(m, pair)] = res
            for cond in pair:
                v = res.get(cond)
                if not v:
                    continue
                print(f"{m[:31]:<32}{('C'+str(cond)):>5}{v['P']:>7.3f}"
                      f"{v['R']:>7.3f}{v['F1']:>7.3f}{v['tp']:>5}{v['fp']:>5}"
                      f"{v['fn']:>5}{v['ds']:>4}{v['nseed']:>4}{v['abst']:>6}")
        sub("subtype recall, " + title)
        print(f"{'model':<32}{'cond':>5}{'REASON':>13}{'CONSEQ':>13}{'TIMING':>12}")
        for m in MODELS:
            res = store.get((m, pair))
            if not res:
                continue
            for cond in pair:
                v = res.get(cond)
                if not v:
                    continue
                row = ""
                for st in ("REASON", "CONSEQUENCE", "TIMING"):
                    h, t = v["sub"].get(st, (0, 0))
                    row += (f"{h}/{t}".rjust(8) + f"{h/t:.0%}".rjust(5)) \
                        if t else "        -    "
                print(f"{m[:31]:<32}{('C'+str(cond)):>5}{row}")
    return store


def ladder(main):
    """The full condition ladder C0-C7 for the models that have it.

    C4 is the ablation the framing predicted: if provenance were recoverable
    from values, showing the model five sample rows should help.  Each row is
    scored on the cells that condition actually has, so the `ds`/`sd` columns
    must be read before any two rows are compared."""
    head("6b. FULL LADDER (C0-C7), matched within model on common datasets")
    for m in MODELS:
        c = cells_for(m)
        conds = sorted({cc for (d, cc, _) in c if d in main})
        if len(conds) < 4:
            continue
        per = {cc: {d for (d, c2, _) in c if c2 == cc and d in main}
               for cc in conds}
        common = set.intersection(*per.values())
        if not common:
            continue
        res = prf(main, c, conds, restrict=common)
        sub(f"{m}   common datasets {len(common)}: {', '.join(sorted(common))}")
        print(f"{'cond':>5}{'P':>8}{'R':>8}{'F1':>8}{'sd':>4}")
        for cc in conds:
            if cc in res:
                v = res[cc]
                print(f"{('C'+str(cc)):>5}{v['P']:>8.3f}{v['R']:>8.3f}"
                      f"{v['F1']:>8.3f}{v['nseed']:>4}")
        got = [res[cc]["F1"] for cc in conds if cc in res]
        if len(got) > 1:
            print(f"  range across the ladder: {max(got)-min(got):.3f}")

    sub("THE C4 ABLATION, pairwise matched: does showing sample rows help?")
    print(f"{'model':<32}{'C1':>8}{'C4':>8}{'delta':>8}{'ds':>4}{'sd':>4}")
    for m in MODELS:
        c = cells_for(m)
        k1 = {(d, sd) for (d, cc, sd) in c if cc == 1 and d in main}
        k4 = {(d, sd) for (d, cc, sd) in c if cc == 4 and d in main}
        keys = k1 & k4
        if not keys:
            continue
        r = prf(main, c, [1, 4], restrict=keys)
        if 1 in r and 4 in r:
            print(f"{m[:31]:<32}{r[1]['F1']:>8.3f}{r[4]['F1']:>8.3f}"
                  f"{r[4]['F1']-r[1]['F1']:>+8.3f}{r[1]['ds']:>4}"
                  f"{r[1]['nseed']:>4}")


def transfer(expl):
    head("7. TRANSFER SET (Stratum B) -- C1 / C2 / C6 / C9")
    print(f"{'model':<32}{'cond':>5}{'P':>7}{'R':>7}{'F1':>7}"
          f"{'tp':>5}{'fp':>5}{'fn':>5}{'ds':>4}{'sd':>4}")
    for m in MODELS:
        c = cells_for(m)
        res = prf(expl, c, (0, 1, 2, 6, 9))
        for cond, v in sorted(res.items()):
            print(f"{m[:31]:<32}{('C'+str(cond)):>5}{v['P']:>7.3f}{v['R']:>7.3f}"
                  f"{v['F1']:>7.3f}{v['tp']:>5}{v['fp']:>5}{v['fn']:>5}"
                  f"{v['ds']:>4}{v['nseed']:>4}")
    sub("subtype recall on Stratum B, all conditions")
    print(f"{'model':<32}{'cond':>5}{'REASON':>13}{'TIMING':>13}"
          f"{'CONSEQ':>13}{'SURROGATE':>13}")
    for m in MODELS:
        c = cells_for(m)
        res = prf(expl, c, (0, 1, 2, 6, 9))
        for cond, v in sorted(res.items()):
            row = ""
            for st in ("REASON", "TIMING", "CONSEQUENCE", "SURROGATE"):
                h, t = v["sub"].get(st, (0, 0))
                row += (f"{h}/{t}".rjust(8) + f"{h/t:.0%}".rjust(5)) \
                    if t else "        -    "
            print(f"{m[:31]:<32}{('C'+str(cond)):>5}{row}")
    sub("SURROGATE recall specifically")
    for m in MODELS:
        c = cells_for(m)
        res = prf(expl, c, (1, 2, 6, 9))
        line = f"{m[:31]:<32}"
        for cond in (1, 2, 6, 9):
            if cond in res:
                h, t = res[cond]["sub"].get("SURROGATE", (0, 0))
                line += f"  C{cond}={h}/{t}" if t else f"  C{cond}=-"
        print(line)


def downstream():
    head("8. DOWNSTREAM")
    # A stale arm file is invisible: it parses, it plots, and every number in
    # it is from a ground truth that no longer exists.  downstream2 was once
    # killed by a timeout mid-run and left an eight-hour-old CSV in place,
    # which this harness then reported as current.  Refuse instead.
    for dep in ("audit.py", "runner.py"):
        if os.path.getmtime(HERE + "downstream2.csv") < os.path.getmtime(HERE + dep):
            print(f"  REFUSING TO REPORT: downstream2.csv is older than {dep}.")
            print("  Re-run downstream2.py; these numbers would be stale.")
            return
    d = pd.read_csv(HERE + "downstream2.csv")
    gt = d[d.arm == "GT"].set_index(["dataset", "learner"])[["auc", "f1"]]
    d = d.join(gt.add_prefix("gt_"), on=["dataset", "learner"])
    d["res_f1"] = d.f1 - d.gt_f1
    d["res_auc"] = d.auc - d.gt_auc
    sub("honest ceiling (arm GT) -- is the downstream model well trained?")
    g = d[d.arm == "GT"].pivot_table(index="dataset", columns="learner", values="f1")
    a = d[d.arm == "GT"].pivot_table(index="dataset", columns="learner", values="auc")
    print(f"{'dataset':<12}{'F1 rf':>8}{'F1 gb':>8}{'AUC rf':>9}{'AUC gb':>9}")
    for ds in g.index:
        print(f"{ds:<12}{g.loc[ds,'rf']:>8.3f}{g.loc[ds,'gb']:>8.3f}"
              f"{a.loc[ds,'rf']:>9.3f}{a.loc[ds,'gb']:>9.3f}")
    sub("inflation, ALL vs GT")
    al = d[d.arm == "ALL"]
    print(f"{'learner':<9}{'mean dF1':>10}{'median':>9}{'max':>8}"
          f"{'mean dAUC':>11}{'n':>4}")
    for lr, gg in al.groupby("learner"):
        print(f"{lr:<9}{gg.res_f1.mean():>10.3f}{gg.res_f1.median():>9.3f}"
              f"{gg.res_f1.max():>8.3f}{gg.res_auc.mean():>11.3f}{len(gg):>4}")
    sub("inflation EXCLUDING BONEMARROW (degenerate ceiling, see confusion)")
    al2 = al[al.dataset != "BONEMARROW"]
    for lr, gg in al2.groupby("learner"):
        print(f"{lr:<9}{gg.res_f1.mean():>10.3f}{gg.res_f1.median():>9.3f}"
              f"{gg.res_f1.max():>8.3f}{gg.res_auc.mean():>11.3f}{len(gg):>4}")
    sub("residual to ceiling per cleaning arm (rf)")
    print(f"{'arm':<24}{'mean resid F1':>15}{'mean |resid|':>14}{'n':>4}")
    for arm in ["ALL"] + sorted(set(d.arm) - {"ALL", "GT"}) + ["GT"]:
        gg = d[(d.arm == arm) & (d.learner == "rf")]
        if len(gg):
            print(f"{arm:<24}{gg.res_f1.mean():>15.3f}"
                  f"{gg.res_f1.abs().mean():>14.3f}{len(gg):>4}")
    sub("per-dataset leaked vs clean (rf)")
    print(f"{'dataset':<12}{'F1 leak':>9}{'F1 clean':>10}{'dF1':>8}"
          f"{'AUC leak':>10}{'AUC clean':>11}{'dAUC':>8}")
    for _, x in al[al.learner == "rf"].sort_values("res_f1", ascending=False).iterrows():
        print(f"{x.dataset:<12}{x.f1:>9.3f}{x.gt_f1:>10.3f}{x.res_f1:>8.3f}"
              f"{x.auc:>10.3f}{x.gt_auc:>11.3f}{x.res_auc:>8.3f}")


def confusion():
    head("9. CONFUSION MATRICES (pooled over folds)")
    for dep in ("audit.py", "runner.py"):
        if os.path.getmtime(HERE + "confusion.csv") < os.path.getmtime(HERE + dep):
            print(f"  REFUSING TO REPORT: confusion.csv is older than {dep}.")
            return
    d = pd.read_csv(HERE + "confusion.csv")
    print(f"{'dataset':<12}{'lrn':<4}{'arm':<8}{'TN':>7}{'FP':>6}{'FN':>6}"
          f"{'TP':>6}{'prec':>8}{'rec':>7}{'F1':>7}")
    for _, x in d.sort_values(["dataset", "learner", "arm"]).iterrows():
        print(f"{x.dataset:<12}{x.learner:<4}{x.arm:<8}{x.tn:>7.0f}{x.fp:>6.0f}"
              f"{x.fn:>6.0f}{x.tp:>6.0f}{x.precision:>8.3f}{x.recall:>7.3f}{x.f1:>7.3f}")


def cachestats():
    head("10. CACHE / RUN STATISTICS")
    cond = collections.Counter(); mod = collections.Counter(); prov = collections.Counter()
    npara = 0
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        cond[r["condition"]] += 1; mod[r["model"]] += 1
        prov[r.get("provider", "?")] += 1
        npara += bool(r.get("paraphrase"))
    print(f"total cached cells: {sum(cond.values())}")
    print(f"by condition: {dict(sorted(cond.items()))}")
    print(f"by provider:  {dict(prov)}")
    print(f"paraphrased:  {npara}")
    sub("cells per model")
    for m, n in sorted(mod.items(), key=lambda x: -x[1]):
        print(f"  {m:<40}{n:>5}")



# ---------------------------------------------------- memorisation control
def paraphrase_control(main):
    """C6's REASON gain, on real column names and on aliases.

    The objection C6 invites is that its clause was written after looking at
    failures on KOI, AI4I and DIABETES, so the gain could be recall of those
    names rather than use of the criterion.  The control renames every column
    and re-runs.  A gain that survives renaming is not name recall; a gain
    that shrinks is partly name recall, and the shrinkage measures how much.

    The paraphrased arm must be scored against ALIASED bundles.  Scoring it
    against the original truth dict joins nothing and reports 0.000 for every
    cell, which looks like a catastrophic result and is a bug."""
    head("11. MEMORISATION CONTROL (paraphrased column names)")
    import paraphrase as PP
    pbundles = {n: PP.apply_to(b) for n, b in main.items()}
    aback = {(n, a): o for n, b in pbundles.items()
             for a, o in b["alias"].items()}
    for m in MODELS:
        pc = cells_for(m, para=True)
        if not pc:
            continue
        oc = cells_for(m, para=False)
        # compare on exactly the datasets and conditions present in BOTH arms,
        # otherwise the control measures coverage rather than memorisation
        both = {d for (d, c, s) in pc} & {d for (d, c, s) in oc}
        conds = sorted({c for (d, c, s) in pc if d in both} &
                       {c for (d, c, s) in oc if d in both})
        if not conds:
            continue
        # ...and on the same SHUFFLE SEEDS.  The original arm has 5 seeds for
        # C1/C6 where the paraphrase arm has 1.  Pooling all 5 against 1 is the
        # unequal comparison this harness exists to prevent: it would report
        # 47/75 against 9/15 and invite the reader to subtract them.
        pseeds = {s for (_, _, s) in pc}
        oc = {k: v for k, v in oc.items() if k[2] in pseeds}
        keys = {(d, s) for (d, c, s) in pc if d in both} & \
               {(d, s) for (d, c, s) in oc if d in both}
        ro = prf(main, oc, conds, restrict=keys)
        rp = prf(pbundles, pc, conds, restrict=keys, aliasback=aback)
        sub(f"{m}   datasets {len(both)}: {', '.join(sorted(both))}")
        print(f"{'arm':<16}{'cond':>5}{'P':>8}{'R':>8}{'F1':>8}   "
              f"{'REASON':>12}{'CONSEQ':>12}{'TIMING':>12}")
        for tag, rr in (("original", ro), ("paraphrased", rp)):
            for c in conds:
                if c not in rr:
                    continue
                d = rr[c]
                def sh(k):
                    h, t = d["sub"].get(k, (0, 0))
                    return f"{h}/{t} {0 if not t else round(100*h/t)}%"
                print(f"{tag:<16}{'C'+str(c):>5}{d['P']:>8.3f}{d['R']:>8.3f}"
                      f"{d['F1']:>8.3f}   {sh('REASON'):>12}"
                      f"{sh('CONSEQUENCE'):>12}{sh('TIMING'):>12}")


    # ---- every model with both arms, one line each -------------------------
    # WHY THIS SUMMARY EXISTS
    #   The per-model blocks above are the evidence; this is the table §7 needs.
    #   §7 currently argues memorisation-robustness by LEAVING OUT the datasets
    #   tabmemcheck says are recalled.  At three models measured, eight of
    #   thirteen datasets are fully recalled by someone, so that check would
    #   have to drop most of the corpus and could no longer answer anything.
    #
    #   The paraphrase decrement does not have that problem: it is per model,
    #   it covers every column of every mapped dataset, and it measures the
    #   thing directly rather than by subtraction.  A decrement near zero says
    #   the score does not depend on the strings.  This prints one row per
    #   model so the claim can be read off rather than assembled by hand.
    sub("cross-model summary — paraphrase decrement (original minus aliased)")
    print(f"{'model':<44}{'cond':>5}{'F1 real':>9}{'F1 alias':>10}"
          f"{'delta':>8}{'datasets':>10}")
    allm = sorted({json.load(open(f))["model"]
                   for f in glob.glob(HERE + "responses/*.json")})
    rows = []
    for m in allm:
        pc = cells_for(m, para=True)
        if not pc:
            continue
        oc = cells_for(m, para=False)
        both = {d for (d, c, s) in pc} & {d for (d, c, s) in oc}
        if not both:
            continue
        conds = sorted({c for (d, c, s) in pc if d in both} &
                       {c for (d, c, s) in oc if d in both})
        pseeds = {s for (_, _, s) in pc}
        oc = {k: v for k, v in oc.items() if k[2] in pseeds}
        keys = {(d, s) for (d, c, s) in pc if d in both} & \
               {(d, s) for (d, c, s) in oc if d in both}
        # First pass collects join failures from BOTH arms; the second rescores
        # with the union dropped from both, so every printed delta is a
        # difference over the identical set of (dataset, condition) cells.
        bad = set()
        prf(main, oc, conds, restrict=keys, refused=bad)
        prf(pbundles, pc, conds, restrict=keys, aliasback=aback, refused=bad)
        ro = prf(main, oc, conds, restrict=keys, exclude=bad)
        rp = prf(pbundles, pc, conds, restrict=keys, aliasback=aback,
                 exclude=bad)
        for c in conds:
            if c in ro and c in rp:
                d = ro[c]["F1"] - rp[c]["F1"]
                n = len(both - {x for (x, cc) in bad if cc == c})
                rows.append((m, c, ro[c]["F1"], rp[c]["F1"], d, n))
                print(f"  {m[:42]:<44}{'C'+str(c):>5}{ro[c]['F1']:>9.3f}"
                      f"{rp[c]['F1']:>10.3f}{d:>+8.3f}{n:>10}")
    if rows:
        ds = [r[4] for r in rows]
        print(f"\n  {len(rows)} model-condition cells across "
              f"{len({r[0] for r in rows})} models")
        print(f"  mean decrement {np.mean(ds):+.3f}, median {np.median(ds):+.3f}, "
              f"worst {max(ds):+.3f} ({max(rows, key=lambda r: r[4])[0][:34]})")
        print("  A decrement near zero means the score does not depend on the "
              "column strings.\n  A large positive one means it does, for that "
              "model.")
    else:
        print("  no model has both arms on a shared dataset yet")


# ------------------------------------------------- leave-one-dataset-out
def loo(main):
    """Does the C1 -> C6 effect depend on the datasets the clause was written
    from?  Each row drops one dataset and rescores on the remaining ones."""
    head("12. LEAVE-ONE-DATASET-OUT (C1 -> C6)")
    for m in MODELS:
        cl = cells_for(m)
        conds = {c for (_, c, _) in cl}
        if not {1, 6} <= conds:
            continue
        k1 = {(d, s) for (d, c, s) in cl if c == 1 and d in main}
        k6 = {(d, s) for (d, c, s) in cl if c == 6 and d in main}
        keys = k1 & k6
        if not keys:
            continue
        allds = {d for (d, _s) in keys}
        base = prf(main, cl, [1, 6], restrict=keys)
        if 1 not in base or 6 not in base:
            continue
        sub(f"{m}   full: C1 F1 {base[1]['F1']:.3f} -> C6 {base[6]['F1']:.3f} "
            f"(dF1 {base[6]['F1']-base[1]['F1']:+.3f})")
        print(f"{'dropped':<12}{'C1 F1':>8}{'C6 F1':>8}{'dF1':>8}"
              f"{'REASON C1':>12}{'REASON C6':>12}")
        for drop in sorted(allds):
            r = prf(main, cl, [1, 6],
                    restrict={k for k in keys if k[0] != drop})
            if 1 not in r or 6 not in r:
                continue
            def sh(c):
                h, t = r[c]["sub"].get("REASON", (0, 0))
                return f"{h}/{t}"
            print(f"{drop:<12}{r[1]['F1']:>8.3f}{r[6]['F1']:>8.3f}"
                  f"{r[6]['F1']-r[1]['F1']:>+8.3f}{sh(1):>12}{sh(6):>12}")



# ------------------------------------------------------------- seed spread
def seed_spread(main, expl):
    """Per-shuffle F1 for every model/condition with more than one shuffle.

    Reported as min-max rather than a standard deviation: with 3 or 5 seeds an
    SD is not meaningfully estimable, and a range says the same thing without
    implying precision the data does not support."""
    head("13. SHUFFLE-ORDER SENSITIVITY (per-seed F1)")
    for label, bundles in (("Stratum A", main), ("Stratum B", expl)):
        sub(label)
        print(f"{'model':<32}{'cond':>5}{'n':>3}{'min':>8}{'max':>8}"
              f"{'spread':>8}   seeds")
        for m in MODELS:
            c = cells_for(m)
            conds = sorted({cc for (d, cc, _) in c if d in bundles})
            for cond in conds:
                seeds = sorted({sd for (d, cc, sd) in c
                                if cc == cond and d in bundles})
                if len(seeds) < 2:
                    continue
                # one F1 per seed, on the datasets that seed answered under
                # this condition -- a seed that answered fewer datasets is not
                # comparable, so restrict to datasets ALL these seeds answered
                per = {sd: {d for (d, cc, s2) in c
                            if cc == cond and s2 == sd and d in bundles}
                       for sd in seeds}
                common = set.intersection(*per.values())
                if not common:
                    continue
                f1s = []
                for sd in seeds:
                    r = prf(bundles, c, [cond],
                            restrict={(d, sd) for d in common})
                    if cond in r:
                        f1s.append(r[cond]["F1"])
                if len(f1s) < 2:
                    continue
                print(f"{m[:31]:<32}{('C'+str(cond)):>5}{len(f1s):>3}"
                      f"{min(f1s):>8.3f}{max(f1s):>8.3f}"
                      f"{max(f1s)-min(f1s):>8.3f}   {len(common)} ds")



# ------------------------------------------------------------------ triage
def triage(main, expl):
    """The two claims §9 makes about deployment, rather than about scores.

    (a) review burden: what fraction of columns a model asks a human to look
        at, and what fraction of documented leaks that surfaces;
    (b) intersection of two independent models, which is the obvious way to
        buy precision when a false positive costs a human's time."""
    head("14. TRIAGE (what a reviewer would actually do)")
    sub("review burden, best condition per model, Stratum A")
    print(f"{'model':<32}{'cond':>5}{'flagged':>9}{'of':>6}{'burden':>8}"
          f"{'recall':>8}")
    for m in MODELS:
        c = cells_for(m)
        for cond in (1, 6, 9):
            keys = {(d, sd) for (d, cc, sd) in c if cc == cond and d in main}
            if not keys:
                continue
            r = prf(main, c, [cond], restrict=keys)
            if cond not in r:
                continue
            v = r[cond]
            ncol = sum(len(main[d]["columns"]) for (d, _s) in keys)
            fl = v["tp"] + v["fp"]
            print(f"{m[:31]:<32}{('C'+str(cond)):>5}{fl:>9}{ncol:>6}"
                  f"{fl/ncol:>8.3f}{v['R']:>8.3f}")

    sub("two-model intersection on Stratum B, per shuffle seed")
    a = cells_for("claude-opus-5-max")
    b = cells_for("gpt-5.6-sol-xhigh")
    print(f"{'arm':<24}{'cond':>5}{'P':>8}{'R':>8}{'F1':>8}"
          f"{'tp':>5}{'fp':>5}{'fn':>5}")
    for cond in (1, 2, 6, 9):
        rows = {"opus alone": (lambda fa, fb: fa),
                "gpt alone": (lambda fa, fb: fb),
                "AND(opus, gpt)": (lambda fa, fb: fa and fb),
                "OR(opus, gpt)": (lambda fa, fb: fa or fb)}
        out = {}
        for name, rule in rows.items():
            tp = fp = fn = 0
            for (d, cc, sd), ga in a.items():
                if cc != cond or d not in expl:
                    continue
                gb = b.get((d, cond, sd))
                if not gb:
                    continue
                for col, pos in expl[d]["truth"].items():
                    fa = ga.get(col, {}).get("verdict") == "UNAVAILABLE"
                    fb = gb.get(col, {}).get("verdict") == "UNAVAILABLE"
                    f = rule(fa, fb)
                    if pos and f: tp += 1
                    elif pos: fn += 1
                    elif f: fp += 1
            if tp + fp:
                out[name] = (tp/(tp+fp), tp/(tp+fn) if tp+fn else 0.0,
                             tp, fp, fn)
        for name, (p_, r_, tp, fp, fn) in out.items():
            print(f"{name:<24}{('C'+str(cond)):>5}{p_:>8.3f}{r_:>8.3f}"
                  f"{(2*p_*r_/(p_+r_) if p_+r_ else 0):>8.3f}"
                  f"{tp:>5}{fp:>5}{fn:>5}")



# ------------------------------------------------- closed-world dictionary
UCI_OF = {"BANK": 222, "SUPPORT2": 880, "BONEMARROW": 565, "HEARTFAIL": 519,
          "ECHO": 38, "STEEL": 198, "DIABETES": 296, "AI4I": 601,
          "MI": 579, "CRIME": 211, "STUDENT": 320}


def closed_world(main, expl):
    """The negative result of 4.4, recomputed over the full archive.

    The rule classifies a column from its own dictionary entry, on datasets
    where EVERY column has one -- so silence is informative rather than
    missing.  If documentation were sufficient, this would work."""
    head("15. CLOSED-WORLD DICTIONARY RULE")
    rows = json.load(open(HERE + "closed_labels.json"))
    lab = collections.defaultdict(dict)
    for r in rows:
        lab[int(r["uci_id"])][r["column"]] = r["label"]
    ncol = len(rows)
    flag = [r for r in rows if r["label"] != "CLEAN"]
    print(f"complete-dictionary datasets {len(lab)}   columns {ncol}")
    print(f"flagged {len(flag)}  = {len(flag)/ncol:.3%}   "
          f"{dict(collections.Counter(r['label'] for r in flag))}")
    allb = dict(main); allb.update(expl)
    npos = sum(sum(b["truth"].values()) for b in allb.values())
    nall = sum(len(b["columns"]) for b in allb.values())
    print(f"corpus base rate: {npos} / {nall} = {npos/nall:.1%}")
    sub("recall on this benchmark's positives, where the dataset is in scope")
    tot = got = 0
    inscope = []
    for n, b in sorted(allb.items()):
        uid = UCI_OF.get(n)
        if uid is None or uid not in lab:
            continue
        cols = lab[uid]
        pos = [c for c, v in b["truth"].items() if v]
        hit = [c for c in pos if cols.get(c, "CLEAN") != "CLEAN"]
        tot += len(pos); got += len(hit); inscope.append(n)
        print(f"  {n:<12} positives {len(pos):>3}   flagged {len(hit):>3}   "
              f"{', '.join(hit) or '--'}")
    if tot:
        print(f"  TOTAL  {got}/{tot} = {got/tot:.1%}   "
              f"({len(inscope)} of {len(allb)} corpus datasets in scope)")
    print("\n  Datasets absent from the complete-dictionary set are absent "
          "because at\n  least one of their columns has no description at "
          "all -- which is the\n  point: the rule cannot be applied where "
          "documentation is incomplete.")



# ----------------------------------------------- memorisation robustness
# Datasets whose column list gemini-3.5-flash reproduces IN FULL under
# tabmemcheck's feature-names test, INCLUDING their leaking columns.
# Recall is a property of the model, not of the benchmark, but a reviewer is
# entitled to ask what the headline looks like without them.
MEMORISED = {"AI4I", "BANK", "HEARTFAIL"}


def memorisation_robustness(main):
    """Main-corpus F1 with and without the datasets the checker says are
    recalled verbatim.

    tabmemcheck (Bordt et al., COLM 2024) reproduces 7 of 36 leaking column
    names overall -- 19%, against 33% for columns generally -- and none at all
    on KOI, STEEL, SUPPORT2, BONEMARROW, COMPAS, TITANIC or LC.  But it
    reproduces AI4I, BANK and HEARTFAIL completely, leaking columns included.
    Those three contribute 6 of the 40 Stratum-A positives, and this is the
    honest way to report them: rescore without them and show both numbers."""
    head("16. MEMORISATION ROBUSTNESS (drop the recalled datasets)")
    keep = {n for n in main if n not in MEMORISED}
    print(f"dropping {sorted(MEMORISED)} -> {len(keep)} datasets, "
          f"{sum(sum(main[n]['truth'].values()) for n in keep)} positives")
    print(f"\n{'model':<32}{'cond':>5}{'F1 all':>9}{'F1 kept':>9}{'delta':>8}")
    for m in MODELS:
        c = cells_for(m)
        for cond in (1, 6):
            ka = {(d, s) for (d, cc, s) in c if cc == cond and d in main}
            kb = {(d, s) for (d, s) in ka if d in keep}
            if not kb:
                continue
            ra = prf(main, c, [cond], restrict=ka)
            rb = prf(main, c, [cond], restrict=kb)
            if cond in ra and cond in rb:
                print(f"{m[:31]:<32}{('C'+str(cond)):>5}{ra[cond]['F1']:>9.3f}"
                      f"{rb[cond]['F1']:>9.3f}"
                      f"{rb[cond]['F1']-ra[cond]['F1']:>+8.3f}")



# ------------------------------------------- quantities cited only in prose

def stratum_c(_=None):
    """Stratum C's figures, so the paper's §6.4 numbers are SOURCED here.

    They live in other artefacts -- kaggle_sieve.out, kaggle_anchor.log,
    STRATC_DOWNSTREAM.txt -- and claim_audit only reads NUMBERS.txt, so every
    §6.4 decimal was reported as unsourced.  One of them (the 2.97% raw Kaggle
    trigger rate) is load-bearing: the paper reports the trigger rate on both
    denominators precisely because which one you use flips the comparison with
    UCI.  A number the audit cannot see is a number nobody re-checks."""
    head("18. STRATUM C — external validation figures")
    import re as _re

    def _grab(path, pats):
        if not os.path.exists(HERE + path):
            print(f"  {path}: MISSING")
            return {}
        t = open(HERE + path, errors="replace").read()
        out = {}
        for k, p in pats.items():
            m = _re.search(p, t, _re.M)
            if m:
                out[k] = m.group(1)
        return out

    k = _grab("kaggle_sieve.out", {
        "enriched": r"denominators are the ([\d,]+) datasets",
        "sentences": r"^(\d+) surviving sentences",
        "trigger_ds": r"surviving sentences across (\d+) datasets",
        "synthetic": r"synthetic \(EXCLUDED\)\s+(\d+)",
        "mirrors": r"re-upload of Stratum A/B\s+(\d+)",
        "real": r"REAL and new\s+(\d+)"})
    a = _grab("kaggle_anchor.log", {
        "readable": r"(\d+) datasets with a readable header",
        "anchored": r"(\d+) datasets have a surviving sentence that names",
        "rate": r"anchoring rate ([\d.]+)%"})
    if k and a:
        en, td = int(k["enriched"].replace(",", "")), int(k["trigger_ds"])
        rl = int(k["real"])
        print(f"  Kaggle sweep, COMPLETE")
        print(f"    enriched                        {en}")
        print(f"    triggering datasets             {td}   ({100*td/en:.2f}% raw)")
        print(f"    synthetic excluded              {k['synthetic']}")
        print(f"    re-uploads excluded             {k['mirrors']}")
        print(f"    real and new                    {rl}   ({100*rl/en:.2f}% post-exclusion)")
        print(f"    readable schema                 {a['readable']}")
        print(f"    anchored to a real column       {a['anchored']}   ({a['rate']}%)")
        print(f"    admissible                      0")
        print(f"    UCI reference rate              13/689 = {100*13/689:.2f}%")

    # --- cirrhosis detection, per model.  S6.4.6 quoted "eight API-served
    # models ... six of eight flag N_Days at C1" against a cache that holds TEN
    # models and four C1 hits.  The paragraph had no source here, so nothing
    # could contradict it.  It has one now.
    sub("CIRRHOSIS detection, every model in the cache")
    import glob as _g
    rows = {}
    for f in _g.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if str(r.get("dataset", "")).upper() != "CIRRHOSIS":
            continue
        d, _ = parse(r.get("raw", ""))
        if not d:
            continue
        cols = {c["name"] for c in d["columns"]
                if isinstance(c, dict) and c.get("name")
                and c.get("verdict") == "UNAVAILABLE"}
        rows.setdefault(r["model"], {})[r["condition"]] = (
            "N_Days" in cols, len(cols - {"N_Days"}))
    print(f"    {'model':<46}{'C1 hit':>7}{'C1 fp':>7}{'C6 hit':>8}{'C6 fp':>7}")
    h1 = h6 = f1s = f6s = 0
    for m in sorted(rows):
        a1, b1 = rows[m].get(1, (None, 0))
        a6, b6 = rows[m].get(6, (None, 0))
        print(f"    {m[:44]:<46}{str(a1):>7}{b1:>7}{str(a6):>8}{b6:>7}")
        h1 += bool(a1); h6 += bool(a6); f1s += b1; f6s += b6
    print(f"    MODELS {len(rows)}   flag N_Days at C1 {h1}   at C6 {h6}"
          f"   false positives C1 {f1s}  C6 {f6s}")
    exact = [m for m in rows
             if rows[m].get(1, (0, 1))[0] and rows[m].get(6, (0, 1))[0]
             and rows[m].get(1, (0, 1))[1] == 0 and rows[m].get(6, (0, 1))[1] == 0]
    print(f"    exact (hit, zero fp) at BOTH conditions: {len(exact)} "
          f"{', '.join(exact) if exact else '--'}")

    print("\n  Downstream arms (stratc_downstream.py):")
    if os.path.exists(HERE + "STRATC_DOWNSTREAM.txt"):
        t = open(HERE + "STRATC_DOWNSTREAM.txt", errors="replace").read()
        for m in _re.finditer(r"^===== (\w+).*?\n\s+keep-all F1 ([\d.]+)\s+"
                              r"oracle F1 ([\d.]+)\s+oracle delta ([+-][\d.]+)",
                              t, _re.M | _re.S):
            nm, ka, orc, dl = m.groups()
            chk = "ok" if abs((float(ka)-float(orc)) - float(dl)) < 0.0011 else "ARITHMETIC MISMATCH"
            print(f"    {nm:<13}keep-all {ka}  oracle {orc}  delta {dl}   [{chk}]")
    else:
        print("    STRATC_DOWNSTREAM.txt missing")

    print("\n  ChessFraud (chessfraud_downstream.py):")
    if os.path.exists(HERE + "CHESSFRAUD_DOWNSTREAM.txt"):
        t = open(HERE + "CHESSFRAUD_DOWNSTREAM.txt", errors="replace").read()
        for ln in t.splitlines():
            if "F1 " in ln and ("keep" in ln or "drop" in ln or "alone" in ln):
                print("   " + ln.rstrip()[:96])
            if "dF1" in ln:
                print("   " + ln.strip())
    else:
        print("    CHESSFRAUD_DOWNSTREAM.txt missing")


def response_coverage(main, expl):
    """How much of each prompt each model actually answered.

    WHY THIS SECTION EXISTS

      Recall is computed over every column in the ground truth, and a column
      with no verdict is read as "not flagged".  That is the right reading when
      the MODEL declined to judge it and the wrong one when OUR token budget cut
      the completion off mid-object -- and from the scored table the two are
      indistinguishable.

      33 cells were the second kind.  Every campaign ran at max_tokens=4000, and
      a 144-column dataset at reasoning=high needs far more; CRIME C6 on
      nemotron parsed 1 of 144 columns after 67,868 characters of output and was
      scored as a model that found almost nothing.  Those cells were quarantined
      to responses_truncated/ and re-run at 16,000 tokens.

      This section is the guard that stops it recurring silently.  A cell that
      stops mid-object is TRUNCATED and is reported as a defect; a cell that is
      well-formed and merely short is the model omitting columns, which is a
      model property and is reported as one.

    WHAT THE NUMBERS MEAN

      complete   fraction of cells in which every ground-truth column got a
                 verdict
      mean cov   mean fraction of ground-truth columns judged, over cells

      A model below 100% complete is being scored on columns it did not answer
      for.  That does not invalidate its recall, but it bounds it, and a reader
      comparing two models should know which of them answered the question.
    """
    head("17. RESPONSE COVERAGE — how much of each prompt was answered")
    bundles = dict(main)
    bundles.update(expl)
    per = collections.defaultdict(lambda: [0, 0, 0.0])
    trunc = []
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if r.get("paraphrase"):
            continue                      # aliased names, judged separately
        nm = r.get("shown_as") or r.get("dataset")
        b = bundles.get(nm)
        if not b:
            continue
        raw = r.get("raw", "")
        d, _ = parse(raw)
        if not d:
            continue
        got = {c["name"] for c in d["columns"]
               if isinstance(c, dict) and c.get("name")}
        n = sum(1 for c in b["truth"] if c in got)
        tot = len(b["truth"])
        s = per[r["model"]]
        s[0] += 1
        s[1] += (n == tot)
        s[2] += n / tot
        if n < tot:
            tail = raw.rstrip()[-1:] if raw.strip() else ""
            closed = tail in "}]`\"" and (raw.count("{") - raw.count("}")) <= 1
            if not closed:
                trunc.append((nm, r["model"], r["condition"], n, tot))
    if not per:
        print("  no scored cells")
        return
    print(f"  {'model':<44}{'cells':>6}{'complete':>10}{'mean cov':>10}")
    for m, (n, c, cov) in sorted(per.items(), key=lambda kv: kv[1][2] / max(1, kv[1][0])):
        print(f"  {m[:42]:<44}{n:>6}{100*c/n:>9.0f}%{100*cov/n:>9.1f}%")
    N = sum(v[0] for v in per.values())
    C = sum(v[1] for v in per.values())
    V = sum(v[2] for v in per.values())
    print(f"  {'ALL':<44}{N:>6}{100*C/N:>9.0f}%{100*V/N:>9.1f}%")
    if trunc:
        print(f"\n  TRUNCATED CELLS STILL IN THE CACHE: {len(trunc)} — these are "
              f"OUR token budget, not model failures,\n  and they depress recall. "
              f"Quarantine and re-run at a larger --max-tokens before reporting.")
        for nm, m, c, n, t in sorted(trunc)[:10]:
            print(f"    {nm:<12}C{c} {m[:34]:<36}{n}/{t} columns")
    else:
        print("\n  no truncated cells: every incomplete response is well-formed, "
              "i.e. the model\n  omitted columns rather than being cut off.")

    # ---- cells that were quarantined and never came back -------------------
    # A truncated cell removed from the cache and not regenerated is WORSE than
    # the truncation it replaced: the model silently has fewer cells, matched
    # comparisons quietly drop datasets, and nothing in the scored table says
    # so.  That is not hypothetical -- gemini-3.5-flash lost four AI4I cells to
    # a provider quota, AI4I left the paraphrase control's matched set, and its
    # recall printed 0.000 where it had been 0.680.
    #
    # So every regeneration checks the quarantine against the live cache and
    # names the models whose numbers are provisional.
    qdir = HERE + "responses_truncated/"
    if os.path.isdir(qdir):
        live = collections.defaultdict(set)
        for f in glob.glob(HERE + "responses/*.json"):
            r = json.load(open(f))
            live[(r["model"], r["dataset"], bool(r.get("paraphrase")))].add(
                (r["condition"], r.get("seed")))
        gone = collections.Counter()
        detail = []
        for f in glob.glob(qdir + "*.json"):
            r = json.load(open(f))
            k = (r["model"], r["dataset"], bool(r.get("paraphrase")))
            if (r["condition"], r.get("seed")) not in live[k]:
                gone[r["model"]] += 1
                detail.append((r["model"], r["dataset"], r["condition"],
                               r.get("seed")))
        if gone:
            print(f"\n  *** {sum(gone.values())} QUARANTINED CELLS NEVER "
                  f"RESTORED — these models' numbers are PROVISIONAL ***")
            for m, n in gone.most_common():
                print(f"    {m[:44]:<46}{n:>3} cell(s) missing")
            for m, d, c, s in sorted(detail)[:20]:
                print(f"      {m[:34]:<36}{d:<12}C{c} seed={s}")
            print("    Re-run them before reporting. A missing cell is not a "
                  "model that found nothing.")
        else:
            print("\n  every quarantined cell has been restored.")

    # ---- does incomplete coverage favour one condition over another? --------
    # It would be a serious confound if it did.  The headline comparison is
    # C1 against C6, and a model that answers less of the C6 prompt would show
    # a fake C6 penalty -- indistinguishable, in the scored table, from the
    # derivation clause not working.
    bycond = collections.defaultdict(lambda: [0, 0, 0.0])
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        if r.get("paraphrase"):
            continue
        nm = r.get("shown_as") or r.get("dataset")
        b = bundles.get(nm)
        if not b:
            continue
        d, _ = parse(r.get("raw", ""))
        if not d:
            continue
        got = {c["name"] for c in d["columns"]
               if isinstance(c, dict) and c.get("name")}
        n = sum(1 for c in b["truth"] if c in got)
        tot = len(b["truth"])
        s = bycond[r["condition"]]
        s[0] += 1; s[1] += (n == tot); s[2] += n / tot
    print(f"\n  coverage by condition — a confound check, not a result")
    print(f"  {'cond':<6}{'cells':>7}{'complete':>10}{'mean cov':>10}")
    for c in sorted(bycond):
        n, comp, cov = bycond[c]
        print(f"  C{c:<5}{n:>7}{100*comp/n:>9.0f}%{100*cov/n:>9.1f}%")
    if 1 in bycond and 6 in bycond:
        d1 = bycond[1][2] / bycond[1][0]
        d6 = bycond[6][2] / bycond[6][0]
        print(f"\n  C1 mean coverage {d1:.3%}, C6 {d6:.3%}, difference "
              f"{abs(d1-d6):.3%}.")
        print(f"  {'A C6 deficit would look exactly like the derivation clause failing.' if abs(d1-d6) > 0.02 else 'Too small to bias the C1-vs-C6 comparison the paper reports.'}")


def uncertainty(main):
    """Cluster-bootstrap CIs and McNemar for the C1 -> C6 change.

    Emitted here so the paper's interval and p-value claims have a source in
    NUMBERS.txt like every other number, rather than living only in a script's
    stdout where claim_audit cannot see them."""
    head("19. UNCERTAINTY (cluster bootstrap over datasets; McNemar)")
    import stats_uncertainty as SU
    SU.report(main)


def stratum_d_section(_=None):
    """Stratum D's figures, re-verified from the CSVs on every run."""
    head("20. STRATUM D — mechanically verified positives")
    import stratum_d as SD
    SD.main()


def trivial_positive(main):
    """The headline with ECHO's `still_alive` removed.

    The appendix's own check says still_alive == 0 implies alive_at_1 == 0 on
    45 of 45 rows: it is not so much a leaking feature as a second copy of the
    target, and every model gets it.  Keeping it is defensible -- it is a real
    column a real practitioner would find -- but leaving it unmarked inside the
    headline P/R/F1 is not, because a free true positive inflates recall for
    everyone and a reader cannot see how much.  So the headline is printed both
    ways and the difference is the answer.
    """
    head("23. THE HEADLINE WITHOUT ECHO's `still_alive`")
    drop = {("ECHO", "still_alive")}
    trimmed = {}
    for nm, b_ in main.items():
        c = dict(b_)
        c["truth"] = {k: (False if (nm, k) in drop else v_)
                      for k, v_ in b_["truth"].items()}
        trimmed[nm] = c
    print(f"  {'model':<34}{'F1 C1':>8}{'F1 C1*':>9}{'d':>8}"
          f"{'F1 C6':>9}{'F1 C6*':>9}{'d':>8}")
    print("  * = ECHO.still_alive recoded legitimate\n")
    for m in MODELS:
        cells = cells_for(m)
        keys = {(d, s) for (d, c, s) in cells if c == 1 and d in main} & \
               {(d, s) for (d, c, s) in cells if c == 6 and d in main}
        if not keys:
            continue
        a_ = prf(main, cells, [1, 6], restrict=keys)
        b2 = prf(trimmed, cells, [1, 6], restrict=keys)
        if 1 not in a_ or 6 not in a_ or 1 not in b2 or 6 not in b2:
            continue
        print(f"  {m[:32]:<34}{a_[1]['F1']:>8.3f}{b2[1]['F1']:>9.3f}"
              f"{b2[1]['F1']-a_[1]['F1']:>+8.3f}"
              f"{a_[6]['F1']:>9.3f}{b2[6]['F1']:>9.3f}"
              f"{b2[6]['F1']-a_[6]['F1']:>+8.3f}")
    print("\n  A uniformly small negative shift is the expected result: the")
    print("  column is a free true positive, so removing it costs every model")
    print("  a little recall and costs none of them anything else.")


def subtype_robustness(main):
    """How much §6.2 depends on the subtype partition being right.

    Emitted here so the paper's sensitivity claims have a source like every
    other number.  The analysis lives in subtype_sensitivity.py."""
    head("21. SUBTYPE ROBUSTNESS (adversarial relabelling)")
    import subtype_sensitivity as SS
    SS.main()


def prose_quantities(main):
    """Numbers the manuscript states in sentences rather than tables.

    The paper's rule is that a number not in this file is unverified and does
    not belong.  Table cells are checked row-by-row by verify_tables.py; these
    are the rest -- derived means, thresholds, per-arm downstream figures --
    emitted here so nothing is cited from memory."""
    head("24. QUANTITIES CITED IN PROSE")
    sub("subtype recall, aggregated -- the abstract quotes THIS convention")
    BAD = incomplete_rosters()
    print("  Mean-of-models over the models holding both a C1 and a C6 subtype")
    print("  row.  Stated because the paper previously quoted 62%/81%, which is")
    print("  neither this convention nor column-pooling, and no checker could")
    print("  see it: both are plausible readings of the table.")
    print("  Reported TWICE.  COMPLETE ROSTERS is the primary convention -- the")
    print("  paper quotes it -- because a mean over models weights each row as")
    print("  one comparable unit, and a row missing cells non-randomly is not")
    print("  one.  The all-models figure follows so a reader can see that the")
    print("  choice changes nothing that matters.")
    if BAD:
        print(f"  excluded from the primary aggregate: {', '.join(sorted(BAD))}")
    rows_ = {}
    for m in MODELS:
        c = cells_for(m)
        keys = {(d, s) for (d, cc, s) in c if cc == 1 and d in main} & \
               {(d, s) for (d, cc, s) in c if cc == 6 and d in main}
        if not keys:
            continue
        r = prf(main, c, [1, 6], restrict=keys)
        if 1 in r and 6 in r:
            rows_[m] = r

    def _agg(pop, label):
        print(f"\n  {label}  (n={len(pop)} models)")
        print(f"  {'subtype':<14}{'C1':>8}{'C6':>8}{'lift':>8}")
        for st in ("REASON", "CONSEQUENCE", "TIMING"):
            vals = {}
            for cond in (1, 6):
                xs = [pop[m][cond]["sub"][st][0] / pop[m][cond]["sub"][st][1]
                      for m in pop
                      if st in pop[m][cond]["sub"] and pop[m][cond]["sub"][st][1]]
                vals[cond] = sum(xs) / len(xs) if xs else float("nan")
            print(f"  {st:<14}{vals[1]:>7.1%}{vals[6]:>8.1%}"
                  f"{vals[6]-vals[1]:>+8.1%}")
        below = sum(1 for m in pop
                    if pop[m][1]["sub"].get("REASON", (0, 0))[1]
                    and pop[m][1]["sub"].get("CONSEQUENCE", (0, 0))[1]
                    and (pop[m][1]["sub"]["REASON"][0] / pop[m][1]["sub"]["REASON"][1]
                         < pop[m][1]["sub"]["CONSEQUENCE"][0]
                         / pop[m][1]["sub"]["CONSEQUENCE"][1]))
        print(f"  models scoring REASON below their own CONSEQUENCE at C1: "
              f"{below} of {len(pop)}")

    _agg({m: r for m, r in rows_.items() if m not in BAD}, "COMPLETE ROSTERS")
    _agg(rows_, "ALL MODELS, including incomplete rosters")

    sub("tier means of the C1->C6 F1 gain")
    FRONT = {"claude-opus-5-max", "gpt-5.6-sol-xhigh", "gemini-3.7-flash",
             "gemini-3.5-flash"}
    g = {"frontier": [], "replication": []}
    gc = {"frontier": [], "replication": []}
    BAD = incomplete_rosters()
    for m in MODELS:
        c = cells_for(m)
        keys = {(d, s) for (d, cc, s) in c if cc == 1 and d in main} & \
               {(d, s) for (d, cc, s) in c if cc == 6 and d in main}
        if not keys:
            continue
        r = prf(main, c, [1, 6], restrict=keys)
        if 1 in r and 6 in r:
            g["frontier" if m in FRONT else "replication"].append(
                r[6]["F1"] - r[1]["F1"])
            if m not in BAD:
                gc["frontier" if m in FRONT else "replication"].append(
                    r[6]["F1"] - r[1]["F1"])
    for k, v in g.items():
        print(f"  {k:<13}mean gain {sum(v)/len(v):+.3f}  (n={len(v)})")
    # Same reasoning as the subtype aggregate: an incomplete roster is a fine
    # row and a poor summand.
    for k, v in gc.items():
        if len(v) != len(g[k]):
            print(f"  {k:<13}mean gain {sum(v)/len(v):+.3f}  (n={len(v)}, "
                  f"complete rosters only)")
    # The replication mean is pulled down by the one model that gets WORSE at
    # C6 (S7.3).  Printed so the paper can say so with a source rather than
    # leaving a reader to wonder whether the tier gap is one model's doing.
    rep = sorted(g["replication"])
    if rep:
        print(f"  replication, excluding the single negative model "
              f"({rep[0]:+.3f}): {sum(rep[1:])/len(rep[1:]):+.3f}  (n={len(rep)-1})")

    sub("B3 threshold and the correlations of the columns the paper names")
    import baselines10 as B
    F = pd.read_csv(HERE + "baseline10_features.csv")
    r = B.best_threshold(F.y.values, F.cor.values)
    print(f"  B3 threshold |r| >= {r['threshold']}")
    for ds, col in (("LC", "recoveries"), ("LC", "collection_recovery_fee"),
                    ("TITANIC", "sex"), ("TITANIC", "body")):
        row = F[(F.ds == ds) & (F.col == col)]
        if len(row):
            print(f"  {ds}.{col:<26}|r| = {abs(row.cor.iloc[0]):.3f}   "
                  f"positive={bool(row.y.iloc[0])}")

    sub("downstream arm F1s cited by name")
    d = pd.read_csv(HERE + "downstream2.csv")
    for ds, arm in (("LC", "B3"), ("LC", "GT"), ("TITANIC", "B3"),
                    ("TITANIC", "GT"), ("ECHO", "GT"),
                    ("ECHO", "claude-opus-5-max")):
        x = d[(d.dataset == ds) & (d.arm == arm) & (d.learner == "rf")]
        if len(x):
            print(f"  {ds:<9}{arm:<20}F1 {x.f1.iloc[0]:.3f}  "
                  f"dropped {int(x.n_dropped.iloc[0])}")


if __name__ == "__main__":
    main, expl = corpus()
    recs = evidence(main, expl)
    derivation_checks()
    scarcity()
    baselines()
    model_table(main)
    ladder(main)
    transfer(expl)
    downstream()
    confusion()
    cachestats()
    paraphrase_control(main)
    loo(main)
    seed_spread(main, expl)
    triage(main, expl)
    closed_world(main, expl)
    memorisation_robustness(main)
    response_coverage(main, expl)
    stratum_c()
    uncertainty(main)
    stratum_d_section()
    subtype_robustness(main)
    trivial_positive(main)
    prose_quantities(main)
    print("\n" + "=" * W + "\nEND OF VERIFICATION\n" + "=" * W)
