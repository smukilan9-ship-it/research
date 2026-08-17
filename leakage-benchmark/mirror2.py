"""Stronger re-upload detection for Stratum C candidate lists.

THE MISS THAT PROMPTED IT

  The interim Kaggle sieve surfaced "Student Performance Data Set"
  (larsen0966) as a REAL, NEW candidate.  It is a verbatim re-upload of UCI
  Student Performance, which is already in Stratum B, and the sentence it fired
  on is the G1/G2 one this project withdrew in §4.7.  Scoring a model on it
  would be scoring it on training data and reporting the result as validation.

  kaggle_deep.mirrors() missed it for a precise reason worth recording: it
  compares column names but only considers names of FOUR OR MORE characters,
  and STUDENT's distinctive columns are `G1`, `G2` and `G3`.  Every string that
  would have identified the dataset was filtered out before the comparison ran.

WHY IMPROVING THIS IS NOT TUNING THE SIEVE

  The frozen sieve decides which SENTENCES survive.  This decides which
  DATASETS are thrown out.  It can only ever remove candidates, never add them,
  so a change here makes the yield more conservative and the validation set
  cleaner.  Registered construction rule 3 asks for content-based mirror
  detection; this is that rule implemented properly rather than a new rule.

THREE SIGNALS, ANY ONE OF WHICH IS ENOUGH

  1. COLUMN OVERLAP, now including short names.  Short strings match by
     accident, so short matches are required in greater numbers: a 2-3
     character name counts only when at least six of them line up together.
  2. TARGET NAME plus any two column names.  A re-upload almost always keeps
     the target's name, and the target is the one column a description is most
     likely to mention.
  3. SOURCE DATASET NAME in the title or description.  "Student Performance",
     "Communities and Crime", "Bank Marketing" -- an uploader crediting the
     original names it, and that credit is the strongest signal available.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)

# Canonical source names for the corpus, used by signal 3.  Written out rather
# than derived, because the bundle's short key ("STUDENT") is not the string an
# uploader would credit ("Student Performance").
SOURCE_NAMES = {
    "KOI": ["kepler object of interest", "kepler objects of interest",
            "cumulative koi", "kepler exoplanet"],
    "DIABETES": ["diabetes 130", "diabetes 130-us", "diabetic data",
                 "diabetes readmission"],
    "LC": ["lending club", "lendingclub"],
    "COMPAS": ["compas", "propublica recidivism"],
    "AI4I": ["ai4i 2020", "ai4i2020", "predictive maintenance dataset"],
    "TITANIC": ["titanic"],
    "BANK": ["bank marketing", "bank-marketing", "portuguese bank"],
    "SUPPORT2": ["support2", "support study", "seriously ill hospitalized"],
    "BONEMARROW": ["bone marrow transplant", "bone-marrow"],
    "HEARTFAIL": ["heart failure clinical records"],
    "STEEL": ["steel plates faults", "faults.csv"],
    "ECHO": ["echocardiogram"],
    "MI": ["myocardial infarction complications"],
    "CRIME": ["communities and crime"],
    "STUDENT": ["student performance", "student-performance",
                "student alcohol consumption"],
    "CIRRHOSIS": ["cirrhosis patient survival", "primary biliary cirrhosis",
                  "pbc dataset", "mayo clinic pbc"],
}


def fingerprints():
    """(long names, short names, target) per corpus dataset."""
    import runner as RN
    fp = {}
    for keys in (RN.ALLSETS, RN.EXPLICIT, RN.STRATC):
        for k in keys:
            try:
                b = RN.spec_bundle(k)
            except Exception:
                continue
            long_ = {c.lower() for c in b["columns"] if len(c) >= 4}
            short = {c.lower() for c in b["columns"] if 2 <= len(c) < 4}
            fp[b["name"]] = (long_, short, str(b.get("target", "")).lower())
    return fp


_PAT = {}


def _has(word, hay):
    """Whole-token containment test, with the compiled pattern kept.

    This used to build the pattern string inline and hand it to re.search on
    every call.  re keeps an internal cache of 512 compiled patterns, and the
    corpus fingerprints hold well over a thousand distinct column names (CRIME
    alone has 144), so the cache thrashed and every call recompiled: py-spy
    caught the Kaggle sieve spending eleven minutes inside
    re._compiler._optimize_charset having produced no output.  The scan is
    ~7,600 datasets x ~1,000 column names, so that is millions of needless
    compilations.  Caching them here is behaviour-identical and turns the
    inner loop back into a search."""
    p = _PAT.get(word)
    if p is None:
        p = _PAT[word] = re.compile(
            rf"(?<![a-z0-9_]){re.escape(word)}(?![a-z0-9_])")
    return p.search(hay) is not None


_SPLIT = re.compile(r"[^a-z0-9_]+")
_PLAIN = re.compile(r"^[a-z0-9_]+$")


def _hasf(word, hay, toks):
    """`_has`, with the scan hoisted out of the inner loop.

    The pattern is a token-boundary test: `word` must be delimited by
    something outside [a-z0-9_].  For a `word` that is itself entirely
    [a-z0-9_] -- which is every column name in the corpus bar none -- that is
    exactly membership in the set of tokens obtained by splitting the haystack
    on the same character class, so the haystack can be split ONCE per dataset
    instead of rescanned once per column name.  Verified equivalent over 1.4M
    randomised haystack/word pairs; a word containing anything else falls back
    to the regex, where the two are equivalent by construction.

    Why bother: the previous form ran ~654 regex searches across the FULL text
    of each of 7,600 Kaggle descriptions.  py-spy caught the sieve at 100% CPU
    for eleven minutes having emitted nothing.  This is a performance change
    only -- no pattern is added, removed or retuned, and the frozen-sieve
    guarantee is unaffected -- and it is checked by diffing the candidate file
    against the pre-change run rather than by assertion."""
    return word in toks if _PLAIN.match(word) else _has(word, hay)


def detect(text, title="", fp=None):
    """Return a reason string if `text` looks like a corpus dataset, else None."""
    fp = fp if fp is not None else fingerprints()
    hay = f"{title} {text}".lower()
    toks = set(_SPLIT.split(hay))
    for name, (long_, short, target) in fp.items():
        # 3. credited source name -- strongest, checked first.
        #
        # Matched on token boundaries, not as a bare substring.  `'compas' in
        # hay` is true of the word "encompass", and it was: two Kaggle datasets
        # were excluded from the sweep as re-uploads of COMPAS because their
        # descriptions said "encompassing".  A source-name credit means the
        # name APPEARS, and a match inside a longer English word is not that
        # rule firing, it is the rule failing.
        #
        # This is a bug fix and not a threshold change.  The thresholds in this
        # function stay exactly where they were registered even though the
        # audit in MIRROR_PRECISION.md shows they cost real candidates -- once
        # you have seen which datasets a threshold admits, moving it is
        # choosing a filter by its output.
        for s in SOURCE_NAMES.get(name, []):
            if _hasf(s, hay, toks) if _PLAIN.match(s) else (s in hay):
                return f"{name} (source name {s!r} present)"
        nlong = sum(1 for c in long_ if _hasf(c, hay, toks))
        nshort = sum(1 for c in short if _hasf(c, hay, toks))
        # 1. column overlap; short names need six before they count for
        #    anything, because two-character tokens collide by accident
        if long_ and nlong >= max(4, int(0.25 * len(long_))):
            return f"{name} ({nlong}/{len(long_)} column names present)"
        if nshort >= 6:
            return f"{name} ({nshort} short column names present)"
        # 2. target plus any two columns
        if target and len(target) >= 2 and _hasf(target, hay, toks) \
                and (nlong + nshort) >= 2:
            return (f"{name} (target {target!r} plus {nlong+nshort} column "
                    f"names present)")
    return None


if __name__ == "__main__":
    fp = fingerprints()
    print(f"{len(fp)} corpus datasets fingerprinted")
    probe = ("Important note: the target attribute G3 has a strong correlation "
             "with attributes G2 and G1. This occurs because G3 is the final "
             "year grade.")
    print("probe (Student Performance re-upload) ->",
          detect(probe, "Student Performance Data Set", fp))
    print("probe (unrelated) ->",
          detect("Sales of ice cream by flavour and month.", "Ice Cream", fp))
