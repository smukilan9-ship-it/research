"""Stratum C specs — datasets this project did not choose.

SEPARATE FILE, ON PURPOSE

  Stratum A and B are frozen.  Every number in the paper is scored against
  them, and adding a dataset to `explicit_specs.py` would silently change the
  denominator of the held-out transfer set that §6.3 reports.  Stratum C lives
  beside them and is scored beside them, never inside them.

  This is the same frozen-sieve discipline applied to the corpus rather than to
  the scanner: a post-hoc addition runs alongside the original, and any
  comparison between them is made on cells present in both.

PROVENANCE IS A FIELD, NOT A FOOTNOTE

  Records here carry how they were found.  `SIEVE` means the frozen sieve
  surfaced it and it counts in the yield denominators.  `HAND_NOMINATED /
  SIEVE_MISS` means a person went looking and found it, which makes it a
  legitimate test case and an illegitimate data point in any rate: a record
  found by searching for it cannot be counted in a statistic that describes
  what a scanner finds at random.  The distinction is enforced by
  `yield_eligible()` rather than left to whoever writes the table.

QUOTATION IS CHECKED, NOT TRUSTED

  `build()` verifies each record's quote against the cached source document and
  raises if it is absent.  The AI4I episode -- documentation naming five flags
  where only four hold -- is the reason nothing in this project is coded from a
  quotation that has not been re-read from the file it claims to come from.
"""
import json, os, re, sys, collections
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
REC = HERE + "records_stratc.jsonl"

SPECS = {
    "cirrhosis": dict(
        name="CIRRHOSIS", target="Status",
        dataset_id="uci878_cirrhosis_survival",
        data="uci/878/data.csv", source="uci/878/meta.json",
        pp="at registration into the trial, before any outcome is observed",
        # ID is an identifier artefact, which §2.1 treats as a separate
        # category from feature-level target leakage.  It is dropped rather
        # than coded, exactly as MI's ID is.
        drop=["ID"]),
    "klaverjas": dict(
        name="KLAVERJAS", target="outcome",
        dataset_id="openml41228_klaverjas2018",
        data="stratc_data/klaverjas2018.csv", source="openml/41228.json",
        pp="when the hand is dealt, before the game is played or solved",
        # `index` is a row identifier and is dropped at export, not coded.
        drop=[],
        # 981,541 rows exhaustively solved; a fixed 100,000-row subsample at
        # seed 0 is used so the CSV is 8 MB instead of 200 MB.  The sample size
        # and seed are recorded here because every downstream number on this
        # dataset depends on them.
        note="100,000-row subsample of 981,541, seed 0; computed (perfect-play "
             "game-theoretic values), not observational"),
    "bikesharing": dict(
        name="BIKESHARING", target="cnt",
        dataset_id="hf_t22000t_bike_sharing_tabular",
        data="stratc_data/bikesharing.csv",
        source="hf_meta/bikesharing_card.json",
        pp="at the start of the hour being forecast, before any rental in that "
           "hour has occurred",
        # `instant` is a row counter and `dteday` the date string it encodes.
        # Identifier artefacts, which S2.1 files as a separate category from
        # feature-level target leakage -- dropped rather than coded, exactly as
        # CIRRHOSIS's ID and MI's ID are.
        drop=["instant", "dteday"],
        # The ONLY record in Stratum C whose positives are named as leakage by
        # the uploader in the uploader's own word.  That is what makes it the
        # cross-archive control: the identical table on UCI 275 yields zero
        # surviving sentences, so the two archives differ in what was written
        # down and not in what is in the data.
        note="HF re-host of UCI 275; the same table at UCI produces ZERO "
             "surviving sentences under the frozen sieve"),
}


def records():
    out = collections.defaultdict(dict)
    if not os.path.exists(REC):
        return out
    for line in open(REC):
        if line.strip():
            r = json.loads(line)
            out[r["dataset_id"]][r["column"]] = r
    return out


def _norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def _strings(obj):
    """Every string anywhere in a nested JSON structure.

    Archives nest their prose differently -- UCI under {"data": {...}}, OpenML
    under {"description": ...} -- and a checker that knows one schema silently
    passes everything from the other."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def verify_quotes(key):
    """Every quote must appear in the cached source record.

    The two archives store their metadata differently -- UCI wraps it in
    {"data": ...}, OpenML in {"description": ...} -- so the whole cached JSON
    is searched rather than a per-archive field path.  A quote check that knows
    the schema of only one source silently passes everything from the other.
    """
    m = SPECS[key]
    # The JSON must be PARSED, not read as text.  Klaverjas' sentence contains
    # `$\alpha\beta$`, which is stored in the file as `$\\alpha\\beta$`; matching
    # a parsed quote against raw file bytes fails on the backslash count alone
    # and would have rejected a quote that is present verbatim.
    hay = _norm(" ".join(_strings(json.load(open(f"{HERE}{m['source']}")))))
    bad = []
    for col, r in records()[m["dataset_id"]].items():
        if _norm(r["quote"]) not in hay:
            bad.append((col, r["quote"][:80]))
    return bad


def yield_eligible(key):
    """Columns admissible to a yield statistic — sieve-found only."""
    m = SPECS[key]
    return [c for c, r in records()[m["dataset_id"]].items()
            if r.get("provenance", "").startswith("SIEVE")]


def build(key):
    m = SPECS[key]
    bad = verify_quotes(key)
    if bad:
        raise ValueError(f"{m['name']}: quote not found in cached source: {bad}")
    df = pd.read_csv(f"{HERE}{m['data']}")
    df.columns = [str(c).strip() for c in df.columns]
    if m["target"] not in df.columns:
        raise KeyError(f"{m['name']}: target {m['target']!r} not in file")
    cols = [c for c in df.columns if c != m["target"] and c not in m["drop"]]
    pos = records()[m["dataset_id"]]
    missing = [c for c in pos if c not in cols]
    if missing:
        raise KeyError(f"{m['name']}: coded columns absent from file {missing}")
    return dict(
        name=m["name"], columns=cols,
        truth={c: (c in pos) for c in cols},
        target=m["target"], prediction_point=m["pp"],
        # Left empty deliberately: a description we author could encode the
        # answer, and C3/C5 would then measure our own hint (PROTOCOL 4).
        description="",
        sample=df[cols].head(5).to_dict("records"),
        sources={c: [pos[c]["source_citation"]] for c in pos if c in cols},
        subtypes={c: pos[c]["subtype"] for c in pos if c in cols},
        provenance={c: pos[c]["provenance"] for c in pos if c in cols},
        yield_eligible=yield_eligible(key),
        missing_positives=missing, n_rows=len(df))


if __name__ == "__main__":
    for k in SPECS:
        b = build(k)
        n = sum(b["truth"].values())
        print(f"  {b['name']:<11}{b['n_rows']:>6} rows{len(b['columns']):>5} "
              f"cols{n:>4} positive   target={b['target']}")
        for c, p in b["provenance"].items():
            print(f"    {c:<12}{b['subtypes'][c]:<12}{p}")
        print(f"    yield-eligible positives: {b['yield_eligible'] or 'none'} "
              f"(hand-nominated records are excluded from yield denominators)")
