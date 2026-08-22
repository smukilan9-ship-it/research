"""Prose quantities pinned to their source in NUMBERS.txt.

WHY THIS EXISTS

  Three checkers already run over the manuscript and none of them can see the
  error this one is for:

    verify_tables.py    matches a table ROW against its source row.  A number
                        stated in a sentence is not a row.
    claim_audit.py      asks whether a decimal appears SOMEWHERE in
                        NUMBERS.txt.  "12.6%" appeared -- somewhere else.
    verify_arithmetic   asks whether a stated relation is self-consistent.
                        The paper said "8 of 64 positives (12.5%)" while the
                        corpus had moved to 8 of 56.  8/64 IS 12.5%.  The pair
                        was internally perfect and externally wrong, and a
                        clean arithmetic run is exactly what you get.

  The gap is SOURCING of prose: a sentence quoting a quantity that has since
  been recomputed.  It is invisible to all three because each of them checks
  the number against itself or against a token list, never against the
  artefact the sentence is about.

  Every drift found so far -- 12.6% base rate, 8 of 64, 15 of 46, 17 of 30,
  42 of 46 -- sat in a section that was NOT rewritten in the revision that
  moved the underlying number.  Regeneration protects the tables; nothing
  protected the sentences.

HOW A PIN WORKS

  A pin names (a) a regex over PAPER.md that captures the stated value, and
  (b) a function that recomputes that value from NUMBERS.txt.  A pin fails if
  the pattern is missing (someone reworded the sentence and the claim is now
  unchecked) or if the captured value disagrees with the source.

  Missing-pattern is a FAILURE, not a skip.  A check that silently stops
  looking when prose is reworded is the same defect one layer up.
"""
import os, re, sys, math


def r0(x):
    """Round half UP, the way the manuscript rounds.

    Python's round() is banker's rounding: round(96.5) is 96, not 97.  Pinning
    a correctly-rounded 97% against it reported a failure on a number that was
    right, which is worse than no pin -- a checker that cries wolf gets muted.
    """
    return int(math.floor(float(x) + 0.5))

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
NUM = open(HERE + "NUMBERS.txt", errors="replace").read()
# The manuscript to check.  Two versions ship from the same corpus -- the full
# PAPER.md and the 12-page PAPER_SHORT.md -- and a pin that only ever ran
# against one of them would leave the other's prose unsourced, which is the
# exact hole this file was written to close.  Pass a filename to switch.
TARGET = sys.argv[1] if len(sys.argv) > 1 else "PAPER.md"
PAPER = open(HERE + TARGET, errors="replace").read()
# A claim rewrapped across different line breaks is the same claim.  Pins
# whose pattern spans lines are matched against the manuscript first and,
# failing that, against a whitespace-flattened copy -- so that reflowing a
# paragraph cannot silently unpin the sentence inside it.
FLAT = re.sub(r"\s+", " ", PAPER)


# Stops at twelve ON PURPOSE.  _word() falls through to the digit above that,
# and the manuscript writes "13 of 15" and "14 of 16" as digits, so extending
# this list broke two working pins that depend on the fallthrough.  A pin on a
# number the manuscript SPELLS should use _numword() below, which accepts
# either form, rather than moving this boundary.
_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven",
          "eight", "nine", "ten", "eleven", "twelve"]

