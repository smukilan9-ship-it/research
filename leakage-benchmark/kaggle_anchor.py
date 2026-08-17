"""Anchor Kaggle candidate sentences to the REAL CSV header.

WHY THIS IS THE STEP THAT DECIDES STRATUM C

  Registered construction rule 2: admission requires the uploader's own
  sentence naming the column, VERIFIED AGAINST THE REAL CSV HEADER at build
  time.  My reading of a column name is not evidence here.

  Everything up to now has been the first half of that rule.  The sieve says a
  sentence survived; it cannot say whether the sentence names a column, because
  the Kaggle listing API exposes no schema -- `datasets/view` returns an empty
  `files` list and `datasets/list/<owner>/<slug>` returns 403 for this token.
  This is where the yield was expected to die: sentences survive
  the language test and then have nothing to attach to.

  `datasets/download/<ref>` DOES work.  So the header can be read from the
  actual file, and the anchoring rate can be measured instead of assumed.

WHAT IT DOES NOT DOWNLOAD

  Only datasets that already produced a surviving sentence and are neither
  synthetic nor a re-upload -- tens of datasets, not thousands.  Anything over
  MAXBYTES is skipped and COUNTED, because a skipped dataset is missing
  evidence and must not be silently folded into "no anchor found".  That is the
  same failure as the 29 UCI records that went undownloaded and were reported
  as though the archive were 660 (§4.3.2).

READING THE HEADER WITHOUT UNPACKING

  zipfile opens the archive's central directory and streams one member at a
  time, so the first line of each CSV is read without writing the whole table
  to disk.  These files reach 14 MB each and there is no reason to keep them.
"""
import json, os, re, sys, csv, io, zipfile, subprocess, collections, shutil

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
CURL = HERE + "kaggle.curl"
CAND = HERE + "kaggle_deep_candidates.jsonl"
OUT = HERE + "kaggle_anchored.json"
TMP = "/tmp/kaggle_anchor/"
MAXBYTES = 250 * 1024 * 1024
os.makedirs(TMP, exist_ok=True)


def headers_for(ref):
    """Every CSV header in the dataset, or a reason string on failure."""
    z = TMP + "d.zip"
    p = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "300", "-K", CURL,
         "--max-filesize", str(MAXBYTES),
         "-o", z, "-w", "%{http_code} %{size_download}",
         f"https://www.kaggle.com/api/v1/datasets/download/{ref}"],
        capture_output=True, text=True)
    code = (p.stdout or "").split()
    if not code or code[0] != "200":
        return None, f"HTTP {code[0] if code else 'curl'}"
    # --max-filesize aborts the transfer and leaves NO file behind, while
    # %{http_code} still reads 200 because the response headers arrived before
    # the size was known.  Trusting the status alone crashed the first run on
    # the fourth dataset.  A missing or empty file here means "too big", which
    # is a skip to be counted, never a dataset with no anchor.
    if not os.path.exists(z) or os.path.getsize(z) == 0:
        return None, (f"exceeds {MAXBYTES // (1024*1024)} MB cap"
                      if p.returncode in (63,) else
                      f"empty download (curl rc={p.returncode})")
    try:
        out = {}
        with zipfile.ZipFile(z) as zf:
            for nm in zf.namelist():
                if not nm.lower().endswith((".csv", ".tsv")):
                    continue
                with zf.open(nm) as fh:
                    first = io.TextIOWrapper(
                        fh, encoding="utf8", errors="replace").readline()
                if not first.strip():
                    continue
                delim = "\t" if nm.lower().endswith(".tsv") else ","
                cols = next(csv.reader([first], delimiter=delim), [])
                cols = [c.strip().strip('"') for c in cols if c.strip()]
                if cols:
                    out[nm] = cols
        return (out, None) if out else (None, "no CSV member with a header")
    except zipfile.BadZipFile:
        return None, "not a zip (probably an HTML error page)"
    finally:
        if os.path.exists(z):
            os.remove(z)


def names_in(sentence, cols):
    """Columns whose name occurs in the sentence as a whole token.

    Two-character names are excluded: they match inside ordinary prose far more
    often than they identify a column, and a false anchor is worse here than a
    missing one -- it manufactures a ground-truth record out of a coincidence.
    """
    hits = []
    for c in cols:
        if len(c) < 3:
            continue
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(c)}(?![A-Za-z0-9_])",
                     sentence, re.I):
            hits.append(c)
    return hits


def main():
    rows = [json.loads(l) for l in open(CAND)]
    real = collections.defaultdict(list)
    for r in rows:
        if r.get("synthetic") or r.get("mirror"):
            continue
        real[r["ref"]].append(r)
    print(f"{len(real)} real, non-mirror candidate datasets to anchor\n",
          flush=True)

    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for i, (ref, hits) in enumerate(sorted(real.items()), 1):
        if ref in res and res[ref].get("headers"):
            continue
        cols, err = headers_for(ref)
        if err:
            res[ref] = dict(error=err, title=hits[0].get("title"))
            print(f"  [{i}/{len(real)}] {ref[:55]:<55} SKIP {err}", flush=True)
        else:
            allcols = sorted({c for v in cols.values() for c in v})
            anchored = []
            for h in hits:
                nm = names_in(h["sentence"], allcols)
                if nm:
                    anchored.append(dict(sentence=h["sentence"][:400],
                                         family=h["family"],
                                         trigger=h["trigger"], columns=nm))
            res[ref] = dict(title=hits[0].get("title"), headers=cols,
                            n_cols=len(allcols), anchored=anchored,
                            n_sentences=len(hits))
            tag = f"ANCHORED {len(anchored)}" if anchored else "no anchor"
            print(f"  [{i}/{len(real)}] {ref[:55]:<55} {len(allcols):>4} cols "
                  f" {tag}", flush=True)
        json.dump(res, open(OUT, "w"), indent=1)

    ok = {k: v for k, v in res.items() if v.get("headers")}
    anc = {k: v for k, v in ok.items() if v.get("anchored")}
    skipped = {k: v for k, v in res.items() if v.get("error")}
    print(f"\n{len(ok)} datasets with a readable header; {len(skipped)} "
          f"unreadable (NOT counted as 'no anchor')")
    print(f"{len(anc)} datasets have a surviving sentence that names a real "
          f"column")
    if ok:
        print(f"  anchoring rate {100.0*len(anc)/len(ok):.1f}% of readable "
              f"datasets  (anchoring was expected to lose over half)")
    for ref, v in anc.items():
        print(f"\n  {v['title']}\n  https://www.kaggle.com/datasets/{ref}")
        for a in v["anchored"]:
            print(f"    ({a['family']}/{a['trigger']!r}) -> {a['columns']}")
            print(f"      {a['sentence'][:220]}")
    if skipped:
        print(f"\nunreadable, listed so they are not mistaken for negatives:")
        for ref, v in skipped.items():
            print(f"  {ref:<60}{v['error']}")


if __name__ == "__main__":
    main()
