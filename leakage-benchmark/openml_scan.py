"""Run the explicit-statement sieve over OpenML uploader prose.

DIFFERENCE FROM THE UCI PASS
  A UCI record ships its column list, so a hit can be anchored to a column
  immediately.  An OpenML `data_set_description` is free text with no column
  list attached, so anchoring needs a second request per dataset.  Making that
  request for all ~5,000 datasets to anchor a few dozen hits is wasteful, so
  the sieve runs on prose alone and the feature list is fetched ONLY for
  datasets that hit.  Nothing is labelled without an anchored column name.
"""
import json, glob, os, re, sys, collections, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from explicit_scan import WARN, DEFINE, SPLIT

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
CACHE = HERE + "openml/"
OUT = HERE + "openml_candidates.jsonl"
API = "https://www.openml.org/api/v1/json"

# Prose that is about leakage as a CONCEPT rather than about a named column is
# still worth surfacing: the uploader who writes it usually names the column in
# the next clause.
STRONG = re.compile(r"(leaka?ge|leaky|leaks? (?:the|into)|target leak|"
                    r"should be (?:removed|dropped|discarded|excluded)|"
                    r"must be (?:removed|dropped|discarded|excluded)|"
                    r"not known (?:before|at|until)|only known after|"
                    r"cheat|unrealistic|artificially)", re.I)


# Column lists, from the local harvest cache first and the API only for
# datasets the cache does not hold.  The cache was built by openml_harvest.py
# from the same /data/features endpoint, so this is the same data; going to it
# first makes the anchoring step reproducible offline.  It matters: a re-run
# with the network unavailable returned [] for all 89 datasets and silently
# dropped the one anchored hit, leaving a file that looked fine and had lost a
# result.
FEATCACHE = {}
_fc = HERE + "openml_meta/features.json"
if os.path.exists(_fc):
    FEATCACHE = json.load(open(_fc))


def features(did):
    c = FEATCACHE.get(str(did))
    if c:
        return [f["name"] if isinstance(f, dict) else f for f in c]
    try:
        d = json.load(urllib.request.urlopen(f"{API}/data/features/{did}", timeout=45))
        return [f["name"] for f in d["data_features"]["feature"]]
    except Exception:
        return []


def main():
    hits = []
    for p in glob.glob(CACHE + "*.json"):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        txt = d.get("description") or ""
        if not isinstance(txt, str) or len(txt) < 40:
            continue
        for sent in SPLIT.split(txt):
            sent = " ".join(re.sub(r"<[^>]+>", " ", sent).split())
            if not (20 <= len(sent) <= 600):
                continue
            s = STRONG.search(sent)
            w = WARN.search(sent) if s else None
            if not s:
                continue
            hits.append(dict(did=d.get("id"), name=d.get("name"),
                             trigger=s.group(0), sentence=sent,
                             warn=bool(w)))
    # anchor: fetch the column list once per hit dataset
    dids = sorted({h["did"] for h in hits})
    print(f"{len(glob.glob(CACHE+'*.json'))} descriptions scanned")
    print(f"{len(hits)} strong sentences across {len(dids)} datasets")
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(10) as ex:
        feats = dict(zip(dids, ex.map(features, dids)))
    for h in hits:
        cols = feats.get(h["did"], [])
        h["columns"] = [c for c in cols if len(c) >= 3 and
                        re.search(rf"(?<![A-Za-z0-9_]){re.escape(c)}(?![A-Za-z0-9_])",
                                  h["sentence"], re.I)]
    with open(OUT, "w") as fh:
        for h in hits:
            fh.write(json.dumps(h) + "\n")
    anch = [h for h in hits if h["columns"]]
    print(f"{len(anch)} anchored to a named column "
          f"({len({h['did'] for h in anch})} datasets) -> {OUT}\n")
    by = collections.defaultdict(list)
    for h in anch:
        by[(h["did"], h["name"])].append(h)
    for (did, name), v in sorted(by.items(), key=lambda kv: -len(kv[1]))[:30]:
        print(f"{did:>6}  {str(name)[:38]:<40}{len(v):>3}  "
              f"{','.join(sorted({c for x in v for c in x['columns']}))[:50]}")


if __name__ == "__main__":
    main()
