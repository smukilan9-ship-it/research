"""Anchor Hugging Face candidate sentences to the real column schema.

WHY IT IS CHEAPER HERE THAN ON KAGGLE

  Kaggle exposes no schema, so anchoring meant downloading each candidate
  dataset -- tens of megabytes apiece, with a size cap and nine skips.  Hugging
  Face runs a datasets-server that returns the typed feature list for any public
  dataset over HTTP:

      /splits?dataset=X            -> the available config/split pairs
      /first-rows?dataset=X&...    -> features[], each with a name

  So the whole anchoring step is two small JSON calls per candidate and nothing
  is written to disk.  No size cap is needed, which means no skips, which means
  the denominator here is clean in a way Kaggle's cannot be.

WHAT IT SHARES WITH THE KAGGLE VERSION, DELIBERATELY

  The same token-boundary match and the same refusal to anchor on names shorter
  than three characters.  A false anchor manufactures a ground-truth record out
  of a coincidence, which is worse than a missing one, and two-character column
  names ("id", "y", "G1") match ordinary prose constantly.

  Datasets whose schema cannot be fetched are recorded as errors and reported
  separately.  A dataset that could not be checked is missing evidence; folding
  it into "no anchor found" would understate the anchoring rate and overstate
  how much was actually looked at.
"""
import json, os, re, sys, time, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
CAND = HERE + "hf_candidates.jsonl"
OUT = HERE + "hf_anchored.json"
SRV = "https://datasets-server.huggingface.co"

sys.path.insert(0, HERE)
import mirror2
from kaggle_deep import SYNTH


def get(url, tries=3):
    for i in range(tries):
        p = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "45", "-w", "\n%{http_code}",
             url], capture_output=True, text=True)
        if p.returncode == 0 and "\n" in p.stdout:
            body, _, code = p.stdout.rpartition("\n")
            code = code.strip()
            if code == "200":
                return body, "200"
            if code in ("429", "503", "502"):
                time.sleep(5 * (i + 1))
                continue
            return body, code
        time.sleep(2 * (i + 1))
    return None, "retries"


def synthetic(did, cards, configs):
    """Is this dataset generated -- and if so, ALL of it, or one config?

    The naive check cost a real record once already.  `artemlepin/chess-fraud`
    ships `chess_fraud` (real controlled tournaments) beside
    `chess_fraud_synth` (engine-generated), and the word "synthetic" appears in
    the card because of the second one.  A per-DATASET exclusion would have
    discarded a table whose `assistance_line_rank` determines the label exactly
    on all 38,510 rows.

    So this returns a verdict, not a boolean:

      None                nothing matched
      ("whole", phrase)   matched, and the dataset has no config that looks
                          generated -- treat the whole thing as synthetic
      ("scoped", phrase)  matched, but a SIBLING config is named *synth*, so
                          the match may belong to that config.  Reported, never
                          auto-excluded: the cost of a wrong exclusion here is a
                          record nobody finds again.
    """
    m = SYNTH.search(cards.get(did, ""))
    if not m:
        return None
    sibling = any(re.search(r"synth", c, re.I) for c in configs)
    return ("scoped" if sibling and len(set(configs)) > 1 else "whole",
            m.group(0))


def schema(did):
    body, code = get(f"{SRV}/splits?dataset={did.replace('/', '%2F')}")
    if code != "200":
        return None, f"splits HTTP {code}", []
    try:
        sp = json.loads(body)["splits"]
    except Exception:
        return None, "splits unparseable", []
    if not sp:
        return None, "no splits", []
    configs = [x.get("config") for x in sp if x.get("config")]
    # Prefer a config that is NOT the generated sibling: anchoring against the
    # synthetic split would describe a table nobody is claiming is real.
    real = [x for x in sp if not re.search(r"synth", str(x.get("config")), re.I)]
    s = (real or sp)[0]
    u = (f"{SRV}/first-rows?dataset={did.replace('/', '%2F')}"
         f"&config={s['config']}&split={s['split']}")
    body, code = get(u)
    if code != "200":
        return None, f"first-rows HTTP {code}", configs
    try:
        feats = json.loads(body).get("features", [])
        cols = [f["name"] for f in feats if f.get("name")]
    except Exception:
        return None, "first-rows unparseable", configs
    return ((cols, None, configs) if cols
            else (None, "no features", configs))


