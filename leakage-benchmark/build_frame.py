"""PROTOCOL 3a -- build Frame A from a published benchmark suite, then run the
mechanical half of the harvest.

Frame A = OpenML-CC18 (study 99), a curated classification suite published by
Bischl et al.  Using a pre-existing, citable suite removes every "why these
datasets" argument: someone else selected them, before this paper existed.

This script does ONLY the mechanical work:
  * fetch the suite membership, in the suite's own order
  * fetch each dataset's name, citation, licence, source URL, description
  * fetch each dataset's real column list
  * run the regex sieve over whatever documentation text exists
  * emit a REVIEW QUEUE

It does NOT decide whether a column is label-derived.  That judgment is
reserved for a human by PROTOCOL 4, because the models this corpus will be
used to evaluate must not have authored the ground truth they are scored
against.  The queue is the handoff point.
"""
import json, re, sys, time, urllib.request, urllib.error, os

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
API = "https://api.openml.org/api/v1/json"
SUITE = 99                      # OpenML-CC18
UA = {"User-Agent": "provenance-corpus-research/0.1"}

sys.path.insert(0, HERE)
from screen import PAT, WPAT    # the same sieve used on data dictionaries


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def suite_datasets(sid):
    d = json.loads(get(f"{API}/study/{sid}"))["study"]
    ids = d["data"]["data_id"]
    return d.get("alias", str(sid)), d.get("name", ""), [int(x) for x in ids]


def dataset_meta(did):
    d = json.loads(get(f"{API}/data/{did}"))["data_set_description"]
    return dict(did=did, name=d.get("name"), version=d.get("version"),
                url=d.get("url"), licence=d.get("licence"),
                citation=(d.get("citation") or "").strip(),
                collection_date=d.get("collection_date"),
                default_target=d.get("default_target_attribute"),
                description=(d.get("description") or "").strip())


def dataset_columns(did):
    try:
        f = json.loads(get(f"{API}/data/features/{did}"))["data_features"]["feature"]
    except Exception:
        return []
    if isinstance(f, dict):
        f = [f]
    return [dict(name=x.get("name"), dtype=x.get("data_type"),
                 target=x.get("is_target") == "true") for x in f]


def sieve_text(text):
    """Return sentence-ish fragments of the description that trip the sieve."""
    hits = []
    for frag in re.split(r"(?<=[.;\n])\s+", text):
        frag = re.sub(r"\s+", " ", frag).strip()
        if not frag or len(frag) > 400:
            continue
        m = [x.group(0) for x in PAT.finditer(frag)]
        w = WPAT.search(frag)
        if m or w:
            hits.append(dict(fragment=frag[:300],
                             markers=sorted({x if isinstance(x, str) else x[0]
                                             for x in m if x}),
                             tier_hint="E2" if w else "E1"))
    return hits


def main(limit=None):
    alias, sname, dids = suite_datasets(SUITE)
    if limit:
        dids = dids[:limit]
    print(f"Frame A = {alias} ({sname})", flush=True)
    print(f"  {len(dids)} datasets in the suite\n", flush=True)

    out, funnel = [], {"considered": len(dids), "meta_failed": 0,
                       "no_columns": 0, "no_description": 0,
                       "screened": 0, "with_candidates": 0}
    for i, did in enumerate(dids, 1):
        try:
            m = dataset_meta(did)
        except Exception as e:
            funnel["meta_failed"] += 1
            print(f"  [{i:>2}] did={did} METADATA FAILED {e}", flush=True)
            continue
        cols = dataset_columns(did)
        if not cols:
            funnel["no_columns"] += 1
        desc = m["description"]
        if len(desc) < 200:
            funnel["no_description"] += 1
        funnel["screened"] += 1
        cand = sieve_text(desc)
        # also sieve the column NAMES themselves -- some carry the marker
        name_hits = [c["name"] for c in cols
                     if c["name"] and PAT.search(c["name"].replace("_", " "))]
        if cand or name_hits:
            funnel["with_candidates"] += 1
        rec = dict(**m, n_columns=len(cols),
                   columns=[c["name"] for c in cols],
                   doc_candidates=cand, name_candidates=name_hits,
                   has_citation=bool(m["citation"]),
                   doc_chars=len(desc))
        out.append(rec)
        flag = "CAND" if (cand or name_hits) else "    "
        print(f"  [{i:>2}] {flag} did={did:<6} {str(m['name'])[:28]:<30}"
              f" cols={len(cols):<4} doc={len(desc):<6}"
              f" cite={'y' if m['citation'] else 'n'}"
              f" hits={len(cand)}/{len(name_hits)}", flush=True)

    json.dump(dict(frame=alias, suite=SUITE, funnel=funnel, datasets=out),
              open(HERE + "frame_a.json", "w"), indent=1)
    print("\nFUNNEL")
    for k, v in funnel.items():
        print(f"  {k:<18}{v}")
    print(f"\nwrote {HERE}frame_a.json")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
