"""Explicit statements that are HEADINGS, not sentences.

THE FORM THE SENTENCE SCANNER CANNOT SEE
  UCI 579 (Myocardial infarction complications) documents its 124 attributes
  as a numbered list broken into labelled blocks.  Attribute 112 sits under
  "Treatment"; attribute 113 sits under

      Complications and outcomes of myocardial infarction:

  and everything from 113 to 124 falls under it.  Our target ZSN is number
  121 -- inside that block.  The other eleven columns in the block are
  declared by the source itself to be outcomes of the same episode, and no
  sentence anywhere says so.  A sentence-level scanner reads each numbered
  line in isolation and finds nothing; it scored 64 hits on this dataset and
  every one of them was the phrase "at the time of admission" attached to a
  legitimate BASELINE covariate -- exactly backwards.

  A heading is an explicit statement about every column beneath it.  Treating
  it as one is not inference on our part: the authors chose the grouping and
  wrote the word "outcomes".

BLOCK BOUNDARIES
  A block ends at the next heading, whatever that heading says.  Getting this
  wrong is how a licensing phrase leaks onto a neighbouring legitimate column,
  which is the failure mode adjudicate_new.py was written to stop.  So a
  heading is recognised structurally -- a short unnumbered line -- and ANY
  such line closes the current block, not only the ones we like.
"""
import json, glob, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
META = HERE + "ucimeta/"
OUT = HERE + "section_candidates.jsonl"

# A heading that declares its block to be outcomes / post-episode material.
# NOTE the trailing `s?`.  Without it `\bcomplication\b` cannot match the word
# "Complications", because the boundary assertion fails against the plural s --
# which silently returned zero blocks on the one dataset this pass exists for.
OUTCOME_HEAD = re.compile(
    r"\b(complication|outcome|follow[- ]?up|post[- ](?:operative|treatment|"
    r"discharge|infarction|transplant|intervention)|"
    r"result[s]? of (?:the )?(?:treatment|therapy|surgery|procedure)|"
    r"survival|mortalit(?:y|ies)|death|end[- ]?point|"
    r"target (?:variable|attribute)|dependent variable|class attribute|"
    r"response variable|what happened|event(?:s)? (?:during|after))s?\b", re.I)

# Numbered attribute rows: "113. Atrial fibrillation (FIBR_PREDS): Nominal"
NUMBERED = re.compile(r"^\s*(\d{1,3})[.)]\s+(.*)$")


def is_heading(line):
    """Structural test only: a short line that is not a numbered attribute row
    and not a statistics row.  Deliberately not 'a line we recognise'."""
    s = line.strip()
    if not s or len(s) > 130:
        return False
    if NUMBERED.match(s):
        return False
    if re.match(r"^\s*(cases|missing|\d|[-+]?\d*\.?\d+%?)\b", s, re.I):
        return False
    if "\t" in line:
        return False
    return bool(re.search(r"[A-Za-z]{4}", s))


def blocks(text):
    """(heading, [lines]) for every heading-delimited block."""
    head, buf, out = None, [], []
    for line in text.splitlines():
        if is_heading(line):
            if head is not None:
                out.append((head, buf))
            head, buf = line.strip(), []
        elif head is not None:
            buf.append(line)
    if head is not None:
        out.append((head, buf))
    return out


def scan():
    hits = []
    for f in sorted(glob.glob(META + "*.json")):
        try:
            x = json.load(open(f)).get("data", {})
        except Exception:
            continue
        cols = [str(v.get("name")) for v in (x.get("variables") or []) if v.get("name")]
        if not cols:
            continue
        targets = {str(v["name"]) for v in x["variables"]
                   if str(v.get("role", "")).lower() == "target" and v.get("name")}
        tc = x.get("target_col")
        for t in (tc if isinstance(tc, list) else [tc]):
            if isinstance(t, str):
                targets.add(t)
        ai = x.get("additional_info") or {}
        for field, txt in list(ai.items()) + [("abstract", x.get("abstract") or "")]:
            if not isinstance(txt, str) or "\n" not in txt:
                continue
            for head, body in blocks(txt):
                if not OUTCOME_HEAD.search(head):
                    continue
                btxt = "\n".join(body)
                # Do NOT drop role=Target columns here.  UCI marks all twelve
                # of 579's complications as Target because the dataset is
                # multi-target; dropping them emptied the one block this pass
                # exists to find.  Which column is OUR target is a decision
                # made per dataset downstream, not a property of the archive.
                named = [c for c in cols
                         if len(c) >= 2
                         and re.search(rf"(?<![A-Za-z0-9_]){re.escape(c)}"
                                       rf"(?![A-Za-z0-9_])", btxt)]
                if not named:
                    continue
                hits.append(dict(
                    uci_id=x.get("uci_id"), dataset=x.get("name"), field=field,
                    heading=head, n_lines=len(body), columns=named,
                    uci_role_target=[c for c in named if c in targets],
                    excerpt=btxt[:300]))
    return hits


if __name__ == "__main__":
    hits = scan()
    with open(OUT, "w") as fh:
        for h in hits:
            fh.write(json.dumps(h) + "\n")
    print(f"{len(hits)} outcome-headed blocks -> {OUT}\n")
    for h in sorted(hits, key=lambda h: -len(h["columns"]))[:25]:
        print(f"{h['uci_id']:>5}  {str(h['dataset'])[:34]:<36}{len(h['columns']):>4}  "
              f"{h['heading'][:60]}")
        print(f"          {', '.join(h['columns'][:12])}")
