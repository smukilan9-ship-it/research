"""Harvest Kaggle dataset metadata for Stratum C -- the blind validation set.

WHY KAGGLE, AND WHY IT IS NOT MORE OF THE SAME
  Stratum A and B both come from curated academic repositories, where a
  dataset is documented by the people who collected it, in a codebook, for an
  archive with submission standards.  Kaggle is a different documentation
  culture entirely: descriptions are written by uploaders, in markdown, for
  an audience of competitors.  If the detection result only holds on archive
  prose, that is a fact about archive prose.

WHY THE SIEVE IS NOT TOUCHED
  This runs explicit_scan's WARN and DEFINE families and cond_scan's CONDSET
  family EXACTLY as they were frozen.  Not one pattern is added, removed or
  tuned for Kaggle, even where a miss is visible.  Two things follow:

    1. Any positive it finds is source-licensed on the same terms as Stratum
       B -- the uploader's own sentence names the column.
    2. The yield is a second, independent measurement of how often anyone
       documents feature-level target leakage, in a population that shares no
       curation process with the first.  §4.3 currently rests on one
       population.  This is the replication of that measurement.

  The sieve will do worse here, because it was written against archive prose
  and Kaggle prose is not archive prose.  That is a finding, not a bug, and
  it is reported rather than repaired.

WHAT THIS FILE DOES NOT DO
  It does not code anything.  It collects candidate sentences.  Admission to
  Stratum C requires the same record as everywhere else, and for Kaggle the
  intended route is the uploader's own statement, never my reading of a
  column name.
"""
import json, os, re, sys, subprocess, time, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "kaggle_meta/"
CAND = HERE + "kaggle_candidates.jsonl"
CURL = HERE + "kaggle.curl"          # 0600, holds the bearer header
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, HERE)
import explicit_scan as E
import cond_scan as C

# Broad, deliberately generic queries.  Narrow ones ("readmission", "churn")
# would select for the domains where I already expect leakage, which is the
# selection bias the whole two-strata design exists to avoid.
QUERIES = [
    "classification", "prediction", "binary classification", "risk",
    "outcome", "diagnosis", "failure", "fraud", "churn", "default",
    "survival", "readmission", "recurrence", "attrition", "conversion",
    "screening", "detection", "medical", "clinical", "patient",
    "customer", "loan", "credit", "insurance", "maintenance",
    "student", "employee", "manufacturing", "sensor", "quality",
]
PAGES = 5          # 20 per page


class Throttled(Exception):
    """Raised when the API rate-limits us.

    This exists because the first version could not tell a throttled call from
    an empty result.  Seven consecutive queries returned HTTP 429, every one
    was counted as "this query has no more datasets", the index froze at 1,281,
    and the run reported success.  A sieve that reports zero because it was
    blocked, in the same words it uses to report zero because it looked and
    found nothing, is worse than a sieve that crashes."""


def api(url, tries=6):
    """One authenticated GET, with the HTTP status inspected.

    The token lives in a 0600 curl config file passed with -K, so it never
    appears in the process table or in any log line this script writes."""
    cmd = ["curl", "-sS", "-L", "--max-time", "90", "-K", CURL,
           "-w", "\n%{http_code}", url]
    for i in range(tries):
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0 and "\n" in p.stdout:
            body, _, code = p.stdout.rpartition("\n")
            code = code.strip()
            if code == "200":
                return body
            if code == "429":
                # exponential backoff, generous: being slow is free, being
                # wrong about the denominator is not
                wait = min(120, 10 * 2 ** i)
                print(f"    429 -- backing off {wait}s", flush=True)
                time.sleep(wait)
                continue
            if code in ("403", "404"):
                return ""            # genuinely absent or not ours to read
        time.sleep(2 ** i)
    raise Throttled(url)


def harvest():
    seen, incomplete = {}, []
    for q in QUERIES:
        for page in range(1, PAGES + 1):
            u = ("https://www.kaggle.com/api/v1/datasets/list"
                 f"?search={q.replace(' ', '+')}&fileType=csv&page={page}")
            try:
                rows = json.loads(api(u) or "[]")
            except Throttled:
                print(f"    [{q} p{page}] THROTTLED OUT -- query incomplete",
                      flush=True)
                incomplete.append((q, page))
                break
            except Exception:
                rows = []
            if not rows:
                break
            # The API does not always return a list of objects.  A throttled
            # or errored call comes back as a bare string, and indexing it as
            # a dict kills the harvest 24 queries in -- which is exactly what
            # happened, losing 1,947 records that had already been fetched.
            bad = 0
            for r in rows:
                if isinstance(r, dict) and r.get("ref"):
                    seen[r["ref"]] = r
                else:
                    bad += 1
            if bad:
                print(f"    [{q} p{page}] {bad} non-object row(s) ignored",
                      flush=True)
            time.sleep(0.4)
        print(f"  {q:<24}{len(seen):>6} unique so far", flush=True)
        # checkpoint every query, so a crash costs one query and not all of them
        json.dump(list(seen.values()), open(OUT + "index.json", "w"))
    json.dump(list(seen.values()), open(OUT + "index.json", "w"))
    print(f"\n{len(seen)} unique Kaggle datasets indexed")
    if incomplete:
        print(f"WARNING: {len(incomplete)} query/page(s) throttled out and are "
              f"NOT in the index:\n  {incomplete}")
        print("The index is a floor, not a census.  Any rate computed from it "
              "must say so.")
    return list(seen.values())


