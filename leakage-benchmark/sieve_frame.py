"""Run the sieve over Frame A's variable descriptions -> review queue."""
import json, time, urllib.request, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from screen import PAT, WPAT
UA={"User-Agent":"provenance-corpus-research/0.1"}
def get(u,t=3):
    for i in range(t):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40).read())
        except Exception:
            if i==t-1: raise
            time.sleep(1.5**i)
frame=json.load(open("frame_a_uci.json"))
queue, tot_cols, tot_hits, with_hits = [], 0, 0, 0
for x in frame:
    d=get(f"https://archive.ics.uci.edu/api/dataset?id={x['uci_id']}")["data"]
    hits=[]
    for v in d.get("variables") or []:
        desc=(v.get("description") or "").strip()
        tot_cols+=1
        if not desc: continue
        m=[y.group(0).lower() for y in PAT.finditer(desc)]
        w=WPAT.search(desc)
        if m or w:
            hits.append(dict(column=v["name"], role=v.get("role"),
                             markers=sorted(set(m)), tier_hint="E2" if w else "E1",
                             description=desc[:400]))
    tot_hits+=len(hits); with_hits+= bool(hits)
    queue.append(dict(uci_id=x["uci_id"], name=x["name"], area=x["area"],
                      n=x["n"], doi=x["doi"], paper=x["paper"],
                      target=x.get("target"), n_vars=x["n_vars"], candidates=hits))
    print(f"  {x['uci_id']:<5}{str(x['name'])[:44]:<46}{len(hits):>3} candidates", flush=True)
json.dump(queue, open("review_queue.json","w"), indent=1)
print(f"\n{len(frame)} datasets, {tot_cols} columns")
print(f"{tot_hits} candidates flagged across {with_hits} datasets "
      f"({100*tot_hits/max(tot_cols,1):.1f}% of columns)")
print(f"datasets with zero candidates: {len(frame)-with_hits}")
