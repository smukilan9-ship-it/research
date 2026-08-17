"""How much explicit, column-level leakage documentation exists at all.

THE QUESTION THIS ANSWERS
  If a source that names its own leaky columns is the best possible ground
  truth, the obvious move is to build the benchmark entirely out of such
  sources.  This measures whether that is possible.  It is not, and the size
  of the shortfall is itself the most useful number this project has produced.

METHOD
  Two repositories were swept in full: every dataset record in the UCI ML
  Repository API index, and every active dataset description on OpenML.  A
  deliberately over-inclusive sieve looked for any sentence containing
  leakage-adjacent language anywhere in the record -- abstract, uploader
  prose, per-variable descriptions -- and, separately, for headings that file
  a block of columns under an outcome label.  Every hit was read.

  Hits are then classified by WHAT KIND of leakage they describe, because the
  distinction is the point.  Group leakage (the same patient in train and
  test), contamination (train/test overlap) and identifier columns are all
  real problems and all OUT OF SCOPE here; this paper is about a feature whose
  value encodes the outcome.

WHY THE NUMBER MATTERS FOR THE PAPER
  It explains, without any hand-waving, why there is no off-the-shelf tool:
  there is no labelled corpus to build one from, and the repositories that
  would have to supply it are silent.  It also justifies the expense of the
  hand-curated corpus -- 50 PDFs for 46 positives -- as the only route
  available rather than as a methodological preference.
"""
import json, os, glob, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"

# Every OpenML sentence that survived the sieve, read and classified by hand.
# Recorded here rather than derived, because the classification IS the reading.
OPENML_VERDICT = {
    "fri_c1_500_5": ("OUT", "'artificially generated' -- not about leakage"),
    "artificial-characters": ("OUT", "'artificially generated' -- not about leakage"),
    "munich-rent-index-1999": ("OUT", "the word 'cheating' is a COLUMN NAME "
                                      "(central heating), matched by accident"),
    "Diabetes130US": ("GROUP", "duplicate patients across the split"),
    "SDSS17": ("GROUP", "duplicate objects across the split"),
    "sarcos": ("CONTAMINATION", "train/test overlap in the released files"),
    "backache": ("OUT", "a malformed line in the file"),
    "jigsaw-toxic-comment-cla": ("OUT", "rows with invalid labels"),
    "tamilnadu-electricity": ("IDENTIFIER", "serviceID, a row identifier"),
    "video_transcoding": ("IDENTIFIER", "YouTube video id"),
}

# UCI hits that anchored to a column, read the same way.
UCI_VERDICT = {
    (222, "duration"): ("TARGET_LEAK", "'not known before a call is performed "
                                       "... should be discarded'"),
    (320, "G1/G2"): ("TARGET_LEAK", "prior-period grades of the same target"),
    (211, "crime columns"): ("TARGET_LEAK", "target is the sum of them"),
    (579, "complications"): ("TARGET_LEAK", "filed under an outcomes heading"),
    (198, "fault types"): ("TARGET_LEAK", "seven mutually exclusive fault flags"),
    (9, "mpg"): ("OUT", "rows removed for a missing target value"),
    (116, "caseid"): ("IDENTIFIER", "'the first attribute is a caseid and "
                                    "should be ignored'"),
    (74, "musk"): ("IDENTIFIER", "molecule_name / conformation_name"),
    (75, "musk"): ("IDENTIFIER", "molecule_name / conformation_name"),
    (149, "circularity"): ("OUT", "'CIRCULARITY' is a feature name"),
    (33, "family history"): ("OUT", "a feature's own definition, not the target's"),
    (40, "flags"): ("OUT", "a feature's own definition, not the target's"),
    (183, "crime sum"): ("TARGET_LEAK", "same statement as 211; the component "
                                        "columns are absent from this version"),
}


def main():
    n_uci = len(glob.glob(HERE + "ucimeta/*.json"))
    n_oml = len(glob.glob(HERE + "openml/*.json"))
    sent_uci = sum(1 for _ in open(HERE + "explicit_candidates.jsonl"))
    ds_uci = len({json.loads(l)["uci_id"] for l in open(HERE + "explicit_candidates.jsonl")})
    sec = [json.loads(l) for l in open(HERE + "section_candidates.jsonl")]
    oml = [json.loads(l) for l in open(HERE + "openml_candidates.jsonl")]
    ds_oml = len({x["name"] for x in oml})

    print("EXPLICIT LEAKAGE DOCUMENTATION IN THE TWO PUBLIC REPOSITORIES\n")
    print(f"{'':<34}{'UCI':>10}{'OpenML':>10}")
    print(f"{'datasets swept':<34}{n_uci:>10}{n_oml:>10}")
    # union, not sum: 198 and 579 are found by BOTH the sentence pass and the
    # heading pass, and adding the two counts would report 16 where 14 is right
    hit_uci = ({json.loads(l)["uci_id"] for l in open(HERE + "explicit_candidates.jsonl")}
               | {h["uci_id"] for h in sec})
    print(f"{'datasets with any hit':<34}{len(hit_uci):>10}{ds_oml:>10}")
    print(f"{'sentences surviving the sieve':<34}{sent_uci:>10}{len(oml):>10}")

    def tally(v):
        return collections.Counter(k for k, _ in v.values())
    tu, to = tally(UCI_VERDICT), tally(OPENML_VERDICT)
    print(f"\nwhat the hits actually describe (each read individually)")
    print(f"{'':<34}{'UCI':>10}{'OpenML':>10}")
    for k in ("TARGET_LEAK", "GROUP", "CONTAMINATION", "IDENTIFIER", "OUT"):
        print(f"  {k:<32}{tu.get(k,0):>10}{to.get(k,0):>10}")

    tl = [k for k, v in UCI_VERDICT.items() if v[0] == "TARGET_LEAK"]
    print(f"\nfeature-level target leakage, explicitly documented, anywhere in "
          f"{n_uci + n_oml:,} datasets:")
    print(f"  {len(tl)} datasets, all of them in UCI, none in OpenML")
    for k in sorted(tl):
        print(f"    {k[0]:>5}  {k[1]:<20}{UCI_VERDICT[k][1]}")
    print(f"\n  rate: {len(tl)}/{n_uci+n_oml:,} = {len(tl)/(n_uci+n_oml):.3%}")
    print(f"\nOpenML's leakage vocabulary is entirely about splits and ids:")
    for name, (k, why) in sorted(OPENML_VERDICT.items()):
        if k in ("GROUP", "CONTAMINATION", "IDENTIFIER"):
            print(f"    {name:<26}{k:<15}{why}")


if __name__ == "__main__":
    main()
