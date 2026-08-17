"""Read tabmemcheck's raw output and answer the question the paper needs.

  "Are these datasets memorised?" is not the question.  The question is
  whether the model can recall THE COLUMNS WHOSE DETECTION WE MEASURE.  A
  model that reproduces Titanic's canonical schema but cannot produce `boat`
  or `body` has memorised something, and not the thing that would inflate our
  numbers.

  So for every dataset this reports the standard test outcomes AND, for the
  feature-names test, whether each recalled name is one of the corpus's
  positives.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN


def positives():
    out = {}
    for keys in (RN.ALLSETS, RN.EXPLICIT):
        for k in keys:
            try:
                b = RN.spec_bundle(k)
            except Exception:
                continue
            out[b["name"]] = {c for c, v in b["truth"].items() if v}
    return out


def parse_tuple(s):
    """feature_names_test returns (prompt, truth, prediction) as a repr."""
    try:
        v = eval(s, {"__builtins__": {}}, {})
        if isinstance(v, tuple) and len(v) == 3:
            return [x if isinstance(x, str) else "" for x in v]
    except Exception:
        pass
    return None


def names(s):
    return [t.strip() for t in re.split(r"[,\n]", s or "") if t.strip()]


def main():
    res = json.load(open(HERE + "memcheck_results.json"))
    pos = positives()
    print("=" * 78)
    print("FEATURE-NAMES TEST  — can the model complete the column list?")
    print("=" * 78)
    print(f"{'dataset':<12}{'recalled':>10}{'of truth':>10}{'rate':>7}"
          f"{'POSITIVES recalled':>21}")
    tot_r = tot_t = tot_pr = tot_pt = 0
    detail = []
    for ds in sorted(res):
        r = res[ds].get("feature_names_test", {})
        if "error" in r:
            print(f"{ds:<12}{'ERROR':>10}   {r['error'][:44]}")
            continue
        t = parse_tuple(r.get("result", ""))
        if not t:
            print(f"{ds:<12}{'unparsed':>10}")
            continue
        _, truth, pred = t
        T, P = names(truth), set(n.lower() for n in names(pred))
        hit = [n for n in T if n.lower() in P]
        p_all = [n for n in T if n in pos.get(ds, set())]
        p_hit = [n for n in p_all if n.lower() in P]
        tot_r += len(hit); tot_t += len(T)
        tot_pr += len(p_hit); tot_pt += len(p_all)
        print(f"{ds:<12}{len(hit):>10}{len(T):>10}{len(hit)/max(len(T),1):>7.0%}"
              f"{f'{len(p_hit)}/{len(p_all)}':>21}")
        if p_all:
            detail.append((ds, p_all, p_hit))
    print(f"{'TOTAL':<12}{tot_r:>10}{tot_t:>10}{tot_r/max(tot_t,1):>7.0%}"
          f"{f'{tot_pr}/{tot_pt}':>21}")

    print("\n--- which POSITIVES were recalled, per dataset")
    for ds, p_all, p_hit in detail:
        miss = [c for c in p_all if c not in p_hit]
        print(f"  {ds:<12} recalled: {', '.join(p_hit) or '(none)'}")
        print(f"  {'':<12} missed:   {', '.join(miss) or '(none)'}")

    for test, title in (("row_completion_test",
                         "ROW COMPLETION — can it reproduce data rows verbatim?"),
                        ("header_test", "HEADER TEST"),
                        ("dataset_name_test",
                         "DATASET-NAME TEST — recognition, not memorisation")):
        print("\n" + "=" * 78); print(title); print("=" * 78)
        for ds in sorted(res):
            r = res[ds].get(test, {})
            if "error" in r:
                print(f"  {ds:<12}ERROR  {r['error'][:56]}"); continue
            log = re.sub(r"\x1b\[[0-9;]*m", "", r.get("log", ""))
            keep = [l.strip() for l in log.split("\n")
                    if re.search(r"\d", l) and len(l.strip()) < 130
                    and not l.strip().startswith(("Dataset:",))]
            print(f"  {ds:<12}{(keep[-1] if keep else r.get('result',''))[:100]}")


if __name__ == "__main__":
    main()