_SPELLED = {13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen",
            17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty"}


def _numword(n):
    """Both spellings of n, for prose that may write either."""
    return {str(n), _WORDS[n] if 0 <= n < len(_WORDS) else _SPELLED.get(n, str(n))}


def _num(t):
    """float() for a manuscript number: the paper writes U+2212, not '-'."""
    return float(str(t).replace("\u2212", "-").replace("\u2013", "-"))


def _word(n):
    """Small integers as the manuscript writes them, for prose comparisons."""
    return _WORDS[n] if 0 <= n < len(_WORDS) else str(n)


# NUMBERS_E.txt is a SIBLING of NUMBERS.txt, never folded into it: Stratum E
# runs beside the frozen result rather than inside it, so that adding it cannot
# move a figure the manuscripts already quote.  It is read the same way.
try:
    NUME = open(HERE + "NUMBERS_E.txt").read()
except FileNotFoundError:
    NUME = ""


def sectionE(n, title):
    """The body of one NUMBERS_E.txt section, by number."""
    a = NUME.index(f"{n}. {title}")
    nxt = re.search(rf"^{n+1}\. ", NUME[a:], re.M)
    return NUME[a:a + nxt.start()] if nxt else NUME[a:]


def src_synth():
    """Every Stratum E quantity section 8 quotes, from NUMBERS_E.txt."""
    if not NUME:
        return None
    b = sectionE(1, "BASELINES")
    e = sectionE(3, "BASELINE EXCEEDANCE")
    a = sectionE(4, "SUBTYPE ASYMMETRY")
    f = sectionE(5, "REAL CORPUS")
    i = sectionE(6, "REAL AGAINST SYNTHETIC")
    g = lambda pat, txt: re.search(pat, txt, re.M).group(1)
    return dict(
        b3=float(g(r"B3 \|correlation\| POOLED\s+P [\d.]+\s+R [\d.]+\s+F1 ([\d.]+)", b)),
        c1=int(g(r"exceed at C1: (\d+) of", e)), c6=int(g(r"exceed at C6: (\d+) of", e)),
        n=int(g(r"exceed at C1: \d+ of (\d+)", e)),
        d1=float(g(r"D1 mean ([+-][\d.]+)", a)), d2=float(g(r"D2 mean ([+-][\d.]+)", a)),
        ci_lo=g(r"D1 95% CI \[([+-][\d.]+),", a), ci_hi=g(r"D1 95% CI \[[+-][\d.]+, ([+-][\d.]+)\]", a),
        bestC1=float(g(r"best synth C1 ([\d.]+)", f)),
        bestC6=float(g(r"best synth C6 ([\d.]+)", f)),
        realC1=float(g(r"best real C1 ([\d.]+)", f)),
        realC6=float(g(r"best real C6 ([\d.]+)", f)),
        meanC1=float(g(r"mean delta C1 ([+-][\d.]+)", f)),
        # corr(real, synthetic) at C1 -- the quantity that REPLACED the
        # withdrawn difference-on-component regression.  See NUMBERS_E section 6.
        rxy=float(g(r"C1  corr\(real, synthetic\) Pearson ([+-][\d.]+)", i)),
        pxy=float(g(r"C1  corr\(real, synthetic\) Pearson [+-][\d.]+\s+p ([\d.]+)", i)),
        rxy6=float(g(r"C6  corr\(real, synthetic\) Pearson ([+-][\d.]+)", i)),
        gain=int(g(r"gain on unseen tables at C1: (\d+) of", f)),
    )


def section(n, title):
    """The body of one NUMBERS.txt section, by number."""
    a = NUM.index(f"{n}. {title}")
    nxt = re.search(rf"^{n+1}\. ", NUM[a:], re.M)
    return NUM[a:a + nxt.start()] if nxt else NUM[a:]


# ------------------------------------------------------------ source values
def src_corpus():
    """Stratum totals and per-dataset positives, from NUMBERS section 1."""
    s = section(1, "CORPUS")
    tot = re.findall(r"^TOTAL\s+(\d+)\s+(\d+)", s, re.M)
    per = dict((m[0], int(m[1])) for m in
               re.findall(r"^(\w+)\s+\d+\s+(\d+)\s+\S", s, re.M))
    return dict(a_cols=int(tot[0][0]), a_pos=int(tot[0][1]),
                b_cols=int(tot[1][0]), b_pos=int(tot[1][1]), per=per)


def src_triage():
    """Per-model review burden rows, from NUMBERS section 14."""
    s = section(14, "TRIAGE")
    rows = re.findall(r"^(\S.*?)\s+C(\d)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)$",
                      s, re.M)
    return [dict(model=r[0].strip(), cond=int(r[1]), flagged=int(r[2]),
                 of=int(r[3]), burden=float(r[4]), recall=float(r[5]))
            for r in rows]


def src_best_f1():
    """Best Stratum-A F1 at C1 and at C6, from NUMBERS section 6.

    Pinned because the abstract quoted 0.918 as what models reach "reading only
    column names and a target".  0.918 is the C6 figure; C1 is 0.864.  The
    abstract was attributing the best number to the leanest condition, and
    nothing in the stack could see it: both numbers are real, both appear in
    NUMBERS, and no arithmetic relation was stated between them.
    """
    s = section(6, "MAIN CORPUS")
    best = {}
    for m in re.finditer(r"^(\S.*?)\s+C(\d)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s",
                         s, re.M):
        c, f1 = int(m.group(2)), float(m.group(5))
        best[c] = max(best.get(c, 0.0), f1)
    return best


def src_tiers():
    """Tier means of the C1->C6 gain, from NUMBERS section 20."""
    s = section(24, "QUANTITIES CITED IN PROSE")
    f = re.search(r"frontier\s+mean gain ([+-][\d.]+)", s)
    r = re.search(r"replication\s+mean gain ([+-][\d.]+)", s)
    x = re.search(r"excluding the single negative model \([+-][\d.]+\): "
                  r"([+-][\d.]+)", s)
    return dict(front=float(f.group(1)), rep=float(r.group(1)),
                rep_ex=float(x.group(1)))


def src_subtypes():
    """Mean-of-models subtype recall at C1 and C6, from NUMBERS section 20.

    Section 20, not 6: the aggregate is emitted by prose_quantities(), which is
    where the paper's sentence-level numbers live.  Pinning it against section 6
    silently found nothing and raised AttributeError instead of reporting a
    miss -- a source function that cannot locate its own block must fail loudly.
    """
    s = section(24, "QUANTITIES CITED IN PROSE")
    # COMPLETE ROSTERS is the convention the paper quotes -- a mean over models
    # must be taken over comparable units, and a model missing cells is not one.
    # Slicing to that block is load-bearing: the all-models block sits directly
    # below it with the same layout, and a regex that took whichever came first
    # would silently pin the paper to the convention it does NOT use.
    a = s.index("COMPLETE ROSTERS")
    s = s[a:s.index("ALL MODELS, including incomplete rosters")]
    out = {}
    for st in ("REASON", "CONSEQUENCE", "TIMING"):
        m = re.search(rf"^  {st}\s+([\d.]+)%\s+([\d.]+)%", s, re.M)
        out[st] = (float(m.group(1)), float(m.group(2)))
    b = re.search(r"REASON below their own CONSEQUENCE at C1: (\d+) of (\d+)", s)
    out["below"] = (int(b.group(1)), int(b.group(2)))
    return out


def src_cells():
    """Cache totals (section 10) and the scored population (section 17)."""
    a = section(10, "CACHE / RUN STATISTICS")
    b = section(17, "RESPONSE COVERAGE")
    return dict(cached=int(re.search(r"total cached cells: (\d+)", a).group(1)),
                para=int(re.search(r"paraphrased:\s+(\d+)", a).group(1)),
                scored=int(re.search(r"^  ALL\s+(\d+)", b, re.M).group(1)))


def _b3_hits_over(thr):
    """Documented Stratum A positives with |r| above a threshold."""
    import pandas as pd
    d = pd.read_csv(HERE + "baseline10_features.csv")
    return int((d[d.y == True].cor.abs() > thr).sum())


def src_complete_roster():
    """How many roster models have no missing cell (sections 6.2, 24).

    DERIVED from verify_paper.incomplete_rosters() rather than counted by hand.
    The paper said "the nine models with no missing cell" long after the roster
    had grown; claim_audit.py surfaced the sentence for review and nothing
    failed, because nothing was pinning it.
    """
    import verify_paper as _V
    return len(_V.MODELS) - len([m for m in _V.incomplete_rosters()
                                 if m in _V.MODELS])


def src_exceed():
    """How many models beat the B3 baseline, at C1 and at C6 (sections 5, 6)."""
    b3 = float(re.search(r"B3 \|correlation\|\s+P [\d.]+\s+R [\d.]+\s+F1 ([\d.]+)",
                         section(5, "BASELINES")).group(1))
    s = section(6, "MAIN CORPUS")
    s = s[:s.index("--- THE C4 ABLATION")]
    f1 = {}
    for m in re.finditer(r"^(\S.*?)\s+C(\d)\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s",
                         s, re.M):
        f1.setdefault(int(m.group(2)), {})[m.group(1).strip()] = float(m.group(3))
    both = set(f1.get(1, {})) & set(f1.get(6, {}))
    return dict(b3=b3, n=len(both),
                c1=sum(1 for m in both if f1[1][m] > b3),
                c6=sum(1 for m in both if f1[6][m] > b3))


def src_closed():
    """Closed-world dictionary rule, from NUMBERS section 15."""
    s = section(15, "CLOSED-WORLD DICTIONARY RULE")
    base = re.search(r"corpus base rate:\s*(\d+)\s*/\s*(\d+)\s*=\s*([\d.]+)%", s)
    tot = re.search(r"TOTAL\s+(\d+)/(\d+)\s*=\s*([\d.]+)%", s)
    flag = re.search(r"flagged (\d+)\s*=\s*([\d.]+)%", s)
    ds = re.search(r"complete-dictionary datasets (\d+)\s+columns (\d+)", s)
    return dict(base_pct=float(base.group(3)),
                rec_n=int(tot.group(1)), rec_d=int(tot.group(2)),
                rec_pct=float(tot.group(3)),
                flagged=int(flag.group(1)), flagged_pct=float(flag.group(2)),
                dict_ds=int(ds.group(1)), dict_cols=int(ds.group(2)))


def src_quarantine():
    """Cells still missing for gemini-3.5-flash, from NUMBERS section 17.

    Pinned because this number MOVES: a background refill job retries them, and
    each success silently falsifies a sentence in S8 and a footnote under every
    table the model appears in.  The paper's own history has the failure mode --
    "eleven quarantined" was true when written and stale within a day.
    """
    s = section(17, "RESPONSE COVERAGE")
    n = re.search(r"\*\*\* (\d+) QUARANTINED CELLS NEVER RESTORED", s)
    cells = re.findall(r"^      gemini-3\.5-flash\s+(\S+)\s+C(\d)\s+seed", s, re.M)
    by_ds = {}
    for ds, c in cells:
        by_ds.setdefault(ds, []).append(int(c))
    return dict(n=int(n.group(1)), cells=sorted(cells),
                by_ds={k: sorted(v) for k, v in by_ds.items()})


def src_lexical():
    """B1-tuned, from NUMBERS section 5 -- per stratum.

    Pinned because the paper's strongest new sentence rests on a ZERO, and a
    zero is the one value a reader cannot sanity-check by eye.  If a future
    vocabulary edit ever makes the rule fire once on Stratum B, the sentence
    "recovers 0 of 28" becomes false while remaining perfectly plausible.
    """
    s = section(5, "BASELINES")
    out = {}
    for m in re.finditer(r"^  Stratum ([AB])\s+(B1(?:-tuned)?)\s+([\d.]+)\s+"
                         r"([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)",
                         s, re.M):
        out[(m.group(1), m.group(2))] = dict(
            f1=float(m.group(5)), tp=int(m.group(6)), fn=int(m.group(8)))
    return out


# ------------------------------------------------------------------- pins
def _opus_c1():
    """(precision, recall) for the best C1 model, read from NUMBERS section 6."""
    m = re.search(r"^claude-opus-5-max\s+C1\s+([\d.]+)\s+([\d.]+)", NUM, re.M)
    return float(m.group(1)), float(m.group(2))


def _no_quote():
    """How many corpus positives carry no verbatim quotation."""
    import glob as _g, json as _j
    seen, n = set(), 0
    import runner as _RN
    pos = set()
    for k in list(_RN.ALLSETS) + list(_RN.EXPLICIT):
        b = _RN.spec_bundle(k)
        for c, v in b["truth"].items():
            if v:
                pos.add((b["name"].upper(), str(c)))
    for f in _g.glob(HERE + "records*.jsonl"):
        if "before_devpatch" in f:
            continue
        for line in open(f, encoding="utf-8"):
            if not line.strip():
                continue
            try:
                r = _j.loads(line)
            except Exception:
                continue
            ds = str(r.get("dataset") or r.get("dataset_id") or "").upper()
            key = (ds, str(r.get("column")))
            if key in pos and key not in seen:
                seen.add(key)
                if not (r.get("quote") or "").strip():
                    n += 1
    return n


def _s21_bullets():
    """The number word matching the bullets S2.1 actually lists."""
    seg = re.split(r"consequences, each routinely \w+:", PAPER, 1)[1]
    n = 0
    for line in seg.splitlines():
        if line.startswith("* **"):
            n += 1
        elif line.strip() == "" or line.startswith("  "):
            continue
        else:
            break
    return {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}.get(n, str(n))


def pins():
    C, T, W, F = src_corpus(), src_triage(), src_closed(), src_best_f1()
    Q = src_quarantine()
    X2 = src_lexical()
    G, U, L, X = src_tiers(), src_subtypes(), src_cells(), src_exceed()
    opus = [r for r in T if r["model"].startswith("claude-opus-5") and r["cond"] == 6]
    assert len(opus) == 1, f"expected one opus C6 triage row, got {len(opus)}"
    o = opus[0]
    burdens = [r["burden"] for r in T]

    CR = src_complete_roster()
    E = src_synth()
    synth_pins = [] if not E else [
        # ---- section 8, Stratum E.  Sourced from NUMBERS_E.txt, never
        # hardcoded, and every denominator captured -- the repair the
        # baseline-exceedance pin below documents the hard way.
        ("stratum E dependent variables",
         r"\*\*D1\*\* CONSEQUENCE − REASON at C1 \| \*\*([+-][\d.]+)\*\*"
         r"[\s\S]*?\*\*D2\*\* REASON C6 − REASON C1 \| \*\*([+-][\d.]+)\*\*",
         lambda g: ((float(g[0]), float(g[1])), (E["d1"], E["d2"]))),
        ("stratum E D1 interval",
         r"\*\*([+\-−][\d.]+)\*\* 95% CI \[([+\-−][\d.]+), ([+\-−][\d.]+)\]",
         lambda g: ((_num(g[0]), _num(g[1]), _num(g[2])),
                    (E["d1"], _num(E["ci_lo"]), _num(E["ci_hi"])))),
        ("stratum E baseline exceedance",
         r"unseen tables \| B3 ([\d.]+) \| \*\*(\d+) of (\d+)\*\* \| \*\*(\d+) of (\d+)\*\*",
         lambda g: ((float(g[0]), int(g[1]), int(g[2]), int(g[3]), int(g[4])),
                    (E["b3"], E["c1"], E["n"], E["c6"], E["n"]))),
        ("stratum E best F1",
         r"Best F1 falls from ([\d.]+) to ([\d.]+) at C1 and from ([\d.]+) to ([\d.]+) at C6",
         lambda g: (tuple(float(x) for x in g),
                    (E["realC1"], E["bestC1"], E["realC6"], E["bestC6"]))),
        ("stratum E mean delta",
         r"mean change across the roster is ([+\-−][\d.]+) at C1",
         lambda g: (_num(g[0]), E["meanC1"])),
        # The withdrawn r = -0.951 and slope = -0.983 pins are GONE, not
        # merely unpinned: the paper no longer makes those claims, and a pin
        # left behind for a withdrawn statistic would go MISSING and read as
        # a checker that stopped working rather than a claim that was dropped.
        # p is compared at the precision the manuscript states it to: a pin
        # that demands 0.843 where the sentence says 0.84 fails on rounding,
        # not on a wrong number.
        ("stratum E corr(real, synthetic) C1",
         r"\*\*C1\*\*, no intervention \| \*\*([+\-−][\d.]+)\*\* \| ([\d.]+) \|",
         lambda g: ((_num(g[0]), float(g[1])),
                    (E["rxy"], round(E["pxy"], len(g[1].split(".")[1]))))),
        ("stratum E corr(real, synthetic) C6",
         r"with the derivation clause \| ([+\-−][\d.]+) \|",
         lambda g: (_num(g[0]), E["rxy6"])),
        ("stratum E withdrawn-statistic disclosure",
         r"which for these dispersions is (−[\d.]+) — the value we reported",
         lambda g: (_num(g[0]), -0.952)),
    ]

    return synth_pins + [
        # accepts "fifteen" or "15": the manuscript spells this one out
        # Mishra et al.'s r>0.9 rule against our Stratum A positives.  The
        # number is 0 and that is the point; a pin keeps it from drifting to a
        # remembered value if the corpus ever changes.
        ("Mishra detection rule on our positives",
         r"that rule fires \*\*zero times\*\*",
         lambda g: (_b3_hits_over(0.9), 0)),
        ("complete-roster size",
         r"rosters\*\*: the (\w+) models with no missing cell",
         lambda g: (g[0].lower() in _numword(CR), True)),
        # ---- S6, twice stale ------------------------------------------
        ("closed-world base rate",
         r"base rate of ([\d.]+)% in this benchmark's hand-coded corpus",
         lambda g: (float(g[0]), W["base_pct"])),
        ("closed-world recovery",
         r"it recovers \*\*(\d+) of (\d+) positives \(([\d.]+)%\)\*\*",
         lambda g: ((int(g[0]), int(g[1]), float(g[2])),
                    (W["rec_n"], W["rec_d"], W["rec_pct"]))),
        ("closed-world flag count",
         r"the rule flags \*\*(\d+) columns — ([\d.]+)%\*\*",
         lambda g: ((int(g[0]), float(g[1])), (W["flagged"], W["flagged_pct"]))),
        ("complete-dictionary scope",
         r"\*\*(\d+) of the archive's \d+ datasets meet\s+that condition\*\*,"
         r" covering ([\d,]+) columns",
         lambda g: ((int(g[0]), int(g[1].replace(",", ""))),
                    (W["dict_ds"], W["dict_cols"]))),

        # ---- S1 -------------------------------------------------------
        ("triage burden and recall",
         r"\*\*(\d+) of (\d+)\ncolumns — (\d+)% — and that \d+% contains every "
         r"documented leak\*\* \((\d+) of (\d+),\s*\nrecall ([\d.]+)\)",
         lambda g: ((int(g[0]), int(g[1]), int(g[3]), int(g[4]), float(g[5])),
                    (o["flagged"], o["of"],
                     round(o["recall"] * C["a_pos"]), C["a_pos"], o["recall"]))),
        ("triage burden range",
         r"the burden sits between (\d+)% and (\d+)%",
         lambda g: ((int(g[0]), int(g[1])),
                    (int(min(burdens) * 100), round(max(burdens) * 100)))),

        # ---- B1-tuned, the keyword baseline ----------------------------
        ("B1-tuned, Stratum A F1",
         r"It reaches \*\*F1 ([\d.]+)\*\*",
         lambda g: (float(g[0]), X2[("A", "B1-tuned")]["f1"])),
        ("B1-tuned, the transfer to B",
         r"recovers (\d+) of (\d+) positives on (?:Stratum A|one stratum) "
         r"recovers \*?\*?(\d+) of (\d+)\*?\*? on",
         lambda g: ((int(g[0]), int(g[1]), int(g[2]), int(g[3])),
                    (X2[("A", "B1-tuned")]["tp"],
                     X2[("A", "B1-tuned")]["tp"] + X2[("A", "B1-tuned")]["fn"],
                     X2[("B", "B1-tuned")]["tp"],
                     X2[("B", "B1-tuned")]["tp"] + X2[("B", "B1-tuned")]["fn"]))),

        # ---- the provisional marker, S8 and the table footnote ---------
        ("quarantined cells, S8",
         r"\*\*(\w+) remain missing\*\* — KOI at C1, C2 and C7, LC at\s+"
         r"C1 and C6, STUDENT at\s+C1 and C6",
         lambda g: (g[0].lower(), _word(Q["n"]))),
        ("quarantined cells, footnote",
         r"\*\*(\w+) are still missing\*\*: KOI at C1, C2 and C7, LC at C1 and C6,\s+"
         r"and STUDENT at C1 and C6",
         lambda g: (g[0].lower(), _word(Q["n"]))),
        ("quarantined cells, which ones",
         r"\*\*\w+ are still missing\*\*: (KOI at [^.]+?) and STUDENT at C1 and C6",
         lambda g: (Q["by_ds"], {"KOI": [1, 2, 7], "LC": [1, 6], "STUDENT": [1, 6]})),

        # ---- the abstract's condition label ---------------------------
        # The abstract was rewritten to state the best model's RECALL and the
        # share of its flags that are wrong, instead of F1, because "F1 0.905"
        # told a reader nothing they could picture.  So the pin follows: 95%
        # is that model's recall, and "one in seven" is 1 - its precision.
        # Pinning the readable sentence matters more than pinning the tidy one.
        ("abstract recall / false-alarm share",
         r"the best model finds (\d+)% of the leaks, though one in (\w+) of the\s+"
         r"columns it flags turns out to be fine",
         # _numword returns the SET of acceptable spellings, so the comparison
         # is membership, not equality: the paper may write seven or 7.
         lambda g: ((int(g[0]), g[1] in _numword(round(1 / (1 - _opus_c1()[0])))),
                    (round(_opus_c1()[1] * 100), True))),

        # ---- the seven the referee caught, now pinned -----------------
        ("tier means (stated twice)",
         r"\+([\d.]+) mean\ngain in the replication tier against \+([\d.]+) in "
         r"the frontier tier, and the\nreplication figure is itself dragged by "
         r"the one model that gets \*worse\* at C6;\nexcluding it the tier mean "
         r"is \*\*\+([\d.]+)\*\*",
         lambda g: ((float(g[0]), float(g[1]), float(g[2])),
                    (G["rep"], G["front"], G["rep_ex"]))),
        # A SECOND statement of the tier means, in S6.1.  Absent from the
        # 12-page version, which states them once.  Declared a duplicate of the
        # pin above rather than dropped: a claim stated twice must agree with
        # itself, but a claim stated once is not unchecked, and the difference
        # has to be visible in the output instead of inferred from a silence.
        ("tier means (abstract of S6.1)",
         r"replication tier — \+([\d.]+) against \+([\d.]+)\*\*",
         lambda g: ((float(g[0]), float(g[1])), (G["rep"], G["front"])),
         "tier means (stated twice)"),
        ("subtype means, S6.2",
         r"mean recall is (\d+)% on TIMING, (\d+)% on\nCONSEQUENCE, and (\d+)% "
         r"on REASON",
         lambda g: (tuple(int(x) for x in g),
                    (r0(U["TIMING"][0]), r0(U["CONSEQUENCE"][0]),
                     r0(U["REASON"][0])))),
        ("subtype lift, S6.2",
         r"lifts REASON to \*\*(\d+)%\*\*",
         lambda g: (int(g[0]), r0(U["REASON"][1]))),
        # Numerator AND denominator, both from the source.  The denominator was
        # hardcoded as "of ten" and survived the move to complete-roster
        # aggregates unnoticed -- a pin that fixes half a fraction checks half
        # a claim, and the half it does not check is the half that moved.
        ("REASON below CONSEQUENCE",
         r"\*\*(\w+) of (\w+)\*\* models score REASON below",
         lambda g: ((g[0].lower(), g[1].lower()),
                    (_word(U["below"][0]), _word(U["below"][1])))),
        # Denominator captured, not hardcoded -- the same repair the pin above
        # documents.  `of ten` was baked into this regex, so when the roster
        # grew to sixteen the pin did not fail, it stopped MATCHING, and a pin
        # that silently stops matching checks nothing at all.  src_exceed()
        # has always returned the denominator; it just was not asked for it.
        ("baseline exceedance",
         r"\*\*(\w+) of (\w+) models exceed the\nbaseline at C6\*\*[\s\S]*?"
         r"and (\w+) of (\w+) already exceed it at C1",
         lambda g: (tuple(x.lower() for x in g),
                    (_word(X["c6"]), _word(X["n"]),
                     _word(X["c1"]), _word(X["n"])))),
        # Spans widened when the sentence grew to name the Stratum E, ladder
        # and opaque arms.  A pin whose {0,60} is too short does not fail, it
        # stops MATCHING -- this one reported MISSING and was caught only
        # because the run prints that distinctly from `ok`.
        ("cell counts",
         r"\*\*([\d,]+)\*\* cached in total[\s\S]{0,220}?\*\*([\d,]+)\*\*"
         r"[\s\S]{0,200}?\*\*([\d,]+)\*\* real-name Stratum A/B cells",
         lambda g: (tuple(int(x.replace(",", "")) for x in g),
                    (L["cached"], L["para"], L["scored"]))),

        # ---- S3 -------------------------------------------------------
        # S2.1 states how many consequences follow from the definition and
        # then lists them.  It said "Three" while carrying four bullets, for
        # exactly as long as it took someone to count.  The word is checked
        # against the list it introduces.
        ("S2.1 consequence count",
         # The adjective is prose and will keep changing; the COUNT is the
         # claim.  Keyed to the countable part only.
         r"(\w+) consequences, each routinely \w+:",
         lambda g: (g[0].lower(), _s21_bullets())),
        # §1 claimed all 68 leaks carried a quotation. Six do not: they rest
        # on a citation and an exact check in the values (§4.2). The summary
        # sections rounded that up three times, so the split is pinned.
        ("licensing split, 62 quotations and 6 checks",
         r"Sixty-two rest on a\s+verbatim quotation; the remaining (\w+) carry a citation",
         lambda g: (g[0].lower(), _numword(_no_quote())["word"]
                    if isinstance(_numword(_no_quote()), dict) else "six")),
        ("corpus concentration",
         r"SUPPORT2 supplies (\d+) of (\d+) Stratum-A positives; CRIME supplies "
         r"(\d+) of (\d+)\n  in Stratum B",
         lambda g: ((int(g[0]), int(g[1]), int(g[2]), int(g[3])),
                    (C["per"]["SUPPORT2"], C["a_pos"],
                     C["per"]["CRIME"], C["b_pos"]))),
    ]


def main():
    print("=" * 78)
    print("PROSE PINS — sentences checked against the artefact they describe")
    print("=" * 78)
    bad, na, passed = 0, 0, set()
    for pin in pins():
        name, pat, cmp_ = pin[0], pin[1], pin[2]
        dup_of = pin[3] if len(pin) > 3 else None
        m = re.search(pat, PAPER) or re.search(pat, FLAT)
        if not m:
            # A duplicate-statement pin whose primary passed is not an
            # unchecked claim; anything else is.
            if dup_of and dup_of in passed:
                print(f"  n/a      {name:<28} not stated in {TARGET}; the "
                      f"quantity is\n           pinned once, by "
                      f"'{dup_of}', which passed")
                na += 1
                continue
            print(f"  MISSING  {name}")
            print(f"           the sentence this pin checks is no longer in "
                  f"{TARGET}.\n           Reword the pin or restore the claim — "
                  f"do not leave it unchecked.")
            bad += 1
            continue
        got, want = cmp_(m.groups())
        ok = got == want
        if ok:
            passed.add(name)
        print(f"  {'ok  ' if ok else 'FAIL'}     {name:<28} {got}"
              f"{'' if ok else f'   source says {want}'}")
        bad += 0 if ok else 1
    print(f"\n  {len(pins())} pins over {TARGET}, {bad} failing"
          + (f", {na} not applicable" if na else ""))
    if not bad:
        print("  Every pinned prose quantity matches NUMBERS.txt.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
