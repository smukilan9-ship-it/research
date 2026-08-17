"""Find sources that EXPLICITLY name a leaking column.

THE CHANGE OF QUESTION
  Every previous harvest asked: "does this column's description contain
  wording that, on our reading, places it after the prediction point?"  That
  makes us the judge, and PROTOCOL 4 then has to work very hard to stop our
  reading becoming the evidence.

  This asks a different and much cheaper question: "does the source itself say
  this column must not be used?"  When the answer is yes, the ground truth is
  not our inference at all -- it is a citable statement by the people who
  built the dataset.  That is the strongest label available anywhere in this
  project, and it is worth more than any tier ordering of source formality.

WHAT COUNTS AS EXPLICIT
  Two families, both requiring the source to reach a CONCLUSION about use:

  WARN   the source instructs the reader to drop / not use / be careful with a
         named attribute, or says it is unknown at prediction time
  DEFINE the source says the target was computed, assigned or derived FROM a
         named attribute

  Wording that merely describes when a value was measured is NOT explicit and
  is deliberately excluded here.  That material is what the older sieve
  already collects; mixing the two would destroy the whole point of this pass.

WHY DEFINE HAS TO KNOW THE TARGET'S NAME
  The first version required the literal words class / label / target as the
  sentence's subject and fired ZERO times in 612 datasets.  It was not that
  the archive contains no derivation statements; it is that authors write them
  with the target's OWN NAME.  Communities and Crime says "The per capita
  violent crimes variable was calculated using population and the sum of crime
  variables ... murder, rape, robbery, and assault" -- a complete, quotable
  derivation of the target from four columns that are in the table, and the
  word "target" never appears.  So the subject alternation is built per
  dataset from `target_col` and from any variable whose role is Target.

THIS IS A SIEVE, NOT A CLASSIFIER
  Deliberately over-inclusive.  A hit costs seconds of reading; a miss costs a
  source we never find.  Nothing here becomes a label -- every record still
  needs a verbatim sentence that names the column, read by a human.

SCOPE OF THE SEARCH
  Every text field of the record, not just `variables[].description`.  The
  archive's two most-cited leakage warnings (Bank Marketing `duration`,
  Student Performance `G1`/`G2`) are in prose, so a dictionary-only scan finds
  neither -- which is precisely why the closed-world rule under-fired.
"""
import json, glob, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
META = HERE + "ucimeta/"
OUT = HERE + "explicit_candidates.jsonl"

# ---------------------------------------------------------------- WARN family
# The source tells the reader not to use it, or says it is unavailable at the
# moment of prediction.  Each alternative is a conclusion, not a description.
WARN = re.compile(
    r"(should (?:be )?(?:discard|remov|drop|exclud|omit|ignor|not be used|only be used)\w*"
    r"|should not be (?:used|included|considered)"
    r"|must be (?:discard|remov|drop|exclud|omit)\w*"
    r"|(?:we|were|was|is|are) (?:therefore )?(?:discard|remov|drop|exclud|omit)\w* (?:from|because|since|as it|to avoid)"
    r"|(?:not|never) (?:known|available|recorded|measured|observed) (?:before|prior to|at the time|until after)"
    r"|only (?:known|available|obtained|determined) after"
    r"|(?:known|available|obtained) only after"
    r"|not (?:yet )?(?:known|available) (?:at|when|before)"
    r"|for benchmark purposes"
    r"|realistic predictive model"
    r"|highly affects the (?:output|target|class)"
    r"|(?:data|target|label|information) leak\w*"
    r"|leaka?ge"
    r"|circular(?:ity)?"
    r"|unrealistic\w*"
    r"|artificially (?:high|inflat\w+|good|optimistic)"
    r"|(?:perfect|trivial|100%|near[- ]perfect)\w* (?:predict|accura|classif|separ)\w*"
    r"|would (?:not )?be (?:available|known|cheating)"
    r"|cheat\w*"
    # Explicit acknowledgement that the task is trivial WITH a named attribute.
    # Student Performance states the G1/G2 problem in exactly this shape and in
    # no other, so a warn-verb-only pattern cannot see the archive's second
    # most-cited leak.
    r"|(?:difficult|hard|harder|challenging) to (?:predict|classify|model)"
    r"|(?:without|excluding|dropping|ignoring) (?:the )?(?:attribute|variable|feature|column)"
    r"|strong(?:ly)? correlat\w* with"
    r"|(?:this|which) occurs because"
    r"|(?:no|little) predictive (?:value|use|merit)"
    r"|(?:be|is|are|was|were) (?:used|useful) only (?:for|as)"
    r"|(?:before|prior to) the (?:call|outcome|event|decision|prediction)"
    r"|at the time of (?:enrol|admission|application|origination|screening)\w*)", re.I)

# -------------------------------------------------------------- DEFINE family
# The source says the target itself was built from the attribute.
DEFINE = re.compile(
    r"((?:class|label|target|outcome|diagnosis|grade|category|group)\w*\s+"
    r"(?:was|were|is|are|has been)\s+"
    r"(?:then\s+)?(?:assign|determin|deriv|comput|calculat|obtain|defin|creat|label|establish)\w*"
    r"\s+(?:by|from|using|with|according to|on the basis of|based on)"
    r"|(?:was|were|is|are) (?:used|taken) to (?:assign|determin|deriv|comput|calculat|defin|label|creat)\w*"
    r"\s+(?:the )?(?:class|label|target|outcome|diagnosis|grade|categor)"
    r"|(?:calculat|comput|deriv)\w* (?:the )?(?:class|label|target|outcome|categor)\w*"
    r"\s+(?:by|from|using|with|as)"
    r"|(?:sum|total|union|aggregate|combination) of the (?:remaining|other|above|preceding)"
    r"|one of (?:the )?(?:two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:fault|defect|class|categor|type|pattern|outcome)"
    r"|mutually exclusive"
    r"|none of (?:the|these) (?:above|other|named|six|seven)"
    r"|is set to 1 if (?:any|at least one)"
    r"|equal to the (?:sum|product|ratio|difference)"
    r"|(?:sum|total|number) of (?:the )?(?:crime|fault|defect|event|complication)\w*"
    r"|1 if (?:any|at least one|one or more)"
    r"|(?:indicator|flag|dummy) for (?:whether|the)"
    r")", re.I)