def names_in(sentence, cols):
    hits = []
    for c in cols:
        if len(c) < 3:
            continue
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(c)}(?![A-Za-z0-9_])",
                     sentence, re.I):
            hits.append(c)
    return hits


def main():
    if not os.path.exists(CAND):
        print(f"{CAND} does not exist yet -- the HF sweep has not sieved.")
        return
    rows = [json.loads(l) for l in open(CAND)]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["id"]].append(r)
    print(f"{len(by)} HF datasets with a surviving sentence\n", flush=True)

    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    fp2 = mirror2.fingerprints()
    # The cards are needed for the synthetic verdict.  Loading them here rather
    # than re-reading per dataset keeps one 100 MB parse instead of 233.
    cards = json.load(open(HERE + "hf_meta/cards.json"))
    for i, (did, hits) in enumerate(sorted(by.items()), 1):
        if did in res and res[did].get("columns"):
            continue
        # Re-uploads are excluded here rather than in the sieve, same as on
        # Kaggle: the sieve decides which sentences survive, this decides which
        # datasets are thrown out.
        blob = " ".join(h["sentence"] for h in hits)
        mir = mirror2.detect(blob, did, fp2)
        if mir:
            res[did] = dict(mirror=mir)
            print(f"  [{i}/{len(by)}] {did[:58]:<58} MIRROR {mir}", flush=True)
            json.dump(res, open(OUT, "w"), indent=1)
            continue
        cols, err, configs = schema(did)
        if err:
            res[did] = dict(error=err)
            print(f"  [{i}/{len(by)}] {did[:58]:<58} SKIP {err}", flush=True)
        else:
            anchored = []
            for h in hits:
                nm = names_in(h["sentence"], cols)
                if nm:
                    anchored.append(dict(sentence=h["sentence"][:400],
                                         family=h["family"],
                                         trigger=h["trigger"], columns=nm))
            syn = synthetic(did, cards, configs)
            res[did] = dict(columns=cols, n_cols=len(cols),
                            anchored=anchored, n_sentences=len(hits),
                            configs=configs,
                            synthetic=(list(syn) if syn else None))
            tag = f"ANCHORED {len(anchored)}" if anchored else "no anchor"
            print(f"  [{i}/{len(by)}] {did[:58]:<58} {len(cols):>4} cols  "
                  f"{tag}", flush=True)
        json.dump(res, open(OUT, "w"), indent=1)
        time.sleep(0.3)

    ok = {k: v for k, v in res.items() if v.get("columns")}
    anc = {k: v for k, v in ok.items() if v.get("anchored")}
    mirs = {k: v for k, v in res.items() if v.get("mirror")}
    errs = {k: v for k, v in res.items() if v.get("error")}
    print(f"\n{len(ok)} with a readable schema; {len(mirs)} re-uploads "
          f"excluded; {len(errs)} unreadable (NOT counted as 'no anchor')")
    print(f"{len(anc)} name a real column")
    # Synthetic is REPORTED, never auto-excluded.  A per-dataset exclusion would
    # have discarded chess-fraud, whose real config carries a perfect leak, on
    # the strength of one word describing its generated sibling.
    whole = {k for k, v in anc.items()
             if (v.get("synthetic") or [None])[0] == "whole"}
    scoped = {k for k, v in anc.items()
              if (v.get("synthetic") or [None])[0] == "scoped"}
    print(f"  of those: {len(whole)} look wholly generated, {len(scoped)} have "
          f"a synthetic SIBLING config\n"
          f"  (scoped ones are kept -- their real config is what was anchored)")
    for k in sorted(scoped):
        print(f"    scoped: {k}  configs={anc[k].get('configs')}")
    if ok:
        print(f"  anchoring rate {100.0*len(anc)/len(ok):.1f}%  "
              f"(Kaggle was 20.0%; anchoring was expected to lose over half)")
    for did, v in anc.items():
        print(f"\n  https://huggingface.co/datasets/{did}")
        for a in v["anchored"]:
            print(f"    ({a['family']}/{a['trigger']!r}) -> {a['columns']}")
            print(f"      {a['sentence'][:220]}")
    if errs:
        print("\nunreadable, listed so they are not mistaken for negatives:")
        for did, v in errs.items():
            print(f"  {did:<62}{v['error']}")


if __name__ == "__main__":
    main()
