"""Anchored harvest: find each REAL column name in each paper, then judge the
wording around it.

This replaces the unanchored pass in harvest_dict.py, which matched any
"Word Word..." pair and consequently proposed author surnames from reference
lists (Aftab, Chicco, Blackstone) as candidate columns -- 127 "candidates" for
heart failure, almost all bibliography.

Anchoring on the distributed column list is also what PROTOCOL I5 demands: the
names in the evidence source must match the names in the file, or the record is
not admissible.  Matching the other way round -- inventing a name from the paper
and hoping a column exists -- is how you get evidence for a column nobody has.

MATCHING
  Names are compared on a normalised form (lowercase, separators stripped) so
  `still_alive` in the CSV matches "Still-alive" in a table.  Short names are a
  hazard: `time`, `age`, `mult`, `epss`, `y`.  Anything under 5 characters must
  match with its separators intact and is additionally required to sit next to
  dictionary-ish or timing wording, or it is dropped -- otherwise every "time"
  in an English sentence becomes evidence.

OUTPUT
  A candidate is (dataset, column, paper, page, quote, marker).  It is NOT a
  label.  adjudicate_new.py turns candidates into records, and only where the
  quote actually places the value at or after the outcome.
"""
import json, os, re, sys, glob, collections
from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
from screen import PAT
from harvest_pdf import slug_of
import newdata as ND

OUT = HERE + "anchored_candidates.jsonl"

TIMEPAT = re.compile(
    r"(time (?:of|to) (?:observation|event|failure|recur|death|relapse)|"
    r"time[- ]to[- ]event|follow[- ]?up|until (?:development|the event)|"
    r"duration until|at end of|during the .{0,25}period|censor|"
    r"if (?:the patient )?(?:died|dead|alive|survived)|time period of|"
    r"only known after|known only after|after the (?:call|outcome|event|"
    r"diagnosis|discharge|procedure|surgery|transplant)|"
    r"post[- ]?(?:transplant|operative|treatment)|recovery|survival)", re.I)
# Wording that shows the LABEL IS DEFINED IN TERMS OF the column.  PAT and
# TIMEPAT are both temporal, so without this the sieve cannot surface a REASON
# column as a candidate at all -- the transfer batch produced zero, and the
# adjudicator never got the chance to judge them.  Same blindness as the models.
REASONPAT = re.compile(
    r"(one of (?:the )?(?:two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:fault|defect|class|categor|type|pattern|outcome)|"
    r"mutually exclusive|none of the (?:above|other|named|six|seven)|"
    r"remaining (?:fault|defect|class|categor|case)|"
    r"assigned (?:by|from|based on|according to|on the basis of)|"
    r"classified (?:as|into|according to|based on|on the basis of)|"
    r"determined (?:by|from|on the basis of)|"
    r"(?:label|labell?ed|coded|scored) (?:as|according to|based on|from)|"
    r"derived from the|defined as (?:the )?(?:absence|presence|any|none)|"
    r"used to (?:assign|define|determine|derive) the "
    r"(?:class|label|target|outcome|diagnosis)|"
    r"expert|obstetrician|clinician|annotator|adjudicat)", re.I)
# wording that marks a real data-dictionary row rather than running prose
DICTISH = re.compile(r"(numerical|categorical|binary|numeric|input|attribute|"
                     r"variable|feature|days|months|years|yes,? ?no|0\s*[-,–]\s*1|"
                     r"class attribute|measured in|defined as|range)", re.I)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def pages_text(path):
    try:
        r = PdfReader(path)
    except Exception:
        return []
    out = []
    for i, pg in enumerate(r.pages, 1):
        t = pg.extract_text() or ""
        out.append((i, re.sub(r"\s+", " ", re.sub(r"-\n", "", t))))
    return out


def variants(col):
    """Surface forms a paper might use for one column name."""
    v = {col, col.replace("_", " "), col.replace("_", "-"), col.replace("_", "")}
    return {x for x in v if len(x) >= 2}


def scan(path, columns, target):
    recs = []
    cols_by_norm = {norm(c): c for c in columns}
    for pageno, text in pages_text(path):
        low = text
        for c in columns:
            short = len(c) < 5
            for form in variants(c):
                if short and form != c:
                    continue          # short names must match exactly
                # exclude hyphen adjacency: matching `time` inside
                # "time-to-failure" captures the compound's tail as the
                # column's description instead of the real dictionary row
                for m in re.finditer(r"(?<![A-Za-z0-9\-])" + re.escape(form) +
                                     r"(?![A-Za-z0-9\-])", low, re.I):
                    w = low[max(0, m.start() - 170): m.start() + 230]
                    hit = PAT.search(w) or TIMEPAT.search(w) or REASONPAT.search(w)
                    if not hit:
                        continue
                    if short and not DICTISH.search(w):
                        continue      # `time`/`age` need dictionary context
                    recs.append(dict(column=c, page=pageno,
                                     quote=w.strip()[:300],
                                     marker=hit.group(0).lower()[:40],
                                     dictish=bool(DICTISH.search(w)),
                                     is_target=(c == target)))
                    break
                else:
                    continue
                break
    # one record per (column) per paper: keep the most dictionary-like quote
    best = {}
    for r in recs:
        k = r["column"]
        if k not in best or (r["dictish"] and not best[k]["dictish"]):
            best[k] = r
    return list(best.values())


def main():
    files = sorted(glob.glob(HERE + "pdfs/*.pdf"))
    allrecs = []
    per_ds = collections.defaultdict(lambda: collections.defaultdict(set))
    for f in files:
        slug, src = slug_of(f)
        key = ND.SLUG.get(slug)
        if not key:
            continue                      # not a manifest dataset (or already ours)
        spec = ND.NEW[key]()
        for r in scan(f, spec["columns"], spec["target"]):
            r.update(dataset=spec["name"], dataset_key=key, source=src,
                     evidence_tier="E3", source_type="PEER_REVIEWED",
                     scope="FULL_COLUMN_SET" if r["dictish"] else "EXCLUSION_LIST_ONLY",
                     adjudicated=False)
            allrecs.append(r)
            if not r["is_target"]:
                per_ds[spec["name"]][r["column"]].add(src)

    with open(OUT, "w") as fh:
        for r in allrecs:
            fh.write(json.dumps(r) + "\n")

    print(f"{len(allrecs)} anchored candidates "
          f"({sum(1 for r in allrecs if r['is_target'])} are the target itself)\n")
    print(f"{'dataset':<14}{'cols flagged':>13}{'>=2 sources':>13}   columns")
    for ds in sorted(per_ds):
        cols = per_ds[ds]
        multi = [c for c, s in cols.items() if len(s) >= 2]
        print(f"  {ds:<12}{len(cols):>13}{len(multi):>13}   "
              f"{', '.join(sorted(cols)[:7])}")
        if multi:
            print(f"  {'':<12}{'':>13}{'':>13}   CORROBORATED: {', '.join(sorted(multi))}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
