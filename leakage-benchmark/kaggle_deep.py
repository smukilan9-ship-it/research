"""Deeper Kaggle sweep for Stratum C, restricted to REAL datasets.

WHAT CHANGED FROM kaggle_harvest.py

  1. Roughly four times the query surface and twice the depth.  The first
     sweep's 1,281 datasets came from 30 queries capped at 5 pages, and its
     last seven queries were throttled out entirely, so that index was a floor
     and was reported as one.

  2. SYNTHETIC DATASETS ARE EXCLUDED.  The first sweep's only two admissible
     candidates were both synthetic -- one publishing its own generative
     formula, one with a section headed "Special Column (Intentional Leakage
     Risk)".  Both give exact ground truth, and both are easier than reality:
     a generator that plants a leak also documents it perfectly, which is
     precisely the condition that does not hold in the field.  A validation
     set made of them would answer a question nobody asked.

  3. MIRROR DETECTION IS BY CONTENT, NOT NAME.  Registered construction rule 3
     said so, and the first sweep proved why: "ML Marathon Dataset by Azure
     Developer Community" is Bank Marketing's description copied verbatim, and
     shares no substring with any name in the corpus.  Twelve of that sweep's
     46 hits were re-uploads of datasets already in Stratum A or B.  Scoring
     models on those and calling it validation would be scoring them on
     training data.

  The sieve itself is STILL FROZEN.  Not one pattern is added, removed or
  tuned.  Only the population changes.
"""
import json, os, re, sys, subprocess, time, collections, random

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "kaggle_meta/"
CAND = HERE + "kaggle_deep_candidates.jsonl"
CURL = HERE + "kaggle.curl"

sys.path.insert(0, HERE)
import explicit_scan as E
import cond_scan as C
from kaggle_harvest import api, Throttled

QUERIES = [
    # outcomes and events
    "classification", "prediction", "binary classification", "risk",
    "outcome", "diagnosis", "failure", "fraud", "churn", "default",
    "survival", "readmission", "recurrence", "attrition", "conversion",
    "screening", "detection", "mortality", "relapse", "complication",
    "adverse event", "dropout", "delinquency", "bankruptcy", "claim",
    # domains
    "medical", "clinical", "patient", "hospital", "icu", "oncology",
    "cardiology", "diabetes", "sepsis", "customer", "loan", "credit",
    "insurance", "maintenance", "student", "employee", "manufacturing",
    "sensor", "quality", "telecom", "retail", "marketing", "hr analytics",
    "supply chain", "logistics", "energy", "agriculture", "education",
    # documentation-shaped terms, where codebooks live
    "codebook", "data dictionary", "variable description", "cohort",
    "registry", "longitudinal", "follow-up", "electronic health record",
    "survey", "census", "administrative data", "audit", "inspection",
]
PAGES = 10

SYNTH = re.compile(
    r"\b(synthetic|synthesised|synthesized|simulat\w+|artificially "
    r"(?:generated|created)|fictional|fake data|generated using (?:faker|"
    r"numpy|python|a script|gpt)|randomly generated|toy dataset|"
    r"dummy data|mock data|not real (?:patient )?data|does not represent "
    r"real)\b", re.I)


def is_synthetic(d):
    t = " ".join(str(d.get(k) or "") for k in ("title", "subtitle",
                                               "description"))
    m = SYNTH.search(t)
    return m.group(0) if m else None


def corpus_fingerprints():
    """Distinctive column-name sets for every dataset already in A or B.

    Content, not name: a re-upload keeps the columns and changes everything
    else."""
    import runner as RN
    fp = {}
    for keys in (RN.ALLSETS, RN.EXPLICIT):
        for k in keys:
            try:
                b = RN.spec_bundle(k)
            except Exception:
                continue
            cols = {c.lower() for c in b["columns"] if len(c) >= 4}
            if cols:
                fp[b["name"]] = cols
    return fp


_SPLIT = re.compile(r"[^a-z0-9_]+")
_PLAIN = re.compile(r"^[a-z0-9_]+$")
_PAT = {}


def mirrors(d, fp):
    """Does this description name enough of a corpus dataset's columns?

    The membership test is a token-boundary match, and for a column name that
    is entirely [a-z0-9_] -- every one in the corpus -- that is exactly
    membership in the haystack split on the same class.  So the haystack is
    split ONCE and the columns are looked up, instead of the haystack being
    rescanned by a freshly compiled regex once per column name.

    The old form built the pattern string inline, so re's 512-entry compile
    cache thrashed against the corpus's ~650 distinct column names and every
    call recompiled.  py-spy caught the Kaggle sieve at 100% CPU for ten
    minutes inside re._compiler having produced no output; the same bug in
    mirror2._has was fixed first, and this is where the time actually went.

    Behaviour is unchanged -- verified by replaying 1,500 cached Kaggle records
    through both code paths and requiring identical verdicts -- and no pattern
    is added, removed or retuned, so the frozen-sieve guarantee holds."""
    t = (str(d.get("description") or "") + " " +
         str(d.get("title") or "")).lower()
    toks = set(_SPLIT.split(t))
    for name, cols in fp.items():
        hit = 0
        for c in cols:
            if _PLAIN.match(c):
                hit += c in toks
            else:
                p = _PAT.get(c)
                if p is None:
                    p = _PAT[c] = re.compile(
                        rf"(?<![a-z0-9_]){re.escape(c)}(?![a-z0-9_])")
                hit += p.search(t) is not None
        if hit >= max(4, int(0.25 * len(cols))):
            return f"{name} ({hit}/{len(cols)} column names present)"
    return None


