"""Sweep Hugging Face dataset cards for Stratum C.

WHY, AND WHAT TO EXPECT

  Fourth documentation culture: a dataset card is a README written by a model
  developer for people who will load the table with `datasets.load_dataset`,
  not by a collector for an archive and not by an uploader for competitors.
  If any population documents columns differently again, it is this one.

  The expected yield is LOW and that is worth saying before the run rather
  than after.  Hugging Face is overwhelmingly text and vision; only 37
  datasets carry the `tabular-classification` tag.  Most cards that do exist
  describe splits and licences, not columns.  A near-zero result here is a
  real measurement of how rarely feature-level leakage is documented outside
  archives, which is the same measurement §4.3 makes -- it only reads as a
  failure if you went in expecting a haul.

  So the tag filter is used as a floor, not a ceiling: the sweep also runs the
  same generic keyword queries as the Kaggle sweep, so the population is
  comparable across sources and is not selected for the answer.

THE CARD, NOT THE API BLURB

  `?full=true` returns a `description` that is usually the first line of the
  card and sometimes empty.  The column documentation, where it exists at all,
  lives further down README.md.  This fetches the raw README for every
  candidate and sieves that.  Fetching the blurb would have been four times
  faster and would have measured almost nothing.
"""
import json, os, re, sys, time, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "hf_meta/"
os.makedirs(OUT, exist_ok=True)
IDX = OUT + "index.json"
CARDS = OUT + "cards.json"
DEAD = OUT + "dead.json"
CAND = HERE + "hf_candidates.jsonl"

sys.path.insert(0, HERE)
import explicit_scan as E
import cond_scan as C

TAGS = ["tabular-classification", "tabular-regression", "tabular"]
# identical to the Kaggle sweep's list, so the two populations are comparable
QUERIES = [
    "classification", "prediction", "risk", "outcome", "diagnosis", "failure",
    "fraud", "churn", "default", "survival", "readmission", "recurrence",
    "attrition", "screening", "detection", "mortality", "relapse",
    "adverse event", "dropout", "delinquency", "bankruptcy", "claim",
    "medical", "clinical", "patient", "hospital", "icu", "diabetes",
    "sepsis", "customer", "loan", "credit", "insurance", "maintenance",
    "student", "employee", "manufacturing", "sensor", "telecom", "retail",
    "marketing", "hr analytics", "energy", "education", "codebook",
    "data dictionary", "cohort", "registry", "longitudinal", "survey",
    "census", "electronic health record", "tabular",
]


def get(url, tries=4):
    for i in range(tries):
        p = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "45", "-w", "\n%{http_code}",
             url], capture_output=True, text=True)
        if p.returncode == 0 and "\n" in p.stdout:
            body, _, code = p.stdout.rpartition("\n")
            code = code.strip()
            if code == "200":
                return body, "200"
            if code in ("429", "503"):
                time.sleep(min(60, 5 * 2 ** i))
                continue
            return body, code
        time.sleep(2 * (i + 1))
    return None, "retries"


def index():
    ids = {}
    for kind, terms in (("filter", TAGS), ("search", QUERIES)):
        for t in terms:
            q = t.replace(" ", "%20")
            body, code = get(f"https://huggingface.co/api/datasets"
                             f"?{kind}={q}&limit=1000&full=false")
            if code != "200":
                print(f"  {kind}={t}: HTTP {code}", flush=True)
                continue
            try:
                rows = json.loads(body)
            except Exception:
                continue
            for r in rows:
                if r.get("id"):
                    ids.setdefault(r["id"], r.get("downloads", 0))
            print(f"  {kind}={t:<26}{len(ids):>7}", flush=True)
            time.sleep(0.3)
    return ids


def main():
    ids = index()
    json.dump(ids, open(IDX, "w"))
    print(f"\n{len(ids)} unique HF datasets indexed\n", flush=True)

    cards = json.load(open(CARDS)) if os.path.exists(CARDS) else {}
    dead = json.load(open(DEAD)) if os.path.exists(DEAD) else {}
    todo = [i for i in ids if i not in cards and i not in dead]
    print(f"{len(cards)} cached, fetching {len(todo)} cards", flush=True)
    for n, did in enumerate(todo, 1):
        body, code = get(f"https://huggingface.co/datasets/{did}"
                         f"/raw/main/README.md")
        if code == "200" and body:
            cards[did] = body[:200000]
        else:
            dead[did] = f"HTTP {code}"
        if n % 50 == 0:
            json.dump(cards, open(CARDS, "w"))
            json.dump(dead, open(DEAD, "w"))
            print(f"  {len(cards):>6} cards  {len(dead):>5} missing  "
                  f"{len(todo)-n:>6} left", flush=True)
        time.sleep(0.2)
    json.dump(cards, open(CARDS, "w"))
    json.dump(dead, open(DEAD, "w"))
    print(f"\n{len(cards)} cards, {len(dead)} without a README", flush=True)
    sieve(cards)


def sieve(cards=None):
    cards = cards if cards is not None else json.load(open(CARDS))
    hits, per = [], collections.Counter()
    for did, txt in cards.items():
        # A card is markdown with a YAML front-matter block; the block is
        # configuration, not prose, and sieving it would fire on `task_ids`
        # lists rather than on anything anybody wrote.
        body = re.sub(r"\A---\n.*?\n---\n", "", txt, flags=re.S)
        for sent in C._sents(body):
            w = E.WARN.search(sent)
            df = E.DEFINE.search(sent)
            cd = C.COND.search(sent) and C.ASSIGN_GENERIC.search(sent)
            if not (w or df or cd):
                continue
            hits.append(dict(id=did, sentence=sent.strip()[:400],
                             family="WARN" if w else
                                    ("DEFINE" if df else "CONDSET"),
                             trigger=(w or df or cd).group(0)[:60]))
            per[did] += 1
    with open(CAND, "w") as fh:
        for h in hits:
            fh.write(json.dumps(h) + "\n")
    print(f"\nscanned {len(cards)} cards")
    print(f"{len(hits)} surviving sentences across {len(per)} datasets\n")
    for did, n in per.most_common(60):
        print(f"  [{n}] {did}")
        seen = set()
        for h in hits:
            if h["id"] != did or h["sentence"][:60] in seen:
                continue
            seen.add(h["sentence"][:60])
            print(f"      ({h['family']}/{h['trigger']!r}) "
                  f"{h['sentence'][:200]}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sieve":
        sieve()
    else:
        main()
