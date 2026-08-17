"""PROTOCOL 5, steps 3-4: pull candidate exclusion statements out of papers.

INPUT   pdfs/<uuid>-<dataset_slug>__<author><year>.pdf
OUTPUT  pdf_candidates.jsonl -- one record per candidate sentence, with the
        verbatim quote and a page locator, ready for adjudication.

This is a SIEVE, not a classifier, for the same reason screen.py is: the models
under evaluation must never contribute to the ground truth they are scored
against (PROTOCOL 4).  A regex proposes; a human disposes.  Every record it
emits still needs the quote read in context before it licenses a label.

WHY THE PAPER SIEVE DIFFERS FROM THE DICTIONARY SIEVE
  screen.py looks for wording that places a COLUMN after the outcome
  ("post charge off", "at discharge").  A paper almost never says that.  It says
  what the authors DID: "we excluded", "was removed to avoid leakage".  So the
  vocabulary here is removal verbs and leakage terms, and the column name is
  what we search for nearby, not what triggers the match.

SCOPE, WHICH IS RECORDED AND MATTERS
  Papers are EXCLUSION_LIST_ONLY sources (PROTOCOL 8a).  Their silence about a
  column is uninformative -- it may be legitimate, unused, or unconsidered.
  That is why agreement is only ever computed against sources of equal scope,
  and why nothing here can generate a LEGITIMATE label.
"""
import json, os, re, sys, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
PDFDIR = HERE + "pdfs/"
OUT = HERE + "pdf_candidates.jsonl"

# what an author says when they drop a column
ACTION = r"(exclud|remov|drop|discard|omit|delet|elimina|not\s+used|were\s+not\s+included)"
# what an author says about WHY
REASON = (r"(leak|data\s+snooping|look[-\s]?ahead|target\s+leak|future\s+information"
          r"|not\s+available\s+at|unavailable\s+at|after\s+the\s+outcome|post[-\s]?outcome"
          r"|only\s+known\s+after|determined\s+after|prior\s+to\s+prediction"
          r"|would\s+not\s+be\s+known|realistic\s+predict)")
ACT = re.compile(ACTION, re.I)
RSN = re.compile(REASON, re.I)
# a token that looks like a column name: snake_case, CamelCase w/ digits, or ALLCAPS
COLLIKE = re.compile(r"\b(?:[a-z]+_[a-z0-9_]+|[A-Z]{2,}[0-9]*|[a-z]+[A-Z][a-zA-Z]*)\b")
# identifier leakage is real but is NOT a label-derived feature
IDPAT = re.compile(r"\b(identifier|patient[_ ]?(id|nbr)|encounter[_ ]?id|record[_ ]?id|"
                   r"\bids?\b|primary key|index column)", re.I)
# wording that places a value at or after the outcome
TIMEPAT = re.compile(r"(only known after|known only after|available only after|"
                     r"after the (call|outcome|event|diagnosis|discharge|procedure|surgery)|"
                     r"not (?:be )?(?:known|available|recorded) (?:until|before|at)|"
                     r"recorded (?:after|post)|measured after|collected after|"
                     r"determined after|assigned after|subsequent to the outcome|"
                     r"posterior to|not available at (?:the )?(?:time of )?prediction)", re.I)
# a column referred to in prose rather than as a token ("the call duration")
NAMEDCOL = re.compile(r"\b(?:variable|feature|attribute|column|field)s?\b[^.]{0,60}"
                      r"|such as the \w+", re.I)


def slug_of(path):
    """<uuid>-<dataset>__<author><year>.pdf -> (dataset, source)"""
    base = os.path.basename(path)
    base = re.sub(r"^[0-9a-f]{6,}-", "", base)          # strip upload uuid
    base = re.sub(r"\.pdf$", "", base, flags=re.I)
    if "__" in base:
        ds, src = base.split("__", 1)
        return ds, src
    return base, "unknown"


def pages(path):
    from pypdf import PdfReader
    try:
        r = PdfReader(path)
    except Exception as e:
        return None, f"unreadable: {str(e)[:80]}"
    out = []
    for i, pg in enumerate(r.pages, 1):
        try:
            out.append((i, pg.extract_text() or ""))
        except Exception:
            out.append((i, ""))
    if sum(len(t) for _, t in out) < 500:
        return out, "NO_TEXT_LAYER (scanned image? needs OCR)"
    return out, None


