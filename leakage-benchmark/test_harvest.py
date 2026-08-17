"""Tests for harvest.py.  Written to break it, not to confirm it works."""
import harvest as H

FAILS = []


def check(cond, label, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f"   {detail}" if detail else ""))
    if not cond:
        FAILS.append(label)


def rec(**kw):
    base = dict(dataset_id="d1", dataset_url="http://x", column="c1",
                label="LEGITIMATE", subtype=None, evidence_tier="E3",
                source_type="PEER_REVIEWED", source_citation="Paper A",
                source_locator="s3", quote="removed as leakage", coder="SM",
                date="2026-08-12", scope="EXCLUSION_LIST_ONLY", notes=None)
    base.update(kw)
    return base


print("=== validate ===")
check(not H.validate([rec()]), "a well-formed record passes")
check(H.validate([rec(label="LABEL_DERIVED", subtype=None)]),
      "LABEL_DERIVED without a subtype is rejected")
check(H.validate([rec(label="LABEL_DERIVED", subtype="REASON", quote="")]),
      "LABEL_DERIVED without a quote is rejected")
check(H.validate([rec(evidence_tier="E1")]),
      "E1 from a non-documentation source is rejected")
check(H.validate([rec(scope="WHATEVER")]), "an unknown scope is rejected")
check(H.validate([rec(label="LABEL_DERIVED", subtype="REASON",
                      quote=" ".join(["w"] * 30))]),
      "an over-long quote is rejected")

# --- duplicate detection
dupe = [rec(column="c9"), rec(column="c9")]
check(H.validate(dupe), "the same (dataset, column, source) twice is rejected",
      "otherwise n_sources double-counts")

print("\n=== adjudicate ===")
a = H.adjudicate([rec(column="c1", label="LABEL_DERIVED", subtype="REASON",
                      evidence_tier="E1", source_type="DOCUMENTATION",
                      scope="FULL_COLUMN_SET", source_citation="Dict"),
                  rec(column="c1", label="LEGITIMATE", source_citation="Paper A")])
check(a[("d1", "c1")]["label"] == "LABEL_DERIVED",
      "documentation outranks a disagreeing paper", str(a[("d1", "c1")]["label"]))

b = H.adjudicate([rec(column="c2", label="LABEL_DERIVED", subtype="REASON",
                      source_citation="Paper A"),
                  rec(column="c2", label="LEGITIMATE", source_citation="Paper B")])
check(b[("d1", "c2")]["label"] == "CONTESTED",
      "two papers disagreeing gives CONTESTED, not a vote")

# two documentation sources that disagree must NOT be silently resolved
c = H.adjudicate([rec(column="c3", label="LABEL_DERIVED", subtype="REASON",
                      evidence_tier="E1", source_type="DOCUMENTATION",
                      scope="FULL_COLUMN_SET", source_citation="Dict v1"),
                  rec(column="c3", label="LEGITIMATE", evidence_tier="E1",
                      source_type="DOCUMENTATION", scope="FULL_COLUMN_SET",
                      source_citation="Dict v2")])
check(c[("d1", "c3")]["label"] == "CONTESTED",
      "two E1 sources that disagree give CONTESTED",
      f"got {c[('d1','c3')]['label']} -- must not take whichever came first")

# n_sources should count DISTINCT sources, not records
d = H.adjudicate([rec(column="c4", source_citation="Paper A", source_locator="p1"),
                  rec(column="c4", source_citation="Paper A", source_locator="p2")])
check(d[("d1", "c4")]["n_sources"] == 1,
      "n_sources counts distinct sources, not records",
      f"got {d[('d1','c4')]['n_sources']}")

print("\n=== cohen_kappa ===")
check(abs(H.cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) - 1.0) < 1e-9,
      "identical vectors give kappa 1")
check(abs(H.cohen_kappa(["a"] * 10, ["a"] * 10) - 1.0) < 1e-9,
      "total agreement on one category gives 1, not 0/0")
k = H.cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"])
check(abs(k) < 1e-9, "chance-level agreement gives kappa 0", f"got {k:.4f}")
try:
    from sklearn.metrics import cohen_kappa_score
    x = ["a", "b", "a", "a", "b", "b", "a", "b"]
    y = ["a", "b", "b", "a", "b", "a", "a", "b"]
    check(abs(H.cohen_kappa(x, y) - cohen_kappa_score(x, y)) < 1e-9,
          "matches sklearn on a mixed case")
except ImportError:
    pass

print("\n=== negatives are materialised ===")
# PROTOCOL 7: unnamed columns of an included dataset are LEGITIMATE by default.
# adjudicate() only ever sees columns that HAVE records, so something must
# expand the corpus against the dataset's real column list.
has = hasattr(H, "materialise")
check(has, "a function exists to mark unnamed columns LEGITIMATE",
      "" if has else "PROTOCOL 7 is unimplemented -- negatives never appear")
if has:
    full = H.materialise(H.adjudicate([rec(column="c1", label="LABEL_DERIVED",
                                           subtype="REASON")]),
                         {"d1": ["c1", "c2", "c3"]})
    check(len(full) == 3, "every column of the dataset appears", str(len(full)))
    check(full[("d1", "c2")]["label"] == "LEGITIMATE",
          "an unnamed column defaults to LEGITIMATE")
    check(full[("d1", "c2")]["basis"] == "default (no source named it)",
          "the default is recorded as such, not as evidence")

print("\n" + "=" * 60)
print("ALL PASS" if not FAILS else f"{len(FAILS)} FAILURE(S): " + "; ".join(FAILS))
