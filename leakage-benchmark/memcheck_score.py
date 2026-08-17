"""Score the direct memorisation tests on WHETHER THE MODEL WAS RIGHT.

WHY THIS FILE EXISTS

  memcheck_report_all.py prints, for header_test and row_completion_test, a
  count of cells that "completed" -- meaning the test executed and tabmemcheck
  returned a result tuple instead of raising.  That is a count of API calls
  that did not fail.  It says nothing about whether the model reproduced
  anything.

  I read that column as a memorisation result and wrote in MEMCHECK_FINDINGS.md
  that nemotron "completed the header test on 15 of 15 datasets -- verbatim
  reproduction of the CSV header ... the strongest single piece of memorisation
  evidence in the project".  It is not.  Nemotron's TITANIC header completion is

      true    ,211.3375,S,2,,1\n1,male,0.9
      model   1,female,29.0,0,0,30,C,2,,1

  which is not the continuation; the model re-emitted a mangled copy of the
  prefix it had just been shown.  Counting that as verbatim recall would have
  put a false claim in the paper in the direction that flatters the paper's own
  memorisation worry.  So the tests are scored here, against the ground truth
  tabmemcheck itself returns.

WHAT THE RESULT TUPLES CONTAIN

  header_test          (prefix, true_continuation, model_completion)
  row_completion_test  ([25 true rows], [25 model completions])

  Both are scored the same way: does the model's string reproduce the truth.

SCORING, DELIBERATELY GENEROUS TO THE MODEL

  Every judgement call here is made in the direction that credits the model
  with MORE memorisation, because the number is used as a bound on how much of
  the detection result could be recall:

    * reasoning-model completions are mined for the last CSV-shaped line, so a
      model that thinks out loud before answering is scored on its answer;
    * comparison is on the first `len(true)` characters of the completion, so
      a model that continues past the truth is not penalised for the overrun;
    * a row counts as correct on exact match after whitespace stripping, and
      a near-miss ratio is reported alongside so a reader can see how much of
      the gap is formatting.

  A number produced this way is an upper bound.  If it is small, the smallness
  is real.
"""
import ast, difflib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
STRATB = {"MI", "CRIME", "STUDENT"}          # the held-out transfer set


def parse(cell, test, arity):
    """The stored result string back into a tuple, or None if unusable.

    header_test returns THREE elements (prefix, true continuation, model
    completion) and row_completion_test returns two ([true rows], [model
    completions]).  An earlier version of this scorer required two for both
    and so silently scored zero header cells -- printing an empty table that
    read like "no model reproduced a header" when the truth was "no header was
    examined"."""
    r = cell.get(test)
    if not r or "error" in r or "result" not in r:
        return None
    try:
        v = ast.literal_eval(r["result"])
    except Exception:
        return None
    return v if isinstance(v, tuple) and len(v) == arity else None


CSVISH = re.compile(r"^[^\s,]*(,[^,]*){3,}$")


MINE_FAIL = [0, 0]                # [no CSV line found, completions examined]


def answer(text):
    """The model's actual row, mined out of any reasoning that precedes it.

    A reasoning model returns paragraphs and then the row.  Taking the whole
    blob would score every reasoning model as wrong for a formatting reason,
    which understates memorisation -- the opposite of the error we want to
    make.  So: the last line that looks like a CSV record wins, and if no line
    does, the raw text is used unchanged."""
    if not isinstance(text, str):
        return ""
    lines = [l.strip().strip("`").strip() for l in text.splitlines()]
    hits = [l for l in lines if CSVISH.match(l)]
    MINE_FAIL[1] += 1
    if hits:
        return hits[-1]
    MINE_FAIL[0] += 1                 # reported, so the reader can discount it
    return text.strip()


def match(true, got):
    """(exact, similarity) for one true/completion pair.

    Compared on the first len(true) characters: tabmemcheck asks for a
    continuation and models routinely supply several rows, so an overrun is a
    property of the instruction-following, not of the recall."""
    t = str(true).strip()
    g = answer(got)[:len(t)] if t else ""
    if not t:
        return False, 0.0
    return g == t, difflib.SequenceMatcher(None, t, g).ratio()


def main():
    data = json.load(open(HERE + "memcheck_all.json"))
    rows = []
    for model in sorted(data):
        hdr_ok = hdr_n = 0
        hdr_sim = []
        row_ok = row_n = 0
        row_sim = []
        per_ds = {}
        for ds, cell in data[model].items():
            h = parse(cell, "header_test", 3)
            if h:
                ok, sim = match(h[1], h[2])       # true continuation, model
                hdr_n += 1
                hdr_ok += ok
                hdr_sim.append(sim)
            r = parse(cell, "row_completion_test", 2)
            if r and isinstance(r[0], list):
                true, got = r[0], r[1]
                n = min(len(true), len(got))
                k = 0
                for i in range(n):
                    ok, sim = match(true[i], got[i])
                    k += ok
                    row_sim.append(sim)
                row_ok += k
                row_n += n
                per_ds[ds] = (k, n)
        rows.append((model, hdr_ok, hdr_n, hdr_sim, row_ok, row_n, row_sim,
                     per_ds))

    print("=" * 88)
    print("HEADER TEST — did the model reproduce the true continuation?")
    print("=" * 88)
    print(f"{'model':<44}{'exact':>10}{'mean sim':>11}")
    for m, ho, hn, hs, *_ in rows:
        if hn:
            print(f"  {m[:42]:<42}{ho:>5}/{hn:<4}"
                  f"{sum(hs)/len(hs):>11.3f}")

    print("\n" + "=" * 88)
    print("ROW COMPLETION — 25 rows per dataset, scored per row")
    print("=" * 88)
    print(f"{'model':<44}{'exact rows':>13}{'mean sim':>11}")
    for m, _, _, _, ro, rn, rs, _ in rows:
        if rn:
            print(f"  {m[:42]:<42}{ro:>6}/{rn:<6}"
                  f"{sum(rs)/len(rs):>11.3f}")

    print("\n" + "-" * 88)
    print("Row completion by dataset (exact rows / attempted), * = Stratum B")
    dss = sorted({d for *_, p in rows for d in p})
    for ds in dss:
        cells = []
        for m, *_, p in rows:
            k, n = p.get(ds, (None, None))
            cells.append("  -  " if k is None else f"{k:>2}/{n:<2}")
        star = "*" if ds in STRATB else " "
        print(f"  {ds:<12}{star} " + " ".join(cells))
    print("  models, in column order: "
          + ", ".join(m.split("/")[-1][:20] for m, *_ in rows))

    print("\nExact match is measured on the first len(true) characters after "
          "mining\nthe last CSV-shaped line out of any reasoning text — every "
          "judgement call\nfavours the model, so these are upper bounds.")
    bad, tot = MINE_FAIL
    print(f"No CSV-shaped line could be mined from {bad} of {tot} completions "
          f"({bad/tot:.1%});\nthose were scored on the raw text and are the "
          f"only cells where the scorer,\nrather than the model, could be "
          f"responsible for a miss.")


if __name__ == "__main__":
    main()
