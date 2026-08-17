"""Sweep OpenML for Stratum C.  Third documentation culture, and the only
source that hands us the column list for free.

WHY OPENML BELONGS IN STRATUM C EVEN THOUGH IT IS AN ARCHIVE

  The stated rationale for Kaggle was that Stratum A and B share one
  documentation culture, so a Kaggle-only validation set tests whether the
  result is a fact about archive prose.  OpenML tests a different thing and it
  is worth having both:

    Kaggle  -- different prose, uploader-written, no schema exposed.
    OpenML  -- archive prose again, BUT the datasets were chosen by other
               people for other reasons, and the schema is machine-readable.

  So OpenML is not a test of prose culture; it is a test of dataset SELECTION.
  Stratum A's fifteen tables were picked by this project.  OpenML's were not.
  If the detection numbers only hold on tables I chose, this is where it shows,
  and no amount of Kaggle prose would have told us.

WHY THE SCHEMA MATTERS MORE THAN IT SOUNDS

  The expected dominant failure on Kaggle was
  ANCHORING, not triggering -- a sentence survives the language test and then
  has no column name to attach to, because Kaggle listings rarely expose a
  header.  OpenML's /data/features/{id} returns every column name, typed, for
  every dataset.  That removes the anchoring failure entirely for this source,
  which means OpenML measures the TRIGGER rate cleanly while Kaggle measures
  the compound rate.  Reporting them separately is the point, not a nuisance.

WHAT IS NOT TOUCHED

  The sieve.  explicit_scan's WARN and DEFINE and cond_scan's CONDSET, exactly
  as frozen, on sentences from the dataset description.  No pattern is added
  for OpenML.  Mirror detection is by column content against Stratum A and B,
  which matters here far more than on Kaggle: OpenML re-hosts most of UCI, so
  a name-based check would let half of Stratum A back in through the side
  door.
"""
import json, os, re, sys, time, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "openml_meta/"
os.makedirs(OUT, exist_ok=True)
DESC = OUT + "desc.json"
FEAT = OUT + "features.json"
DEAD = OUT + "dead.json"
# NOT "openml_candidates.jsonl" -- that name belongs to openml_scan.py, whose
# output §4.3 reports.  A smoke test of this file's sieve() overwrote the real
# 89-sentence file with 2 records from a one-dataset fixture, and the paper
# number silently became "2 across 1 datasets" until the NUMBERS diff caught it.
CAND = HERE + "openml_reharvest_candidates.jsonl"

sys.path.insert(0, HERE)
import explicit_scan as E
import cond_scan as C

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
BASE = "https://www.openml.org/api/v1/json"


def get(url, tries=5):
    for i in range(tries):
        p = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "60", "-A", UA,
             "-w", "\n%{http_code}", url],
            capture_output=True, text=True)
        if p.returncode == 0 and "\n" in p.stdout:
            body, _, code = p.stdout.rpartition("\n")
            code = code.strip()
            if code == "200":
                return body, "200"
            if code in ("429", "503", "502"):
                time.sleep(min(60, 4 * 2 ** i))
                continue
            return body, code
        time.sleep(2 * (i + 1))
    return None, "retries"


def index():
    """Every active dataset id.  Paged, because the API caps a listing."""
    ids, off, step = {}, 0, 1000
    while True:
        body, code = get(f"{BASE}/data/list/status/active/"
                         f"limit/{step}/offset/{off}")
        if code != "200":
            print(f"  index stopped at offset {off}: HTTP {code}", flush=True)
            break
        try:
            rows = json.loads(body)["data"]["dataset"]
        except Exception:
            break
        if not rows:
            break
        for r in rows:
            ids[str(r["did"])] = r.get("name")
        print(f"  indexed {len(ids)}", flush=True)
        off += step
        time.sleep(0.4)
    return ids


