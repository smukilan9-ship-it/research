"""Run the frozen sieve over whatever Kaggle metadata is on disk. No fetching.

WHY SEPARATE FROM THE FETCHER

  kaggle_deep.py sieves at the end of its own run, which means the only way to
  see candidates is to wait for a multi-hour enrichment to finish.  This reads
  the checkpoint instead, so the sieve can be run repeatedly while the fetcher
  is still going, and it cannot disturb the fetcher because it never writes to
  the fetcher's files.

  Reporting an INTERIM yield needs care: a partial denominator is not the
  denominator.  Every count printed here is against `len(cache)`, the datasets
  actually enriched so far, and the header says so.  A rate computed on a third
  of the population and quoted as the population's rate is the single easiest
  mistake to make with a resumable sweep.

THE SIEVE IS UNCHANGED

  explicit_scan's WARN and DEFINE, cond_scan's CONDSET, exactly as frozen.
  Synthetic datasets and content-detected re-uploads of Stratum A/B are
  excluded and COUNTED, because "how many hits had to be thrown away" is part
  of what this measurement is for.
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "kaggle_meta/"
CAND = HERE + "kaggle_deep_candidates.jsonl"

sys.path.insert(0, HERE)
import explicit_scan as E
import cond_scan as C
import mirror2
from kaggle_deep import SYNTH, is_synthetic, corpus_fingerprints, mirrors


def main():
    cache = json.load(open(OUT + "full.json"))
    index = {r["ref"] for r in json.load(open(OUT + "deep_index.json"))}
    dead = json.load(open(OUT + "dead_refs.json")) if os.path.exists(
        OUT + "dead_refs.json") else {}
    fp = corpus_fingerprints()
    # Second, stronger mirror test.  The first one compares only column names
    # of four characters or more, which is why it passed a verbatim re-upload
    # of UCI Student Performance -- that dataset's identifying columns are G1,
    # G2 and G3.  See mirror2.py.
    fp2 = mirror2.fingerprints()

    hits, per = [], collections.Counter()
    empty = 0
    for ref, d in cache.items():
        if ref not in index:
            continue
        if not str(d.get("description") or "").strip():
            empty += 1
        syn = is_synthetic(d)
        mir = mirrors(d, fp) or mirror2.detect(
            str(d.get("description") or "") + " " + str(d.get("subtitle") or ""),
            str(d.get("title") or ""), fp2)
        for field in ("title", "subtitle", "description"):
            txt = d.get(field)
            if not isinstance(txt, str):
                continue
            for sent in C._sents(txt):
                w = E.WARN.search(sent)
                df = E.DEFINE.search(sent)
                cd = C.COND.search(sent) and C.ASSIGN_GENERIC.search(sent)
                if not (w or df or cd):
                    continue
                hits.append(dict(ref=ref, title=d.get("title"), field=field,
                                 sentence=sent.strip(),
                                 family="WARN" if w else
                                        ("DEFINE" if df else "CONDSET"),
                                 trigger=(w or df or cd).group(0)[:60],
                                 synthetic=syn, mirror=mir,
                                 url=f"https://www.kaggle.com/datasets/{ref}"))
                per[ref] += 1
    with open(CAND, "w") as fh:
        for h in hits:
            fh.write(json.dumps(h) + "\n")

    refs = set(per)
    syn_refs = {h["ref"] for h in hits if h["synthetic"]}
    mir_refs = {h["ref"] for h in hits if h["mirror"]}
    real = refs - syn_refs - mir_refs
    pct = 100.0 * len(real) / max(1, len(cache))
    print(f"INTERIM -- denominators are the {len(cache)} datasets ENRICHED SO "
          f"FAR, not the {len(index)} indexed")
    print(f"  {len(dead)} refs unreachable; {empty} enriched with an empty "
          f"description")
    print(f"{len(hits)} surviving sentences across {len(refs)} datasets")
    print(f"  synthetic (EXCLUDED)          {len(syn_refs)}")
    print(f"  re-upload of Stratum A/B      {len(mir_refs)}")
    print(f"  REAL and new                  {len(real)}   "
          f"({pct:.2f}% of enriched so far)")
    print(f"\nreal candidates, most sentences first:")
    for ref, n in per.most_common():
        if ref not in real:
            continue
        h0 = next(h for h in hits if h["ref"] == ref)
        print(f"\n  [{n}] {str(h0['title'])[:70]}")
        print(f"      {h0['url']}")
        seen = set()
        for h in hits:
            if h["ref"] != ref or h["sentence"][:60] in seen:
                continue
            seen.add(h["sentence"][:60])
            print(f"      ({h['family']}/{h['trigger']!r}) "
                  f"{h['sentence'][:220]}")


if __name__ == "__main__":
    main()