def enrich(rows, sample=None, seed=20260815):
    """Phase two: fetch each dataset's FULL record.

    The list endpoint returns an empty `description` and no file schema.  The
    first run scanned titles and 50-character subtitles, found one candidate
    sentence in 1,281 datasets, and would have supported the headline "Kaggle
    documents leakage far less than the archives" -- a finding produced
    entirely by an empty field.  Descriptions have to be fetched one at a
    time, so the population is sampled and the sample size is declared."""
    import random
    todo = list(rows)
    if sample and sample < len(todo):
        random.Random(seed).shuffle(todo)
        todo = todo[:sample]
        print(f"enriching a RANDOM SAMPLE of {len(todo)} of {len(rows)} "
              f"(seed {seed}), because the description endpoint is rate-limited")
    cache = {}
    cp = OUT + "full.json"
    if os.path.exists(cp):
        cache = json.load(open(cp))
        print(f"  {len(cache)} already cached")
    done = 0
    for r in todo:
        ref = r["ref"]
        if ref in cache:
            continue
        try:
            body = api(f"https://www.kaggle.com/api/v1/datasets/view/{ref}")
        except Throttled:
            print(f"  THROTTLED after {len(cache)} enriched -- stopping "
                  f"cleanly, rerun to continue", flush=True)
            break
        if body:
            try:
                cache[ref] = json.loads(body)
            except Exception:
                pass
        done += 1
        if done % 25 == 0:
            json.dump(cache, open(cp, "w"))
            print(f"  enriched {len(cache)}", flush=True)
        time.sleep(1.2)
    json.dump(cache, open(cp, "w"))
    nd = sum(1 for v in cache.values() if (v.get("description") or "").strip())
    print(f"\nenriched {len(cache)} datasets; {nd} have a non-empty "
          f"description")
    out = []
    for r in rows:
        v = cache.get(r["ref"])
        if v:
            m = dict(r); m.update(v); out.append(m)
    return out


def texts(r):
    """Every prose field Kaggle gives us for a dataset."""
    for k in ("title", "subtitle", "description"):
        v = r.get(k)
        if isinstance(v, str) and v.strip():
            yield k, v


def colnames(r):
    """Column names, where the listing exposes a schema."""
    out = []
    for f in (r.get("files") or []):
        for c in ((f.get("columns") or []) if isinstance(f, dict) else []):
            n = c.get("name") if isinstance(c, dict) else None
            if n:
                out.append(str(n))
    return out


def scan(rows):
    hits, per = [], collections.Counter()
    for r in rows:
        cols = colnames(r)
        # Kaggle's listing rarely carries a schema; without column names the
        # sieve cannot anchor a sentence to a column, so those datasets are
        # counted as swept-but-unanchorable rather than silently skipped.
        for field, txt in texts(r):
            for sent in C._sents(txt):
                w = E.WARN.search(sent)
                d = E.DEFINE.search(sent)
                cd = C.COND.search(sent) and C.ASSIGN_GENERIC.search(sent)
                if not (w or d or cd):
                    continue
                named = E.mentions(sent, cols) if cols else []
                hits.append(dict(ref=r["ref"], title=r.get("title"),
                                 field=field, sentence=sent.strip(),
                                 family="WARN" if w else ("DEFINE" if d
                                                          else "CONDSET"),
                                 trigger=(w or d or cd).group(0)[:60],
                                 columns_named=named,
                                 has_schema=bool(cols)))
                per[r["ref"]] += 1
    with open(CAND, "w") as fh:
        for h in hits:
            fh.write(json.dumps(h) + "\n")
    nsch = sum(1 for r in rows if colnames(r))
    print(f"\nswept {len(rows)} datasets  ({nsch} expose a column schema)")
    print(f"{len(hits)} candidate sentences across {len(per)} datasets "
          f"-> {CAND}")
    print(f"  families: "
          f"{dict(collections.Counter(h['family'] for h in hits))}")
    print(f"  with a column name anchored: "
          f"{sum(1 for h in hits if h['columns_named'])}")
    print()
    for ref, n in per.most_common(30):
        t = next(h["title"] for h in hits if h["ref"] == ref)
        print(f"  {n:>3}  {str(t)[:44]:<46}{ref}")


if __name__ == "__main__":
    rows = (json.load(open(OUT + "index.json"))
            if "--cached" in sys.argv and os.path.exists(OUT + "index.json")
            else harvest())
    n = next((int(a.split("=")[1]) for a in sys.argv
              if a.startswith("--sample=")), None)
    rows = enrich(rows, sample=n)
    if not rows:
        sys.exit("nothing enriched; refusing to report a yield from titles "
                 "alone (see enrich() docstring)")
    scan(rows)