def main():
    ids = index()
    json.dump(ids, open(OUT + "index.json", "w"))
    print(f"{len(ids)} active OpenML datasets\n", flush=True)

    desc = json.load(open(DESC)) if os.path.exists(DESC) else {}
    feat = json.load(open(FEAT)) if os.path.exists(FEAT) else {}
    dead = json.load(open(DEAD)) if os.path.exists(DEAD) else {}
    todo = [d for d in ids if d not in desc and d not in dead]
    print(f"{len(desc)} cached, fetching {len(todo)}", flush=True)

    for n, did in enumerate(todo, 1):
        body, code = get(f"{BASE}/data/{did}")
        if code != "200":
            dead[did] = f"HTTP {code}"
        else:
            try:
                d = json.loads(body)["data_set_description"]
                desc[did] = dict(name=d.get("name"),
                                 description=d.get("description") or "",
                                 target=d.get("default_target_attribute"),
                                 url=d.get("url"),
                                 version=d.get("version"))
            except Exception as e:
                dead[did] = f"parse: {type(e).__name__}"
        # Only pull the schema when the description could possibly matter.
        # 5,900 extra calls to list columns for datasets whose prose never
        # fires is a lot of somebody's bandwidth for nothing.
        if did in desc and len(desc[did]["description"]) > 40:
            b2, c2 = get(f"{BASE}/data/features/{did}")
            if c2 == "200":
                try:
                    fs = json.loads(b2)["data_features"]["feature"]
                    if isinstance(fs, dict):
                        fs = [fs]
                    feat[did] = [f["name"] for f in fs]
                except Exception:
                    pass
        if n % 25 == 0:
            for p, o in ((DESC, desc), (FEAT, feat), (DEAD, dead)):
                json.dump(o, open(p, "w"))
            print(f"  {len(desc):>5} described  {len(feat):>5} with schema  "
                  f"{len(todo)-n:>5} left", flush=True)
        time.sleep(0.35)

    for p, o in ((DESC, desc), (FEAT, feat), (DEAD, dead)):
        json.dump(o, open(p, "w"))
    print(f"\n{len(desc)} descriptions, {len(feat)} schemas, "
          f"{len(dead)} unreachable", flush=True)
    sieve(desc, feat)


def corpus_fingerprints():
    import runner as RN
    fp = {}
    for keys in (RN.ALLSETS, RN.EXPLICIT):
        for k in keys:
            try:
                b = RN.spec_bundle(k)
            except Exception:
                continue
            cols = {c.lower() for c in b["columns"] if len(c) >= 4}
            if cols:
                fp[b["name"]] = cols
    return fp


def sieve(desc=None, feat=None):
    desc = desc if desc is not None else json.load(open(DESC))
    feat = feat if feat is not None else json.load(open(FEAT))
    fp = corpus_fingerprints()
    hits, per = [], collections.Counter()
    for did, d in desc.items():
        txt = d["description"]
        if not txt:
            continue
        cols = feat.get(did) or []
        low = {c.lower() for c in cols if len(c) >= 4}
        mir = None
        for name, ccols in fp.items():
            ov = len(low & ccols)
            if ccols and ov >= max(4, int(0.6 * len(ccols))):
                mir = f"{name} ({ov}/{len(ccols)} columns shared)"
                break
        for sent in C._sents(txt):
            w = E.WARN.search(sent)
            df = E.DEFINE.search(sent)
            cd = C.COND.search(sent) and C.ASSIGN_GENERIC.search(sent)
            if not (w or df or cd):
                continue
            named = [c for c in cols
                     if re.search(rf"(?<![A-Za-z0-9_]){re.escape(c)}"
                                  rf"(?![A-Za-z0-9_])", sent, re.I)
                     and len(c) >= 3]
            hits.append(dict(did=did, name=d["name"], target=d.get("target"),
                             sentence=sent.strip(),
                             family="WARN" if w else
                                    ("DEFINE" if df else "CONDSET"),
                             trigger=(w or df or cd).group(0)[:60],
                             has_schema=bool(cols), columns_named=named,
                             mirror=mir))
            per[did] += 1
    with open(CAND, "w") as fh:
        for h in hits:
            fh.write(json.dumps(h) + "\n")
    refs = set(per)
    mir_refs = {h["did"] for h in hits if h["mirror"]}
    anch = {h["did"] for h in hits if h["columns_named"]}
    print(f"\nscanned {len(desc)} descriptions")
    print(f"{len(hits)} surviving sentences across {len(refs)} datasets")
    print(f"  mirror of Stratum A/B (EXCLUDED)   {len(mir_refs)}")
    print(f"  anchored to a real column name     {len(anch - mir_refs)}")
    for did, n in per.most_common():
        if did in mir_refs or did not in anch:
            continue
        h0 = next(h for h in hits if h["did"] == did)
        print(f"\n  [{n}] {h0['name']}  (did {did}, target={h0['target']})")
        seen = set()
        for h in hits:
            if h["did"] != did or h["sentence"][:60] in seen:
                continue
            seen.add(h["sentence"][:60])
            tag = f" -> {h['columns_named']}" if h["columns_named"] else ""
            print(f"      ({h['family']}/{h['trigger']!r}) "
                  f"{h['sentence'][:200]}{tag}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sieve":
        sieve()
    else:
        main()