def sentences(text):
    t = re.sub(r"-\n", "", text)            # de-hyphenate across line breaks
    t = re.sub(r"\s+", " ", t)
    return re.split(r"(?<=[.;:])\s+(?=[A-Z(])", t)


def scan(path):
    ds, src = slug_of(path)
    pg, warn = pages(path)
    recs = []
    if pg is None:
        return ds, src, [], warn
    for pageno, text in pg:
        for s in sentences(text):
            if len(s) < 25 or len(s) > 600:
                continue
            a, r_ = ACT.search(s), RSN.search(s)
            if not (a or r_):
                continue
            # an action alone is weak (papers "exclude patients" constantly);
            # require either a leakage reason, or an action next to column-like
            # tokens, which is what a feature-exclusion list looks like
            cols = sorted(set(COLLIKE.findall(s)))
            if not r_ and not (a and len(cols) >= 1):
                continue
            # Classify by what the sentence can LICENSE, not by how many
            # patterns it matched.  The first cut ranked an identifier-removal
            # sentence ("encounter_id and patient_nbr were removed to prevent
            # information leakage") as the strongest evidence in the corpus,
            # while filing the one genuinely useful statement -- "call duration
            # ... is only known after the call" -- as a weak match, because the
            # author described the problem without saying they fixed it.
            # Identifier leakage is a different phenomenon and is not
            # label-derived; a timing claim is exactly what we need whether or
            # not the author acted on it.
            ident = bool(IDPAT.search(s))
            timing = bool(TIMEPAT.search(s))
            named = bool(cols) or bool(NAMEDCOL.search(s))
            if ident and not timing:
                kind = "IDENTIFIER"          # real leakage, wrong kind
            elif timing and named:
                kind = "TIMING_CLAIM"        # <- what licenses LABEL_DERIVED
            elif a and named:
                kind = "EXCLUSION"           # author dropped a named feature
            elif timing:
                kind = "TIMING_NO_COLUMN"
            else:
                kind = "GENERIC"
            recs.append(dict(
                dataset_id=ds, source=src, page=pageno,
                quote=s.strip()[:500],
                kind=kind,
                action=a.group(0).lower() if a else None,
                reason=r_.group(0).lower() if r_ else None,
                column_like=cols[:12],
                source_type="PEER_REVIEWED", scope="EXCLUSION_LIST_ONLY",
                evidence_tier="E3", adjudicated=False))
    return ds, src, recs, warn


def main():
    files = sorted(glob.glob(PDFDIR + "*.pdf"))
    if not files:
        sys.exit(f"no PDFs in {PDFDIR}")
    allrecs, bydataset, warns = [], collections.defaultdict(set), []
    for f in files:
        ds, src, recs, warn = scan(f)
        bydataset[ds].add(src)
        if warn:
            warns.append((os.path.basename(f)[:60], warn))
        allrecs += recs
    with open(OUT, "w") as fh:
        for r in allrecs:
            fh.write(json.dumps(r) + "\n")

    print(f"{len(files)} PDFs -> {len(allrecs)} candidate statements "
          f"across {len(bydataset)} datasets\n")
    kinds = collections.Counter(r["kind"] for r in allrecs)
    print(f"  by kind: {dict(kinds)}")
    print("  TIMING_CLAIM is the only kind that can license LABEL_DERIVED on its\n"
          "  own; EXCLUSION needs reading to confirm it drops a COLUMN, not rows.\n")
    print(f"{'dataset':<38}{'sources':>8}{'TIMING':>8}{'total':>7}")
    for ds in sorted(bydataset):
        rs = [r for r in allrecs if r["dataset_id"] == ds]
        st = sum(1 for r in rs if r["kind"] == "TIMING_CLAIM")
        print(f"  {ds:<36}{len(bydataset[ds]):>8}{st:>8}{len(rs):>7}")
    if warns:
        print(f"\n  {len(warns)} file(s) need attention:")
        for n, w in warns:
            print(f"    {n:<62}{w}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
