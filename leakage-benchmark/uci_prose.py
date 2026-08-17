"""Does prose documentation rescue the datasets whose structured field is empty?

For each UCI dataset, measure two things:
  structured : fraction of columns with a non-empty variables[].description
  prose      : fraction of column NAMES that appear verbatim in additional_info

The prose measure is a proxy, not proof -- a name appearing in prose does not
guarantee the prose defines it. It is deliberately GENEROUS: it will overcount
documentation, so if the crisis survives this measure it is real.
"""
import json, re, time, urllib.request, os
HERE=os.path.dirname(os.path.abspath(__file__))+"/"
UA={"User-Agent":"provenance-corpus-research/0.1"}
def get(u,t=3):
    for i in range(t):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=45).read())
        except Exception:
            if i==t-1: raise
            time.sleep(1.5**i)

lst=get("https://archive.ics.uci.edu/api/datasets/list")["data"]
out=[];fail=0
for i,e in enumerate(lst,1):
    try: d=get(f"https://archive.ics.uci.edu/api/dataset?id={e['id']}")["data"]
    except Exception: fail+=1; continue
    V=d.get("variables") or []
    if not V: continue
    ai=(d.get("additional_info") or {})
    prose=" ".join(str(v) for v in ai.values()) if isinstance(ai,dict) else str(ai)
    prose_l=prose.lower()
    names=[str(v.get("name") or "") for v in V]
    # generous: a name counts as "in prose" if it appears as a word, >=3 chars
    inprose=sum(1 for n in names if len(n)>=3 and
                re.search(r"\b"+re.escape(n.lower())+r"\b", prose_l))
    out.append(dict(uci_id=d.get("uci_id"), name=d.get("name"), area=d.get("area"),
                    year=d.get("year_of_dataset_creation"),
                    n_vars=len(V),
                    n_desc=sum(1 for v in V if (v.get("description") or "").strip()),
                    prose_chars=len(prose), n_in_prose=inprose))
    if i%150==0: print(f"  {i}/{len(lst)} ok={len(out)} fail={fail}",flush=True)
json.dump(out,open(HERE+"uci_prose.json","w"),indent=1)
print(f"done: {len(out)} with variables tables, {fail} failed",flush=True)