# Subject alternation for DEFINE, built per dataset from the target's own name.
DEFVERB = (r"(?:was|were|is|are|has been|have been)\s+(?:then\s+)?"
           r"(?:assign|determin|deriv|comput|calculat|obtain|defin|creat|"
           r"label|establish|set|construct|form)\w*\s+"
           r"(?:by|from|using|with|as|according to|on the basis of|based on)")


def define_named(sent, targets):
    """DEFINE where the SUBJECT is the dataset's own target column name.

    Matching is done on a window: authors put a noun phrase between the name
    and the verb ("The per capita violent crimes VARIABLE was calculated"),
    so requiring adjacency would miss almost every real statement."""
    for t in targets:
        if len(t) < 3:
            continue
        for m in re.finditer(rf"(?<![A-Za-z0-9_]){re.escape(t)}(?![A-Za-z0-9_])",
                             sent, re.I):
            w = sent[m.end(): m.end() + 90]
            mm = re.search(DEFVERB, w, re.I)
            if mm:
                return t + w[:mm.end()]
    return None


def target_names(x):
    """Every plausible name for what this dataset predicts."""
    out = set()
    tc = x.get("target_col")
    for t in (tc if isinstance(tc, list) else [tc]):
        if isinstance(t, str) and t.strip():
            out.add(t.strip())
    for v in (x.get("variables") or []):
        if str(v.get("role", "")).lower() == "target" and v.get("name"):
            out.add(str(v["name"]))
    # the human phrasing of the target, which is what prose actually uses
    out |= {re.sub(r"[_\-]+", " ", t) for t in list(out)}
    return {t for t in out if len(t) >= 3}

# Sentence splitter that survives numbered attribute lists.
SPLIT = re.compile(r"(?<=[.!?;])\s+|\n{1,}")


def texts(x):
    """(field name, text) for every prose field in a UCI record."""
    yield "abstract", x.get("abstract") or ""
    ai = x.get("additional_info") or {}
    if isinstance(ai, dict):
        for k, v in ai.items():
            if isinstance(v, str) and v.strip():
                yield f"additional_info.{k}", v
    ip = x.get("intro_paper") or {}
    if isinstance(ip, dict):
        for k in ("abstract", "title"):
            if isinstance(ip.get(k), str):
                yield f"intro_paper.{k}", ip[k]
    for v in (x.get("variables") or []):
        d = (v.get("description") or "").strip()
        if d:
            yield f"variables[{v.get('name')}]", d


def colnames(x):
    return [str(v.get("name")) for v in (x.get("variables") or []) if v.get("name")]


def mentions(sent, cols):
    """Column names appearing in the sentence, longest first so `G3` does not
    shadow `G3_grade`.  Word-bounded: `age` must not match `average`."""
    out = []
    for c in sorted(cols, key=len, reverse=True):
        if len(c) < 2:
            continue
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(c)}(?![A-Za-z0-9_])", sent):
            out.append(c)
    return out


def scan():
    hits = []
    files = sorted(glob.glob(META + "*.json"), key=lambda p: int(re.sub(r"\D", "", os.path.basename(p)) or 0))
    for f in files:
        try:
            d = json.load(open(f))
        except Exception:
            continue
        x = d.get("data", d)
        cols = colnames(x)
        if not cols:
            continue
        tnames = target_names(x)
        for field, txt in texts(x):
            for sent in SPLIT.split(txt):
                sent = " ".join(sent.split())
                if len(sent) < 15 or len(sent) > 600:
                    continue
                w = WARN.search(sent)
                v = DEFINE.search(sent) or define_named(sent, tnames)
                if not (w or v):
                    continue
                named = mentions(sent, cols)
                # a variable-level field is self-anchoring: the column is the
                # field's own subject even when the text does not repeat it
                own = re.match(r"variables\[(.+)\]$", field)
                if own and own.group(1) not in named:
                    named = [own.group(1)] + named
                if not named:
                    continue
                hits.append(dict(
                    uci_id=x.get("uci_id"), dataset=x.get("name"),
                    field=field, family="WARN" if w else "DEFINE",
                    trigger=(w.group(0) if w else
                             (v.group(0) if hasattr(v, "group") else v)),
                    columns=named[:8],
                    sentence=sent))
    return hits


if __name__ == "__main__":
    hits = scan()
    with open(OUT, "w") as fh:
        for h in hits:
            fh.write(json.dumps(h) + "\n")
    ds = {(h["uci_id"], h["dataset"]) for h in hits}
    print(f"{len(glob.glob(META+'*.json'))} metadata records scanned")
    print(f"{len(hits)} explicit sentences across {len(ds)} datasets -> {OUT}\n")
    fam = collections.Counter(h["family"] for h in hits)
    print(f"  {dict(fam)}\n")
    byds = collections.defaultdict(list)
    for h in hits:
        byds[(h["uci_id"], h["dataset"])].append(h)
    for (uid, name), v in sorted(byds.items(), key=lambda kv: -len(kv[1]))[:40]:
        print(f"{uid:>5}  {name[:44]:<46}{len(v):>4}  "
              f"{','.join(sorted({c for h in v for c in h['columns']}))[:60]}")
