"""Sweep the UCI archive, record every dataset's metadata, apply no filter yet.

Filtering happens afterwards from the saved file, so the thresholds are visible
and changeable without re-fetching -- and so the funnel can be reported exactly.
"""
import json, time, urllib.request, os
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
UA = {"User-Agent": "provenance-corpus-research/0.1"}

def get(u, tries=3):
    for i in range(tries):
        try:
            return json.loads(urllib.request.urlopen(
                urllib.request.Request(u, headers=UA), timeout=40).read())
        except Exception:
            if i == tries - 1: raise
            time.sleep(1.5 ** i)

lst = get("https://archive.ics.uci.edu/api/datasets/list")["data"]
print(f"archive lists {len(lst)} datasets", flush=True)
out, fail = [], 0
for i, e in enumerate(lst, 1):
    try:
        d = get(f"https://archive.ics.uci.edu/api/dataset?id={e['id']}")["data"]
    except Exception:
        fail += 1
        continue
    v = d.get("variables") or []
    ndesc = sum(1 for x in v if (x.get("description") or "").strip())
    out.append(dict(uci_id=d.get("uci_id"), name=d.get("name"),
                    area=d.get("area"), tasks=d.get("tasks") or [],
                    n=d.get("num_instances"), p=d.get("num_features"),
                    n_vars=len(v), n_desc=ndesc,
                    doi=d.get("dataset_doi"),
                    paper=(d.get("intro_paper") or {}).get("title"),
                    year=d.get("year_of_dataset_creation"),
                    target=d.get("target_col")))
    if i % 100 == 0:
        print(f"  {i}/{len(lst)}  ok={len(out)} fail={fail}", flush=True)
json.dump(out, open(HERE + "uci_all.json", "w"), indent=1)
print(f"done: {len(out)} fetched, {fail} failed -> uci_all.json", flush=True)
