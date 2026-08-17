"""Download every UCI dataset's metadata record.

WHY ALL OF THEM, AND WHY THIS IS NOT THE DICTIONARY RULE AGAIN

  closed_rule.py read `variables[].description` and nothing else.  That is the
  wrong place to look.  The single most-cited explicit leakage warning in the
  archive -- Bank Marketing's "duration ... should be discarded if the
  intention is to have a realistic predictive model" -- and the second most
  cited -- Student Performance's note about G1/G2 -- both live in PROSE
  (`abstract`, `additional_info.summary`, `additional_info.variable_info`),
  not in a per-variable description field.  A rule that reads only the
  dictionary is structurally blind to exactly the statements we want.

  So this downloads the whole record for every dataset and the scan runs over
  every text field in it.  We are not classifying columns from descriptions.
  We are LOOKING FOR SOURCES THAT ALREADY NAME THE LEAK.
"""
import json, os, sys, urllib.request, concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
META = HERE + "ucimeta/"
os.makedirs(META, exist_ok=True)


def one(i):
    p = f"{META}{i}.json"
    if os.path.exists(p) and os.path.getsize(p) > 200:
        return "cached"
    try:
        with urllib.request.urlopen(
                f"https://archive.ics.uci.edu/api/dataset?id={i}", timeout=45) as r:
            b = r.read()
        d = json.loads(b)
        if d.get("status") != 200 or not d.get("data"):
            return "empty"
        open(p, "wb").write(b)
        return "ok"
    except Exception as e:
        return type(e).__name__


if __name__ == "__main__":
    idx = json.load(urllib.request.urlopen(
        "https://archive.ics.uci.edu/api/datasets/list", timeout=60))["data"]
    ids = [d["id"] for d in idx]
    print(f"{len(ids)} datasets in the archive index")
    import collections
    c = collections.Counter()
    with cf.ThreadPoolExecutor(8) as ex:
        for i, r in zip(ids, ex.map(one, ids)):
            c[r] += 1
    print(dict(c))
