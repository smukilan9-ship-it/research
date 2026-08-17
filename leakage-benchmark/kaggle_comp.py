"""Sweep every Kaggle competition for Stratum C -- and record what the API
will not give us, because that ceiling is the whole story here.

WHY COMPETITIONS SHOULD BE THE BEST SOURCE AND ARE NOT

  Competitions are where leakage is discussed most seriously anywhere in
  practice: a leaking column decides a leaderboard, so hosts patch data
  mid-competition and announce it.  Those announcements are exactly the
  source-licensed statements Stratum C wants.

  The public API does not expose them.  `competitions/list` returns a
  one-line `description` -- "Create an AI capable of fluid intelligence" is a
  representative example, and it is the whole field.  The Overview and Data
  tabs, where the column documentation and the host's leakage notices live,
  are rendered client-side: fetching /competitions/<slug>/data returns a 5 KB
  JavaScript shell with no content in it.  `competitions/data/list/<slug>`
  returns file names with an empty `description` on every file.  A token
  without competition scope also cannot read `datasets/list/<owner>/<slug>`,
  which is the route to any data-dictionary file shipped inside a dataset.

  So this sweep runs the frozen sieve over the surface that IS available --
  every competition's title, subtitle and one-line description, across every
  category and page -- and reports the ceiling honestly.  A near-zero yield
  from a one-line description field is a fact about the field's length, NOT
  evidence that competition hosts do not document leakage.  Reporting it the
  other way round would be the most flattering mistake available here, so the
  denominator that gets printed is "competitions whose description exceeded
  200 characters", not "competitions".
"""
import json, os, re, sys, time, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "kaggle_meta/"
CURL = HERE + "kaggle.curl"
IDX = OUT + "comps.json"
CAND = HERE + "kaggle_comp_candidates.jsonl"

sys.path.insert(0, HERE)
import explicit_scan as E
import cond_scan as C

CATEGORIES = ["all", "featured", "research", "recruitment", "gettingStarted",
              "masters", "playground", "analytics", "community"]
GROUPS = ["general", "entered", "inClass"]
PAGES = 30


def get(url):
    p = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "60", "-K", CURL,
         "-w", "\n%{http_code}", url], capture_output=True, text=True)
    if p.returncode != 0 or "\n" not in p.stdout:
        return None, "curl"
    body, _, code = p.stdout.rpartition("\n")
    return body, code.strip()


def index():
    comps = json.load(open(IDX)) if os.path.exists(IDX) else {}
    for cat in CATEGORIES:
        for page in range(1, PAGES + 1):
            u = ("https://www.kaggle.com/api/v1/competitions/list"
                 f"?page={page}" + (f"&category={cat}" if cat != "all" else ""))
            body, code = get(u)
            if code == "429":
                time.sleep(20)
                body, code = get(u)
            if code != "200":
                print(f"  {cat} p{page}: HTTP {code}", flush=True)
                break
            try:
                rows = json.loads(body)
            except Exception:
                break
            if not rows:
                break
            for r in rows:
                if isinstance(r, dict) and r.get("ref"):
                    comps[r["ref"]] = r
            time.sleep(0.5)
        print(f"  {cat:<16}{len(comps):>6} competitions", flush=True)
        json.dump(comps, open(IDX, "w"))
    return comps


def sieve(comps=None):
    comps = comps if comps is not None else json.load(open(IDX))
    hits, per = [], collections.Counter()
    lens = []
    for ref, c in comps.items():
        txt = " ".join(str(c.get(k) or "") for k in
                       ("title", "subtitle", "description"))
        lens.append(len(txt))
        for field in ("title", "subtitle", "description"):
            t = c.get(field)
            if not isinstance(t, str) or not t.strip():
                continue
            for sent in C._sents(t):
                w = E.WARN.search(sent)
                df = E.DEFINE.search(sent)
                cd = C.COND.search(sent) and C.ASSIGN_GENERIC.search(sent)
                if not (w or df or cd):
                    continue
                hits.append(dict(ref=ref, title=c.get("title"), field=field,
                                 sentence=sent.strip()[:400],
                                 family="WARN" if w else
                                        ("DEFINE" if df else "CONDSET"),
                                 trigger=(w or df or cd).group(0)[:60]))
                per[ref] += 1
    with open(CAND, "w") as fh:
        for h in hits:
            fh.write(json.dumps(h) + "\n")
    lens.sort()
    substantive = sum(1 for x in lens if x > 200)
    print(f"\n{len(comps)} competitions indexed")
    print(f"  median description length {lens[len(lens)//2] if lens else 0} "
          f"chars; "
          f"{substantive} have more than 200 characters of prose")
    print(f"  THE CEILING: the API exposes a one-line description only.  A "
          f"low yield here is a fact about that field, not about hosts.")
    print(f"{len(hits)} surviving sentences across {len(per)} competitions\n")
    for ref, n in per.most_common(50):
        h0 = next(h for h in hits if h["ref"] == ref)
        print(f"  [{n}] {h0['title']}  {ref}")
        for h in hits:
            if h["ref"] != ref:
                continue
            print(f"      ({h['family']}/{h['trigger']!r}) {h['sentence'][:200]}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sieve":
        sieve()
    else:
        sieve(index())
