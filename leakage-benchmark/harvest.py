"""Harvesting machinery for PROTOCOL.md.

Three jobs, deliberately separated:

  validate()   every record obeys the schema and the evidence standard
  adjudicate() records -> one label per column, by the rules in PROTOCOL §6
  agreement()  how much sources disagree, which is a RESULT not a QC step

Nothing here looks at column values. That is the point: the ground truth for
this paper must be derivable from documents alone, or the paper's central
claim -- that provenance is not recoverable from data -- is undermined by its
own construction.
"""
import json, itertools, collections, sys, os

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"

REQUIRED = ["dataset_id", "dataset_url", "column", "label", "evidence_tier",
            "source_type", "source_citation", "source_locator", "quote",
            "coder", "date", "scope"]
# PROTOCOL 8a.  A source's SILENCE only means "legitimate" if that source
# attempted the whole column set.  A data dictionary defines every column, so
# its silence is informative.  A paper's exclusion list names only what it
# dropped -- its silence may mean legitimate, unused, or unconsidered.  Scoring
# agreement across the two treats different questions as the same question.
SCOPES = {"FULL_COLUMN_SET", "EXCLUSION_LIST_ONLY"}
LABELS = {"LABEL_DERIVED", "LEGITIMATE", "CONTESTED"}
SUBTYPES = {"REASON", "CONSEQUENCE", "TIMING", None}
TIERS = {"E1", "E2", "E3", "E4"}
SOURCES = {"DOCUMENTATION", "PEER_REVIEWED", "PREPRINT", "COMPETITION"}
# PROTOCOL §6.1 -- documentation outranks publications
TIER_RANK = {"E1": 0, "E2": 1, "E3": 2, "E4": 3}


def validate(records):
    """Return a list of (index, problem).  Empty list means the file is clean."""
    problems = []
    for i, r in enumerate(records):
        for k in REQUIRED:
            if not r.get(k):
                problems.append((i, f"missing required field '{k}'"))
        if r.get("label") not in LABELS:
            problems.append((i, f"bad label {r.get('label')!r}"))
        if r.get("subtype") not in SUBTYPES:
            problems.append((i, f"bad subtype {r.get('subtype')!r}"))
        if r.get("evidence_tier") not in TIERS:
            problems.append((i, f"bad evidence_tier {r.get('evidence_tier')!r}"))
        if r.get("source_type") not in SOURCES:
            problems.append((i, f"bad source_type {r.get('source_type')!r}"))
        if r.get("scope") not in SCOPES:
            problems.append((i, f"bad scope {r.get('scope')!r}"))
        # PROTOCOL §4 -- a positive label requires a quotable licensing phrase
        if r.get("label") == "LABEL_DERIVED":
            q = (r.get("quote") or "").split()
            if not q:
                problems.append((i, "LABEL_DERIVED with no quote"))
            elif len(q) > 25:
                problems.append((i, f"quote is {len(q)} words, limit 25"))
            if r.get("subtype") is None:
                problems.append((i, "LABEL_DERIVED requires a subtype"))
        # tier and source_type must be consistent
        if r.get("evidence_tier") in ("E1", "E2") and r.get("source_type") != "DOCUMENTATION":
            problems.append((i, "E1/E2 must come from DOCUMENTATION"))
        if r.get("evidence_tier") == "E3" and r.get("source_type") != "PEER_REVIEWED":
            problems.append((i, "E3 must come from PEER_REVIEWED"))
    # BUG 1.  The same (dataset, column, source) entered twice would inflate the
    # apparent number of independent sources backing a label.
    seen = collections.Counter((r.get("dataset_id"), r.get("column"),
                                r.get("source_citation")) for r in records)
    for key, n in seen.items():
        if n > 1:
            problems.append((-1, f"duplicate record x{n} for {key}"))
    # A source must declare one scope consistently within a dataset.
    scopes = collections.defaultdict(set)
    for r in records:
        scopes[(r.get("dataset_id"), r.get("source_citation"))].add(r.get("scope"))
    for key, s in scopes.items():
        if len(s) > 1:
            problems.append((-1, f"source {key} declares conflicting scopes {s}"))
    return problems


def adjudicate(records):
    """Collapse (dataset, column, source) records into one label per column.

    PROTOCOL §6:
      1. any E1/E2 record decides the column outright
      2. otherwise, if papers disagree -> CONTESTED (never a majority vote)
      3. otherwise the agreed label stands
    """
    by_col = collections.defaultdict(list)
    for r in records:
        by_col[(r["dataset_id"], r["column"])].append(r)

    out = {}
    for key, rs in by_col.items():
        # BUG 3.  Count distinct SOURCES.  One source citing two locators for the
        # same column is one source, not two -- otherwise a single paper quoted
        # twice looks like independent corroboration.
        n_src = len({r["source_citation"] for r in rs})
        best = min(TIER_RANK[r["evidence_tier"]] for r in rs)
        deciding = [r for r in rs if TIER_RANK[r["evidence_tier"]] == best]
        labs = {r["label"] for r in deciding}
        if len(labs) > 1:
            # BUG 2.  Applies at EVERY tier, including documentation.  Two
            # dictionaries that disagree is a genuine conflict; taking whichever
            # was entered first would hide it.
            out[key] = dict(label="CONTESTED", subtype=None,
                            basis=("documentation sources disagree" if best <= 1
                                   else "sources disagree"),
                            n_sources=n_src, tier=deciding[0]["evidence_tier"])
        else:
            out[key] = dict(label=labs.pop(), subtype=deciding[0].get("subtype"),
                            basis=("documentation" if best <= 1 else "sources agree"),
                            n_sources=n_src, tier=deciding[0]["evidence_tier"])
    return out


