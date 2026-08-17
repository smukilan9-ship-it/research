"""Detection-benchmark corpus: no frame filters, any dataset with documentation.

Prevalence is not being claimed here, so area / size / task filters are dropped.
The only requirement is that a positive can be EVIDENCED from documentation.
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

pros=json.load(open("uci_prose.json"))
allm={x["uci_id"]:x for x in json.load(open("uci_all.json"))}
# only requirement: SOME documentation exists to quote from
cand=[x for x in pros if x["n_desc"]>0 or x["n_in_prose"]>0]
print(f"{len(pros)} datasets with variables tables -> {len(cand)} with any documentation\n",flush=True)

out=[];hit=0;tot=0
for i,x in enumerate(cand,1):
    try: d=get(f"https://archive.ics.uci.edu/api/dataset?id={x['uci_id']}")["data"]
    except Exception: continue
    V=d.get("variables") or []
    names=[str(v.get("name") or "") for v in V]
    ai=d.get("additional_info") or {}
    prose=" ".join(str(v) for v in ai.values()) if isinstance(ai,dict) else str(ai)
    c={}
    for v in V:
        desc=(v.get("description") or "").strip()
        if not desc: continue
        m=[y.group(0).lower() for y in PAT.finditer(desc)]
        if m or WPAT.search(desc):
            c[v["name"]]=dict(column=v["name"],via="structured",markers=sorted(set(m)),
                              tier_hint="E2" if WPAT.search(desc) else "E1",text=desc[:300])
    for frag in re.split(r"(?<=[.;\n])\s+", prose):
        frag=re.sub(r"\s+"," ",frag).strip()
        if not frag or len(frag)>400: continue
        m=[y.group(0).lower() for y in PAT.finditer(frag)]
        w=WPAT.search(frag)
        if not (m or w): continue
        for n in names:
            if len(n)>=3 and n not in c and re.search(r"\b"+re.escape(n.lower())+r"\b",frag.lower()):
                c[n]=dict(column=n,via="prose",markers=sorted(set(m)),
                          tier_hint="E2" if w else "E1",text=frag[:300])
    if c:
        hit+=1; tot+=len(c)
        a=allm.get(x["uci_id"],{})
        out.append(dict(uci_id=x["uci_id"],name=x["name"],area=x["area"],
                        n=a.get("n"),tasks=a.get("tasks"),doi=a.get("doi"),
                        paper=a.get("paper"),n_vars=x["n_vars"],
                        candidates=list(c.values())))
    if i%60==0: print(f"  {i}/{len(cand)}  datasets_with_candidates={hit} candidates={tot}",flush=True)
out.sort(key=lambda z:-len(z["candidates"]))
json.dump(out,open("corpus_detection.json","w"),indent=1)
print(f"\nDATASETS WITH >=1 CANDIDATE: {hit}")
print(f"TOTAL CANDIDATES: {tot}")
print(f"\ntop 25 by candidate count:")
for z in out[:25]:
    print(f"  {z['uci_id']:<5}{str(z['name'])[:42]:<44}{str(z['area'])[:18]:<20}"
          f"{len(z['candidates']):>3} cand  {z['n_vars']:>4} cols")
