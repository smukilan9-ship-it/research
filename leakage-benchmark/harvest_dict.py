"""Second harvesting pass: data dictionaries reproduced INSIDE papers.

WHY THIS EXISTS
  harvest_pdf.py scans prose for what authors say they DID ("we excluded X").
  Across 26 papers and 10 datasets it found exactly one usable statement.  That
  looked like the familiar result -- documentation does not exist -- but it was
  partly an artifact of the scanner.  Papers very often reproduce the dataset's
  data dictionary as a TABLE, and pypdf flattens a table into an unpunctuated
  run of text, so a sentence splitter never sees a sentence and the prose sieve
  walks past it.

  Those tables are the best evidence in the corpus:

    "12 Time  Time period of follow-up 4-285 Days"          (heart failure)
    "survival_time  Time of observation (if alive) or time to event (if dead)"
    "Still-alive  0 - the patient is dead at end of survival period"

WHY IT OUTRANKS THE PROSE PASS
  A reproduced dictionary is FULL_COLUMN_SET scope (PROTOCOL 8a): it addresses
  every column, so its SILENCE about a column is informative -- it means "not
  label-derived".  A paper's methods section is EXCLUSION_LIST_ONLY: silence
  there may mean legitimate, unused, or simply unconsidered.  Only equal-scope
  sources may be compared for agreement, so these two passes produce records
  that are deliberately kept apart.

  Tier is still E3, not E1: the paper is quoting the dictionary, and a
  transcription is not the archive's own page.  Where the archive itself can be
  retrieved, that supersedes this (PROTOCOL 6, rule 1).

STILL A SIEVE
  Every hit needs the quote read before it licenses a label.  A description
  containing "survival" may be the target itself rather than a feature, and the
  target is never a label-derived feature -- it IS the label.
"""
import json, os, re, sys, glob, collections
from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
from screen import PAT          # the dictionary-wording sieve, reused verbatim
from harvest_pdf import slug_of

OUT = HERE + "dict_candidates.jsonl"

# a dictionary row: a column-ish name, then a description.  Column names in
# these tables are snake_case, Hyphen-Case, CamelCase or single lowercase words.
ROW = re.compile(
    r"\b([A-Za-z][A-Za-z0-9]*(?:[_\-][A-Za-z0-9]+){0,4})\s+"      # name
    r"((?:[A-Z(]|[a-z])[^|]{12,150}?)"                             # description
    r"(?=\s+[A-Za-z][A-Za-z0-9]*(?:[_\-][A-Za-z0-9]+){0,4}\s+[A-Z(]|$)")
# extra wording that places a value at/after the outcome, beyond screen.PAT
EXTRA = re.compile(
    r"(time (?:of|to) (?:observation|event|failure|recur|death)|"
    r"time[- ]to[- ]event|follow[- ]?up|until (?:development|the event)|"
    r"duration until|at end of|during the .{0,20}period|"
    r"if (?:the patient )?(?:died|dead|alive)|time period of|censor)", re.I)
# things that are the TARGET, not a feature -- flagged so they are not counted
TARGETISH = re.compile(r"\b(class attribute|target|outcome variable|label|"
                       r"dependent variable|response variable)\b", re.I)


def text_of(path):
    try:
        r = PdfReader(path)
    except Exception:
        return []
    out = []
    for i, pg in enumerate(r.pages, 1):
        t = pg.extract_text() or ""
        out.append((i, re.sub(r"\s+", " ", re.sub(r"-\n", "", t))))
    return out


def scan(path):
    ds, src = slug_of(path)
    recs = []
    for pageno, t in text_of(path):
        for m in ROW.finditer(t):
            name, desc = m.group(1), m.group(2).strip()
            if len(name) < 2 or name.lower() in ("the", "and", "for", "with", "this",
                                                 "table", "figure", "input", "value"):
                continue
            hit = PAT.search(desc) or EXTRA.search(desc)
            if not hit:
                continue
            recs.append(dict(
                dataset_id=ds, source=src, page=pageno,
                column=name, description=desc[:220],
                marker=hit.group(0).lower(),
                is_target_row=bool(TARGETISH.search(desc)),
                evidence_tier="E3", source_type="PEER_REVIEWED",
                scope="FULL_COLUMN_SET", adjudicated=False))
    # de-duplicate a column repeated across pages of the same paper
    seen, uniq = set(), []
    for r in recs:
        k = (r["dataset_id"], r["source"], r["column"].lower())
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return ds, src, uniq


def main():
    files = sorted(glob.glob(HERE + "pdfs/*.pdf"))
    allrecs, byds = [], collections.defaultdict(set)
    for f in files:
        ds, src, recs = scan(f)
        byds[ds].add(src)
        allrecs += recs
    with open(OUT, "w") as fh:
        for r in allrecs:
            fh.write(json.dumps(r) + "\n")

    feat = [r for r in allrecs if not r["is_target_row"]]
    print(f"{len(files)} PDFs -> {len(allrecs)} dictionary rows with timing wording "
          f"({len(feat)} after dropping rows that describe the target itself)\n")
    print(f"{'dataset':<36}{'papers':>7}{'candidate columns':>19}")
    for ds in sorted(byds):
        rs = [r for r in feat if r["dataset_id"] == ds]
        if not rs:
            continue
        cols = sorted({r["column"] for r in rs})
        print(f"  {ds:<34}{len(byds[ds]):>7}{len(cols):>19}   {', '.join(cols[:6])}")
    print(f"\nwrote {OUT}  -- every row still needs adjudication")


if __name__ == "__main__":
    main()
