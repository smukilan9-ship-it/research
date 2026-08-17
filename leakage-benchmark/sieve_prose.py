"""Sieve BOTH structured variable descriptions and additional_info prose.

For prose, a candidate requires a fragment that (a) names a column and
(b) carries a temporal marker.  Pairing the two is what makes a prose hit
attributable to a specific column -- a marker floating in an abstract is not
evidence about any particular field.
"""
import json, re, time, urllib.request, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from screen import PAT, WPAT
UA={"User-Agent":"provenance-corpus-research/0.1"}
def get(u,t=3):
    for i in range(t):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=45).read())
        except Exception:
            if i==t-1: raise
            time.sleep(1.5**i)

frame=json.load(open("frame_a_v3.json"))
queue=[]; tot_s=tot_p=0; ds_hit=0
for x in frame:
    d=get(f"https://archive.ics.uci.edu/api/dataset?id={x['uci_id']}")["data"]
    V=d.get("variables") or []
    names=[str(v.get("name") or "") for v in V]
    ai=d.get("additional_info") or {}
    prose=" ".join(str(v) for v in ai.values()) if isinstance(ai,dict) else str(ai)
    cands={}
    # (a) structured descriptions
    for v in V:
        desc=(v.get("description") or "").strip()
        if not desc: continue
        m=[y.group(0).lower() for y in PAT.finditer(desc)]
        if m or WPAT.search(desc):
            cands[v["name"]]=dict(column=v["name"], via="structured",
                                  markers=sorted(set(m)),
                                  tier_hint="E2" if WPAT.search(desc) else "E1",
                                  text=desc[:300])
    ns=len(cands)
    # (b) prose fragments that name a column AND carry a marker
    for frag in re.split(r"(?<=[.;\n])\s+", prose):
        frag=re.sub(r"\s+"," ",frag).strip()
        if not frag or len(frag)>400: continue
        m=[y.group(0).lower() for y in PAT.finditer(frag)]
        w=WPAT.search(frag)
        if not (m or w): continue
        for n in names:
            if len(n)>=3 and re.search(r"\b"+re.escape(n.lower())+r"\b", frag.lower()):
                if n not in cands:
                    cands[n]=dict(column=n, via="prose", markers=sorted(set(m)),
                                  tier_hint="E2" if w else "E1", text=frag[:300])
    np_=len(cands)-ns
    tot_s+=ns; tot_p+=np_; ds_hit+= bool(cands)
    queue.append(dict(uci_id=x["uci_id"], name=x["name"], area=x["area"], n=x["n"],
                      doi=x["doi"], paper=x["paper"], n_vars=x["n_vars"],
                      candidates=list(cands.values())))
    print(f"  {x['uci_id']:<5}{str(x['name'])[:40]:<42}struct={ns:>3} prose={np_:>3}", flush=True)
json.dump(queue, open("review_queue_v3.json","w"), indent=1)
print(f"\n{len(frame)} datasets | candidates: {tot_s} structured + {tot_p} prose = {tot_s+tot_p}")
print(f"datasets with >=1 candidate: {ds_hit}/{len(frame)}   zeros: {len(frame)-ds_hit}")
