"""Harvest columns whose documentation EXPLICITLY states post-outcome provenance.

Not the sieve.  The sieve matched single marker words and needed a human to
judge.  This requires a full phrase in which the source itself states timing or
derivation, so the label's authority is the quoted text, not our reading of it.

A column is emitted only with the verbatim phrase that licenses it.  Anything
requiring inference ("Hospital charges" -> post-outcome iff prediction is at
day 3) is deliberately NOT emitted: that inference is what the benchmark tests.
"""
import json, re, time, urllib.request, sys, os
UA={"User-Agent":"provenance-corpus-research/0.1"}
def get(u,t=3):
    for i in range(t):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=45).read())
        except Exception:
            if i==t-1: raise
            time.sleep(1.5**i)

# each pattern must express TIMING or DERIVATION, not merely a suggestive word
EXPLICIT = [
 (r"predicted by a model",                      "DERIVED"),
 (r"\bpost[- ]charge[- ]?off\b",                "AFTER_EVENT"),
 (r"days? (?:of|from|to) follow[-\s]?up",       "AFTER_EVENT"),
 (r"follow[-\s]?up (?:period|time|days)",       "AFTER_EVENT"),
 (r"cause of death",                            "AFTER_EVENT"),
 (r"\bat discharge\b",                          "AFTER_EVENT"),
 (r"from study entry to discharge",             "AFTER_EVENT"),
 (r"(?:survival|mortality) (?:estimate|score|probability)", "DERIVED"),
 (r"\bat day \d+",                              "AFTER_EVENT"),
 (r"(?:recorded|measured|collected|assigned) after", "AFTER_EVENT"),
 (r"only .{0,25}after (?:the )?(?:outcome|event|discharge|call|charge)", "AFTER_EVENT"),
 (r"not known before",                          "WARNED"),
 (r"should (?:only be|be) (?:used|included|discarded)", "WARNED"),
 (r"realistic predictive model",                "WARNED"),
 (r"after the (?:end of the |)(?:call|outcome|event|procedure|operation)", "AFTER_EVENT"),
 (r"(?:outcome|result) of (?:the )?(?:treatment|surgery|operation|procedure)", "AFTER_EVENT"),
 (r"\bpost[- ]?operative\b",                    "AFTER_EVENT"),
 (r"\bpost[- ]?treatment\b",                    "AFTER_EVENT"),
 (r"time (?:to|until) (?:death|event|failure|relapse)", "AFTER_EVENT"),
 (r"whether the patient (?:died|survived)",     "AFTER_EVENT"),
 (r"(?:number|days) of (?:hospital )?stay",     "AFTER_EVENT"),
]
PATS=[(re.compile(p,re.I),k) for p,k in EXPLICIT]

pros=json.load(open("uci_prose.json"))
allm={x["uci_id"]:x for x in json.load(open("uci_all.json"))}
todo=[x for x in pros if x["n_desc"]>0]          # needs structured descriptions to quote
print(f"{len(todo)} datasets have structured column descriptions\n",flush=True)

out=[];ds=0;tot=0
for i,x in enumerate(todo,1):
    try: d=get(f"https://archive.ics.uci.edu/api/dataset?id={x['uci_id']}")["data"]
    except Exception: continue
    a=allm.get(x["uci_id"],{})
    hits=[]
    for v in d.get("variables") or []:
        desc=re.sub(r"\s+"," ",(v.get("description") or "")).strip()
        if not desc: continue
        for pat,kind in PATS:
            m=pat.search(desc)
            if m:
                s=max(0,m.start()-60); e=min(len(desc),m.end()+60)
                quote=desc[s:e].strip()
                hits.append(dict(column=v["name"], role=v.get("role"), kind=kind,
                                 matched=m.group(0), quote=quote, full=desc[:300]))
                break
    if hits:
        ds+=1; tot+=len(hits)
        out.append(dict(uci_id=x["uci_id"], name=x["name"], area=x["area"],
                        n=a.get("n"), doi=a.get("doi"), paper=a.get("paper"),
                        n_vars=x["n_vars"], columns=hits))
    if i%50==0: print(f"  {i}/{len(todo)}  datasets={ds} columns={tot}",flush=True)
out.sort(key=lambda z:-len(z["columns"]))
json.dump(out,open("explicit_positives.json","w"),indent=1)
print(f"\nDATASETS WITH >=1 EXPLICIT STATEMENT: {ds}")
print(f"COLUMNS WITH AN EXPLICIT QUOTE: {tot}\n")
for z in out[:30]:
    print(f"  {z['uci_id']:<5}{str(z['name'])[:40]:<42}{len(z['columns']):>3} cols  doi={'y' if z['doi'] else 'n'}")
