"""Run Bordt et al.'s tabular-memorisation checker over the benchmark corpus.

WHY THIS IS THE RIGHT INSTRUMENT AND OUR PARAPHRASE CONTROL IS NOT

  Bordt, Nori, Rodrigues, Nushi & Caruana, "Elephants Never Forget:
  Memorization and Learning of Tabular Data in Large Language Models", COLM
  2024 (arXiv:2404.06209), show that LLMs have memorised many popular public
  tabular datasets verbatim, and that contamination effects concentrate in
  datasets with MEANINGFUL COLUMN NAMES.  That is exactly this benchmark's
  setup: fifteen well-known public tables, judged from their column names.

  Our own control renames every column and re-runs.  It is a reasonable
  control and it is ours, which is the problem -- a reviewer has no reason to
  trust a memorisation test invented by the people whose result depends on
  it.  `tabmemcheck` is the field's instrument, released by the authors of the
  finding, and it tests something our control cannot: whether the model can
  reproduce the table's HEADER and ROWS verbatim, which is direct evidence of
  memorisation rather than an inference from a performance drop.

WHAT THE TESTS MEAN HERE

  feature_names_test  Given some column names, can the model produce the
                      rest?  THE test for this paper: our prompts hand the
                      model a column list, so if it can complete that list
                      from memory it may be recalling the table rather than
                      reasoning about it.
  header_test         Can it reproduce the CSV header and first rows verbatim?
  row_completion_test Can it continue data rows verbatim?  Strongest evidence,
                      and the hardest to explain away.
  dataset_name_test   Can it name the dataset from a few rows?  Recognition,
                      which is weaker than memorisation and reported as such.

  A positive result does NOT invalidate the benchmark.  It bounds what the
  detection numbers mean, and it is better to bound them ourselves with the
  standard instrument than to have a reviewer do it.
"""
import os, sys, json, time, io, contextlib
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
CSVDIR = HERE + "memcheck_csv/"
OUT = HERE + "memcheck_results.json"
os.makedirs(CSVDIR, exist_ok=True)
sys.path.insert(0, HERE)

import runner as RN
import tabmemcheck as tmc

# The corpus, as the models actually saw it: the column set from the bundle,
# in the bundle's order, with the target appended.  Writing some other frame
# would test memorisation of a table nobody was shown.
def export():
    paths = {}
    for keys in (RN.ALLSETS, RN.EXPLICIT):
        for k in keys:
            try:
                b = RN.spec_bundle(k)
            except Exception as e:
                print(f"  skip {k}: {type(e).__name__}"); continue
            df = None
            for src in ("df", "_df"):
                if isinstance(b.get(src), pd.DataFrame):
                    df = b[src]; break
            if df is None:
                # Rebuild from whichever loader this bundle came from.  The
                # three families load differently, and an exporter that only
                # knows two of them silently drops Stratum B -- which is the
                # held-out set, so its absence would be the worst one to miss.
                for attempt in ("newdata", "harness", "explicit"):
                    try:
                        if attempt == "newdata":
                            import newdata as ND; df = ND.NEW[k]()["df"]
                        elif attempt == "harness":
                            import harness as H; df = H.LOADERS[k]()["df"]
                        else:
                            import explicit_specs as ES
                            m = ES.SPECS[k]
                            df = pd.read_csv(f"{HERE}uci/{m['uci']}/data.csv")
                            df.columns = [str(c).strip() for c in df.columns]
                        break
                    except Exception:
                        df = None
                if df is None:
                    print(f"  skip {b['name']}: no frame from any loader")
                    continue
            cols = [c for c in b["columns"] if c in df.columns]
            tgt = b["target"]
            keep = cols + ([tgt] if tgt in df.columns and tgt not in cols else [])
            p = CSVDIR + b["name"] + ".csv"
            df[keep].to_csv(p, index=False)
            paths[b["name"]] = p
            print(f"  {b['name']:<12}{len(keep):>4} cols  {len(df):>7} rows -> {p}")
    return paths


def keys():
    """Every Gemini key, so one key's quota does not end the run.

    The first attempt used a single key and exhausted its quota on the second
    dataset: 5 tests succeeded and 55 returned HTTP 429, which the script
    dutifully recorded as results and reported as "15/15 datasets complete".
    An error stored in the results file is not a result."""
    ks = [os.environ[f"GEMINI_API_KEY_{i}"] for i in range(1, 10)
          if f"GEMINI_API_KEY_{i}" in os.environ]
    return ks or [os.environ["GEMINI_API_KEY"]]


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.5-flash"
    KEYS = keys()
    print(f"{len(KEYS)} Gemini key(s); rotating on quota exhaustion")
    print("exporting corpus as CSV ...")
    paths = export()
    print(f"\n{len(paths)} datasets exported\n")

    results = json.load(open(OUT)) if os.path.exists(OUT) else {}
    ki = [0]

    def call(fn, p):
        """Run one test, rotating keys on quota errors.  Raises if every key
        is exhausted, rather than returning an error to be stored."""
        last = None
        for attempt in range(len(KEYS) * 2):
            llm = tmc.gemini_setup(model=model, api_key=KEYS[ki[0] % len(KEYS)])
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    r = fn(p, llm)
                return r, buf.getvalue()
            except Exception as e:
                last = e
                if "429" in str(e) or "ResourceExhausted" in type(e).__name__:
                    ki[0] += 1
                    time.sleep(2)
                    continue
                raise
        raise last

    ok = bad = 0
    for name, p in paths.items():
        row = results.get(name, {})
        for test in ("feature_names_test", "header_test",
                     "row_completion_test", "dataset_name_test"):
            if test in row and "error" not in row[test]:
                continue                      # keep good results, retry bad
            fn = getattr(tmc, test)
            try:
                r, log = call(fn, p)
                # NOT truncated: feature_names_test returns a 3-tuple whose
                # third element is the whole predicted column list, and a
                # 400-character cap silently made it unparseable.
                row[test] = dict(result=repr(r), log=log[-4000:])
                ok += 1
                print(f"  {name:<12}{test:<22}ok", flush=True)
            except Exception as e:
                row[test] = dict(error=f"{type(e).__name__}: {e}"[:300])
                bad += 1
                print(f"  {name:<12}{test:<22}FAIL {type(e).__name__}",
                      flush=True)
            time.sleep(0.5)
        results[name] = row
        json.dump(results, open(OUT, "w"), indent=1)
    print(f"\n{ok} tests succeeded, {bad} failed -> {OUT}")
    if bad:
        print("INCOMPLETE: failed tests are stored as errors and must not be "
              "read as findings.")


if __name__ == "__main__":
    main()
