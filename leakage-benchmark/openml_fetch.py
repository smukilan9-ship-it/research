"""Cache OpenML dataset descriptions.

WHY OPENML AS WELL AS UCI
  660 UCI records yielded explicit leakage statements for a handful of
  datasets.  That number is itself a result -- documentation almost never
  warns you -- but it is not enough ground truth to score models against.
  OpenML is the other machine-readable repository of tabular datasets, its
  descriptions are free prose written by uploaders rather than a fixed
  template, and it carries the same datasets under many curated versions.
  Uploader prose is exactly where a warning like "the duration attribute must
  be removed" tends to appear.

  Formal source tier is not the selection criterion.  A statement is admitted
  because it explicitly names a column and reaches a conclusion about using
  it, whoever wrote it.
"""
import json, os, re, sys, urllib.request, urllib.error, concurrent.futures as cf, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
CACHE = HERE + "openml/"
os.makedirs(CACHE, exist_ok=True)
API = "https://www.openml.org/api/v1/json"


def get(url, timeout=45):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def one(did):
    p = f"{CACHE}{did}.json"
    if os.path.exists(p) and os.path.getsize(p) > 100:
        return "cached"
    try:
        d = get(f"{API}/data/{did}")
        json.dump(d.get("data_set_description", {}), open(p, "w"))
        return "ok"
    except urllib.error.HTTPError as e:
        json.dump({"error": e.code}, open(p, "w"))
        return f"HTTP{e.code}"
    except Exception as e:
        return type(e).__name__


if __name__ == "__main__":
    lst = get(f"{API}/data/list/status/active", timeout=180)
    ds = lst["data"]["dataset"]
    print(f"{len(ds)} active OpenML datasets")
    ids = [d["did"] for d in ds]
    if len(sys.argv) > 1:
        ids = ids[:int(sys.argv[1])]
    c = collections.Counter()
    with cf.ThreadPoolExecutor(12) as ex:
        for i, r in enumerate(ex.map(one, ids)):
            c[r] += 1
            if i % 2000 == 0:
                print(f"  {i}  {dict(c)}", flush=True)
    print(dict(c))
