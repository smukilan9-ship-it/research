"""A post-hoc sieve extension, kept separate from the frozen one.

WHY THIS FILE EXISTS, AND WHY IT IS NOT explicit_scan.py

  While assembling the appendix I re-fetched the 29 UCI records that had
  failed to download on the first two passes (689 in the archive index, 660
  on disk).  One of them was id 601, AI4I 2020 -- a dataset already IN this
  benchmark, whose documentation says:

    "If at least one of the above failure modes is true, the process fails
     and the 'machine failure' label is set to 1."

  That is an explicit, source-authored, feature-level target-leakage
  statement: the target is a disjunction of five columns that sit in the
  table.  All three families of the frozen sieve -- WARN, DEFINE and
  the per-dataset DEFINE-with-target-name -- miss it, because they all
  require a preposition after the assignment verb ("set FROM", "derived
  FROM"), and this author wrote a conditional instead ("set TO 1" governed by
  a preceding "if").

  Editing explicit_scan.py to catch a pattern I found by hand, and then
  reporting the result as if the sieve had found it, would be fitting the
  instrument to its answer.  So the original is frozen and this runs beside
  it.  Everything it finds is reported as POST-HOC and separately from the
  frozen-sieve count.

THE ADDED FAMILY
  CONDSET: a sentence that (a) contains a conditional operator, and (b)
  assigns a value to something named as the label / class / target / outcome,
  or to the dataset's own declared target column.  No preposition required.

  This is the whole extension.  It is one pattern, written to cover the
  construction the miss demonstrated, and it is run once over all 689
  records.  I am not iterating it until the hit list looks good.
"""
import json, glob, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
META = HERE + "ucimeta/"
OUT = HERE + "cond_candidates.jsonl"

sys.path.insert(0, HERE)
import explicit_scan as E

def _sents(txt):
    for s in E.SPLIT.split(txt):
        s = " ".join(s.split())
        if 15 <= len(s) <= 600:
            yield s


COND = re.compile(r"\b(?:if|when|whenever|where|unless|in case)\b", re.I)

# "<something label-ish> is/was set|assigned|coded|marked|flagged to/as <value>"
ASSIGN_GENERIC = re.compile(
    r"(?:class|label|target|outcome|response|dependent variable|flag)\w*\s+"
    r"(?:value\s+)?(?:is|was|are|were|has been|have been|becomes?|gets?)\s+"
    r"(?:then\s+)?(?:set|assigned|coded|marked|flagged|given|put)\s+"
    r"(?:to|as|equal to|=)\s*", re.I)


def assign_named(sent, targets):
    """Same construction, but the subject is the dataset's own target name."""
    verb = (r"\s+(?:value\s+)?(?:is|was|are|were|has been|have been|becomes?)\s+"
            r"(?:then\s+)?(?:set|assigned|coded|marked|flagged|given)\s+"
            r"(?:to|as|equal to|=)")
    for t in targets:
        if len(t) < 3:
            continue
        for m in re.finditer(rf"(?<![A-Za-z0-9_]){re.escape(t)}(?![A-Za-z0-9_])",
                             sent, re.I):
            # allow a short noun phrase between the name and the verb
            win = sent[m.end():m.end() + 60]
            if re.match(r"(?:['\"]?\s*(?:label|column|variable|field|flag)?)" + verb,
                        win, re.I):
                return t
    return None


def main():
    rows, per = [], collections.Counter()
    files = sorted(glob.glob(META + "*.json"))
    for f in files:
        try:
            _r = json.load(open(f)); d = _r.get("data", _r)
        except Exception:
            continue
        targets = E.target_names(d)
        for field, text in E.texts(d):
            for sent in _sents(text):
                if not COND.search(sent):
                    continue
                fam = None
                if ASSIGN_GENERIC.search(sent):
                    fam = "CONDSET_GENERIC"
                else:
                    t = assign_named(sent, targets)
                    if t:
                        fam = "CONDSET_NAMED"
                if not fam:
                    continue
                cols = [c for c in E.colnames(d)
                        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(c)}(?![A-Za-z0-9_])",
                                     sent, re.I) and len(c) >= 3]
                rows.append(dict(uci_id=d.get("uci_id"), name=d.get("name"),
                                 family=fam, field=field, sentence=sent.strip(),
                                 columns_mentioned=cols))
                per[(d.get("uci_id"), d.get("name"))] += 1
    with open(OUT, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"{len(files)} metadata records scanned")
    print(f"{len(rows)} conditional-assignment sentences "
          f"across {len(per)} datasets -> {OUT}\n")
    print("  " + str(dict(collections.Counter(r['family'] for r in rows))) + "\n")
    for (i, n), c in per.most_common():
        print(f"  {i!s:>5}  {str(n)[:45]:<47}{c:>3}")


if __name__ == "__main__":
    main()