def main():
    seen, incomplete = {}, []
    cp = OUT + "deep_index.json"
    if os.path.exists(cp):
        seen = {r["ref"]: r for r in json.load(open(cp))}
        print(f"resuming with {len(seen)} indexed")
    for q in QUERIES:
        for page in range(1, PAGES + 1):
            u = ("https://www.kaggle.com/api/v1/datasets/list"
                 f"?search={q.replace(' ', '+')}&fileType=csv&page={page}")
            try:
                rows = json.loads(api(u) or "[]")
            except Throttled:
                incomplete.append((q, page)); break
            except Exception:
                rows = []
            if not rows:
                break
            for r in rows:
                if isinstance(r, dict) and r.get("ref"):
                    seen.setdefault(r["ref"], r)
            time.sleep(0.35)
        print(f"  {q:<26}{len(seen):>6}", flush=True)
        json.dump(list(seen.values()), open(cp, "w"))
    print(f"\n{len(seen)} unique datasets indexed"
          + (f"; {len(incomplete)} query/page(s) THROTTLED OUT and missing"
             if incomplete else ""))

    # ------------------------------------------------ enrich (descriptions)
    fullp = OUT + "full.json"
    cache = json.load(open(fullp)) if os.path.exists(fullp) else {}
    todo = [r for r in seen.values() if r["ref"] not in cache]
    print(f"{len(cache)} already enriched; fetching {len(todo)} more")
    for i, r in enumerate(todo):
        try:
            body = api(f"https://www.kaggle.com/api/v1/datasets/view/{r['ref']}")
        except Throttled:
            print(f"  THROTTLED after {len(cache)} -- stopping cleanly",
                  flush=True)
            break
        if body:
            try:
                cache[r["ref"]] = json.loads(body)
            except Exception:
                pass
        if i % 50 == 0:
            json.dump(cache, open(fullp, "w"))
            print(f"    enriched {len(cache)}", flush=True)
        time.sleep(1.1)
    json.dump(cache, open(fullp, "w"))

    # ------------------------------------------------------------- sieve
    fp = corpus_fingerprints()
    hits, per = [], collections.Counter()
    nsyn = nmir = 0
    scanned = 0
    for ref, d in cache.items():
        if ref not in seen:
            continue
        scanned += 1
        syn = is_synthetic(d)
        mir = mirrors(d, fp)
        for field in ("title", "subtitle", "description"):
            txt = d.get(field)
            if not isinstance(txt, str):
                continue
            for sent in C._sents(txt):
                w = E.WARN.search(sent); df = E.DEFINE.search(sent)
                cd = C.COND.search(sent) and C.ASSIGN_GENERIC.search(sent)
                if not (w or df or cd):
                    continue
                hits.append(dict(ref=ref, title=d.get("title"), field=field,
                                 sentence=sent.strip(),
                                 family="WARN" if w else ("DEFINE" if df
                                                          else "CONDSET"),
                                 trigger=(w or df or cd).group(0)[:60],
                                 synthetic=syn, mirror=mir))
                per[ref] += 1
    with open(CAND, "w") as fh:
        for h in hits:
            fh.write(json.dumps(h) + "\n")
    refs = set(per)
    syn_refs = {h["ref"] for h in hits if h["synthetic"]}
    mir_refs = {h["ref"] for h in hits if h["mirror"]}
    real = refs - syn_refs - mir_refs
    print(f"\nscanned {scanned} enriched datasets")
    print(f"{len(hits)} candidate sentences across {len(refs)} datasets")
    print(f"  synthetic (EXCLUDED)          {len(syn_refs)}")
    print(f"  re-upload of Stratum A/B      {len(mir_refs)}")
    print(f"  REAL and new                  {len(real)}")
    print(f"\nreal candidates, most sentences first:")
    for ref, n in per.most_common():
        if ref not in real:
            continue
        t = next(h["title"] for h in hits if h["ref"] == ref)
        print(f"\n  [{n}] {str(t)[:60]}   {ref}")
        seenq = set()
        for h in hits:
            if h["ref"] != ref or h["sentence"][:60] in seenq:
                continue
            seenq.add(h["sentence"][:60])
            print(f"      ({h['family']}/{h['trigger']!r}) {h['sentence'][:190]}")


if __name__ == "__main__":
    main()