def materialise(truth, columns_by_dataset):
    """PROTOCOL §7.  Every column of an included dataset that no source named is
    LEGITIMATE by default.

    Without this the corpus contains only positives, and any evaluation run
    against it would have no negative class at all.  The default is recorded as
    a default, never as evidence, because it is exactly the assumption the
    paper's limitations section has to disclose: precision on the positive class
    is partly a function of how complete the harvest was."""
    full = dict(truth)
    for ds, cols in columns_by_dataset.items():
        named = {c for (d, c) in truth if d == ds}
        missing = [c for c in cols if c not in named]
        for c in missing:
            full[(ds, c)] = dict(label="LEGITIMATE", subtype=None,
                                 basis="default (no source named it)",
                                 n_sources=0, tier=None)
        unknown = named - set(cols)
        if unknown:
            raise ValueError(
                f"{ds}: records name columns absent from the distributed file: "
                f"{sorted(unknown)} -- PROTOCOL I5 (name mapping) is violated")
    return full


def cohen_kappa(a, b):
    """Agreement between two coders, corrected for agreement by chance.

        kappa = (p_o - p_e) / (1 - p_e)

    p_o is how often they actually agree.  p_e is how often they would agree
    if each just guessed at their own base rate.  kappa = 0 means "no better
    than chance"; 1 means perfect.  Raw agreement is misleading here because
    ~90% of columns are legitimate, so two coders who blindly said LEGITIMATE
    every time would score 90% raw and kappa 0.
    """
    assert len(a) == len(b) and a, "need equal, non-empty label vectors"
    n = len(a)
    p_o = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    p_e = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return 1.0 if p_e == 1 else (p_o - p_e) / (1 - p_e)


def agreement(records):
    """Inter-SOURCE agreement: do independent sources name the same columns?

    PROTOCOL §8 -- this is a finding, not a quality check.  Low agreement is
    evidence that the field does not have a shared view of provenance, which
    is the paper's motivation."""
    per_source = collections.defaultdict(lambda: collections.defaultdict(set))
    datasets = collections.defaultdict(set)
    scope_of = {}
    for r in records:
        datasets[r["dataset_id"]].add(r["column"])
        scope_of[(r["dataset_id"], r["source_citation"])] = r.get("scope")
        if r["label"] == "LABEL_DERIVED":
            per_source[r["dataset_id"]][r["source_citation"]].add(r["column"])

    rows = []
    for ds, srcs in per_source.items():
        if len(srcs) < 2:
            continue
        universe = sorted(datasets[ds])
        for s1, s2 in itertools.combinations(sorted(srcs), 2):
            # only compare sources that answered the same question (PROTOCOL 8a)
            if scope_of[(ds, s1)] != scope_of[(ds, s2)]:
                rows.append(dict(dataset=ds, a=s1, b=s2, kappa=None,
                                 jaccard=None, only_a=[], only_b=[],
                                 skipped="scope mismatch -- silence is not comparable"))
                continue
            v1 = [("LABEL_DERIVED" if c in srcs[s1] else "LEGITIMATE") for c in universe]
            v2 = [("LABEL_DERIVED" if c in srcs[s2] else "LEGITIMATE") for c in universe]
            inter = len(srcs[s1] & srcs[s2])
            union = len(srcs[s1] | srcs[s2])
            rows.append(dict(dataset=ds, a=s1, b=s2,
                             kappa=cohen_kappa(v1, v2),
                             jaccard=inter / union if union else 1.0,
                             only_a=sorted(srcs[s1] - srcs[s2]),
                             only_b=sorted(srcs[s2] - srcs[s1])))
    return rows


def load(path):
    with open(path) as fh:
        return [json.loads(l) for l in fh if l.strip()]


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else HERE + "records.jsonl"
    recs = load(path)
    print(f"loaded {len(recs)} records\n")

    probs = validate(recs)
    print("VALIDATION")
    if probs:
        for i, p in probs:
            print(f"   record {i}: {p}")
        print(f"   -> {len(probs)} problem(s); fix before proceeding")
    else:
        print("   all records conform to PROTOCOL sections 4 and 7")

    truth = adjudicate(recs)
    n_pos = sum(1 for v in truth.values() if v["label"] == "LABEL_DERIVED")
    n_con = sum(1 for v in truth.values() if v["label"] == "CONTESTED")
    print(f"\nADJUDICATED  {len(truth)} columns  "
          f"({n_pos} label-derived, {n_con} contested)")
    for (ds, col), v in sorted(truth.items()):
        print(f"   {ds:<26}{col:<26}{v['label']:<15}{v['tier']}  "
              f"{v['basis']} (n={v['n_sources']})")

    rows = agreement(recs)
    print("\nINTER-SOURCE AGREEMENT  (a finding, not a QC step)")
    if not rows:
        print("   no dataset yet has two independent sources")
    for r in rows:
        if r.get("skipped"):
            print(f"   {r['dataset']}  SKIPPED: {r['skipped']}")
            print(f"      {r['a'][:46]}  vs  {r['b'][:46]}")
            continue
        print(f"   {r['dataset']}  kappa={r['kappa']:.3f}  jaccard={r['jaccard']:.3f}")
        if r["only_a"]:
            print(f"      named only by {r['a'][:40]}: {r['only_a']}")
        if r["only_b"]:
            print(f"      named only by {r['b'][:40]}: {r['only_b']}")
