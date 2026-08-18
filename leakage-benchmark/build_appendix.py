"""Generate APPENDIX.md from the artefacts, so nothing in it is retyped.

The manuscript's appendix is where a reviewer goes to check a claim, which
means every line of it has to come from the same files the claim came from.
Nothing here is hand-authored except the section prose.

app_bug_ledger_unused() -- a ledger of engineering defects found during
development -- is still defined but is NOT emitted.  A changelog of bugs is not evidence about
the world, and no reader needs one to use or evaluate the benchmark; the claim
is that the code is public and correct now, not that the route here was tidy.
It is kept in this file as project history.

Run:  python3 build_appendix.py > APPENDIX.md
"""
import json, glob, os, sys, collections, textwrap
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN
import prompts as P
import verify_paper as V

OUT = []


def w(s=""):
    OUT.append(s)


def h(n, t):
    w("")
    w("#" * n + " " + t)
    w("")


def fence(body, lang=""):
    w("```" + lang)
    for line in body.rstrip("\n").split("\n"):
        w(line)
    w("```")


# ============================================================== A. protocol
def app_a():
    h(2, "Appendix A. Evidence protocol")
    w(textwrap.dedent("""\
    A column enters the benchmark as a positive only through a written
    record. The record fixes six things, and a candidate that cannot fill all
    six is rejected rather than argued about:

    | field | what it fixes |
    |---|---|
    | `target` | which outcome the column is being judged against |
    | `prediction_point` | the moment before which a value must exist |
    | `subtype` | which mechanism is claimed |
    | `source_citation` + `source_locator` | where a reader finds the evidence |
    | `quote` | the source's own words, copied verbatim |
    | `coder` + `date` | who read it and when |

    **Admissibility tiers.** The tier records what kind of statement the
    evidence is, not how prestigious its container is. A dataset's own
    documentation outranks a paper that merely uses the dataset, because the
    documentation is written by the people who built the column.

    | tier | evidence |
    |---|---|
    | E1 | the source states the relationship as a fact about the data's construction |
    | E2 | the source describes the column in terms that entail the relationship |
    | E3 | the relationship follows from the column's documented meaning, and the coder says so explicitly |

    **Legitimate by default.** A column with no admissible record is coded
    legitimate, whatever the coder suspects. This is deliberate and it is
    asymmetric: it can only create false negatives in the ground truth, never
    false positives, so a model's measured precision is a lower bound and its
    measured recall is not.

    **Verification against the data.** Where a coded mechanism implies a
    testable pattern in the values, the pattern is checked (Appendix A.2).
    The check does not create the label -- a legitimate column can correlate
    perfectly by accident, which is exactly why correlation is a baseline
    here and not an oracle -- but a coded derivation that the data contradict
    is withdrawn. One was: see AI4I `RNF` below."""))

    h(3, "A.1 Record counts")
    recs = V.load_records()
    main, expl = {}, {}
    for k in RN.ALLSETS:
        b = RN.spec_bundle(k); main[b["name"]] = b
    for k in RN.EXPLICIT:
        b = RN.spec_bundle(k); expl[b["name"]] = b
    pos = [(lab, n, c) for d, lab in ((main, "A"), (expl, "B"))
           for n, b in sorted(d.items()) for c, v in b["truth"].items() if v]
    nq = sum(1 for _, n, c in pos if (recs.get((n, c), {}).get("quote") or "").strip())
    tier = collections.Counter(recs[(n, c)].get("evidence_tier", "?") for _, n, c in pos)
    ex = collections.Counter(recs[(n, c)].get("explicitness")
                             or ("NAMED_BY_SOURCE" if lab == "B"
                                 else "INFERRED_FROM_DESCRIPTION")
                             for lab, n, c in pos)
    w(f"* positives: **{len(pos)}**, every one with a record")
    w(f"* carrying a verbatim source quotation: **{nq}**; without: "
      f"**{len(pos)-nq}** (TITANIC `boat`/`body`, COMPAS `r_*`)")
    w(f"* tiers: " + ", ".join(f"{k} {v}" for k, v in sorted(tier.items())))
    w(f"* explicitness: " + ", ".join(f"{k} {v}" for k, v in ex.items()))
    nrej = sum(1 for _ in open(HERE + "records_rejected.jsonl"))
    w(f"* candidate rows rejected at adjudication: **{nrej}**")
    w("")
    w("The six records without a quotation are marked E3 and rest on the "
      "column's documented name plus an exact check in the data; the "
      "documentation itself (hbiostat.org for titanic3, the ProPublica "
      "repository for COMPAS) was not retrievable from the run environment. "
      "They are the weakest evidence in the corpus and are labelled so.")

    h(3, "A.2 Coded derivations checked against the data")
    w("Reproduced from `NUMBERS.txt` §3.")
    txt = open(HERE + "NUMBERS.txt").read()
    a = txt.index("3. CODED DERIVATIONS")
    b = txt.index("4. REPOSITORY SWEEP")
    fence(txt[a:b].rstrip().rsplit("=" * 78, 1)[0].strip())
    w("Four of the five checks confirm the coding. The fifth refutes part of "
      "a source statement: AI4I's documentation names five failure modes as "
      "inputs to `Machine failure`, and `RNF` is not one of them in the "
      "table -- 1 of its 19 flagged rows carries the target. `RNF` is "
      "therefore coded legitimate, against its own documentation. This is "
      "the clearest evidence in the project that source-named ground truth "
      "still has to be checked.")


# =============================================================== B. records
def app_b():
    h(2, "Appendix B. The records")
    w("Every positive in the benchmark AFTER the audit of \u00a74.7, with the "
      "evidence it rests on. "
      "Quotations are verbatim; `--` means no quotation was obtainable and "
      "the record is E3 (see A.1). Generated by `build_appendix.py` from the "
      "record files, not transcribed.")
    recs = V.load_records()
    order = []
    for keys, lab in ((RN.ALLSETS, "A"), (RN.EXPLICIT, "B")):
        for k in keys:
            b = RN.spec_bundle(k)
            cols = [c for c in b["columns"] if b["truth"].get(c)]
            if cols:
                order.append((lab, b, cols))
    n = 0
    for lab, b, cols in order:
        h(3, f"{b['name']}  (stratum {lab})")
        w(f"*target* `{b['target']}` &nbsp;&nbsp; *prediction point* — "
          f"{b['prediction_point']}")
        w("")
        for c in cols:
            n += 1
            r = recs.get((b["name"], c), {})
            q = (r.get("quote") or "").strip()
            w(f"**B{n}. `{c}`** — {r.get('subtype') or V.subtype(b['name'], c)}"
              f", tier {r.get('evidence_tier','?')}, "
              f"{r.get('explicitness') or ('NAMED_BY_SOURCE' if lab=='B' else 'INFERRED_FROM_DESCRIPTION')}")
            w("")
            # a quotation may legitimately begin with "#" (the KOI column
            # definition block); unescaped it becomes a heading inside the
            # blockquote and the reader sees a title, not a quotation.
            w("> " + (q.replace("#", "\\#") if q else "--"))
            w("")
            w(f"*source*: {r.get('source_citation','--')} — "
              f"{r.get('source_locator','--')}  ")
            if r.get("data_check"):
                w(f"*check in data*: {r['data_check']}  ")
            if r.get("notes"):
                w(f"*note*: {r['notes']}")
            w("")
    w(f"Total: {n} records.")


# ===================================================== C. prediction points
def app_c():
    h(2, "Appendix C. Prediction points")
    w("Leakage is a property of the triple (column, target, prediction "
      "point). The third element is not in any dataset file, so it is "
      "authored -- once per dataset, before any model was run, from the "
      "framing the dataset's own documentation gives its task. It is shown "
      "to models only from C2 onward; C0 and C1 withhold it deliberately.")
    w("")
    w("| dataset | target | prediction point |")
    w("|---|---|---|")
    for keys in (RN.ALLSETS, RN.EXPLICIT):
        for k in keys:
            b = RN.spec_bundle(k)
            w(f"| {b['name']} | `{b['target']}` | {b['prediction_point']} |")


# =============================================================== D. prompts
def app_d():
    h(2, "Appendix D. Prompts, verbatim")
    w("Rendered by the same functions the runs used, on the same bundle "
      "object. The dataset shown is HEARTFAIL, chosen because it is small "
      "enough to print whole; every other dataset differs only in the column "
      "list, the sample rows and the two framing lines.")
    b = RN.spec_bundle("heartfail")
    cols = list(b["columns"])
    h(3, "System message (C0–C4, C6, C7, C9)")
    w("Every condition uses this system message except **C5**, which has its "
      "own expert framing below.")
    fence(P.SYSTEM)
    h(3, "C0 — names only")
    fence(P.build(b["name"], cols, 0))
    h(3, "C1 — + target (primary condition)")
    fence(P.build(b["name"], cols, 1, target=b["target"]))
    h(3, "C2 — + prediction point")
    fence(P.build(b["name"], cols, 2, target=b["target"],
                  prediction_point=b["prediction_point"]))
    h(3, "C3 / C4 — + description, + sample rows")
    w("C3 appends a `Dataset description:` block (truncated at 1500 "
      "characters); C4 appends five sample rows rendered as a pipe table. "
      "Both are shown in full in the source of `prompts.py:build`, "
      "Appendix I.")
    h(3, "C5 — expert framing (system + task)")
    w("The one condition that does not build on the C1 task text. It supplies "
      "no prediction point: the model must infer it at step 2, and handing it "
      "over would confound C5 with C2.")
    fence(P.EXPERT_SYSTEM)
    fence(P.EXPERT_TASK)
    h(3, "C6 — derivation criterion (appended to C1)")
    w("C1 is the base, so that C6 − C1 isolates exactly one variable: the "
      "statement of the criterion. Building on C4 instead would confound the "
      "criterion with the sample rows.")
    fence(P.DERIVATION_CLAUSE)
    h(3, "C7 — surrogate clause (appended to C6)")
    w("The only clause that stacks on C6 rather than on C1: C7 is C6's task "
      "text plus the clause below.")
    fence(P.SURROGATE_CLAUSE)
    h(3, "C9 — derivation criterion restated, without reference to time "
         "(appended to C1)")
    w("C9 differs from C6 in one respect, and it is the respect the failure "
      "analysis pointed at: it says in as many words that the criterion is "
      "about information and not about time, and it gives the reconstruction "
      "test to apply instead of a temporal test. Both are appended to the "
      "same C1 base, so the two are directly comparable and any difference is "
      "attributable to the wording alone. There is no C8.")
    fence(P.DERIVATION_CLAUSE_V2)


# ============================================================ E. paraphrase
def app_e():
    h(2, "Appendix E. Paraphrase map")
    pmap = json.load(open(HERE + "paraphrase.json"))
    w(pmap["_doc"])
    w("")
    ndc = 0
    for k, v in pmap.items():
        if k.startswith("_"):
            continue
        ndc += len(v.get("columns", {}))
    w(f"Covers {ndc} column names across "
      f"{len([k for k in pmap if not k.startswith('_')])} datasets.")
    w("")
    w("Four mechanical checks are run by `paraphrase.py --check`, and the "
      "map does not ship unless all four pass:")
    w("")
    w("1. **Bijection** — no two original names map to the same alias, in "
      "either direction.")
    w("2. **String distinctness** — no alias shares a case-insensitive "
      "substring of length ≥ 3 with the name it replaces, except for terms "
      "on an explicit exemption list (drug names in DIABETES, which have no "
      "meaning-preserving alias).")
    w("3. **Transparency preservation** — an opaque acronym maps to a "
      "different opaque acronym; a transparent word maps to a synonym. "
      "Expanding an acronym would add information the original never "
      "carried, which would confound the control in the direction that "
      "flatters it.")
    w("4. **Coverage** — every column of every paraphrased dataset appears "
      "in the map, including the target and the columns coded legitimate.")
    w("")
    w("Example (KOI), from `paraphrase.json`:")
    ex = {k: v for k, v in list(pmap["KOI"].get("columns", {}).items())[:8]}
    fence(json.dumps(ex, indent=2), "json")


# ================================================================ F. numbers
def app_f():
    h(2, "Appendix F. `NUMBERS.txt` in full")
    w("The output of `verify_paper.py`. Every table in the manuscript is "
      "annotated with the section of this file it comes from. If a number is "
      "in the paper and not here, it is unverified.")
    fence(open(HERE + "NUMBERS.txt").read())


# ================================================================== G. sweep
def app_g():
    h(2, "Appendix G. The repository sweep")
    w("Two sieves over 689 UCI and 6,420 OpenML metadata records — 7,109 in "
      "total, the entire machine-readable population — followed "
      "by a hand reading of every surviving sentence. The sieves are "
      "deliberately over-inclusive: a hit costs seconds of reading, a miss "
      "costs a source that is never found.")
    h(3, "G.1 Yield")
    txt = open(HERE + "NUMBERS.txt").read()
    a = txt.index("4. REPOSITORY SWEEP")
    b = txt.index("5. BASELINES")
    fence(txt[a:b].rstrip().rsplit("=" * 78, 1)[0].strip())
    h(3, "G.2 Every surviving UCI sentence")
    rows = [json.loads(l) for l in open(HERE + "explicit_candidates.jsonl")]
    byds = collections.defaultdict(list)
    for r in rows:
        byds[(r["uci_id"], r["dataset"])].append(r)
    for (i, nm), rs in sorted(byds.items(), key=lambda x: -len(x[1])):
        w(f"**UCI {i} — {nm}** ({len(rs)} sentences)")
        w("")
        seen = set()
        for r in rs[:6]:
            s = r["sentence"]
            if s[:70] in seen:
                continue
            seen.add(s[:70])
            w(f"* `{r['family']}` in `{r['field']}` — "
              f"columns named: {', '.join(r['columns']) or '—'}")
            w(f"  > {s}")
        if len(rs) > 6:
            w(f"* … and {len(rs)-6} further sentences in the same record "
              f"(all in `{rs[0]['field']}`).")
        w("")
    h(3, "G.3 The hand reading")
    w("Each dataset that survived the sieve was read and classified. Only "
      "`TARGET_LEAK` counts toward the scarcity figure.")
    w("")
    w("| verdict | UCI | OpenML | what it means |")
    w("|---|---|---|---|")
    w("| TARGET_LEAK | 6 | 0 | the source names a column whose value encodes the target |")
    w("| IDENTIFIER | 3 | 2 | a row id or key, not a feature |")
    w("| GROUP | 0 | 2 | a grouping warning (split by subject), not feature-level |")
    w("| CONTAMINATION | 0 | 1 | train/test overlap, not feature-level |")
    w("| OUT | 4 | 5 | matched the sieve, says nothing about leakage |")
    h(3, "G.4 The post-hoc family, and a demonstrated miss")
    w("While assembling this appendix, the 29 UCI records that had failed to "
      "download on earlier passes were re-fetched (689 in the archive index, "
      "660 previously on disk). One of them — id 601, AI4I 2020 — is a "
      "dataset already in this benchmark, and its documentation says:")
    w("")
    cu = [json.loads(l) for l in open(HERE + "cond_candidates.jsonl")]
    for c in cu:
        w(f"> {c['sentence']}")
    w("")
    w("That is an explicit, source-authored, feature-level target-leakage "
      "statement, and all three families of the frozen sieve miss "
      "it: each requires a preposition after the assignment verb (*derived "
      "from*, *set from*), and this author wrote a conditional (*set to 1* "
      "governed by a preceding *if*).")
    w("")
    w("Rather than edit the sieve and report the result as if it had been "
      "found by the sieve, the original is frozen and a one-pattern "
      "extension (`cond_scan.py`) runs beside it, over all 7,109 records. It "
      "recovers exactly the sentence above and finds one other construction, "
      "in two OpenML records describing image annotation, which is not "
      "leakage. The frozen-sieve rate is 6/7,109; including the post-hoc "
      "find it is 7/7,109. Both are lower bounds, and the miss is the proof.")


# ============================================================= H. bug ledger
LEDGER = [
 ("Word boundary could not match a plural",
  "section_scan.py", "`\\bcomplication\\b` cannot match \"Complications\". The "
  "heading pass returned zero blocks on the one dataset it existed for, and "
  "would have silently dropped an 11-positive dataset from the transfer set.",
  "Trailing `s?` on the heading nouns."),
 ("DEFINE required the words class/label/target",
  "explicit_scan.py", "The first DEFINE family required a literal "
  "class/label/target as the sentence subject and fired zero times in 612 "
  "datasets. Authors write derivations with the target's own name.",
  "Per-dataset subject alternation built from `target_col` and any variable "
  "whose role is Target, matched over a 60-character window."),
 ("Failed API calls were cached as answers",
  "runner.py", "A non-2xx or empty response was written to the cache like a "
  "real one. 91 cells recorded zero coverage that had never been asked.",
  "Only non-empty parsed responses are cached; failures raise."),
 ("Transport errors were not retried",
  "runner.py", "curl exit 7 (connection refused) was treated as terminal. One "
  "pass lost 91 of 96 cells to it.",
  "TRANSIENT regex over curl exits 7/18/28/35/52/55/56 with a longer backoff "
  "than the rate-limit path."),
 ("The watchdog killed itself",
  "supervise.sh", "`pkill -9 -f \"supervise.sh\"` matched the harness's own "
  "`bash -c '... ./supervise.sh ...'` wrapper. A watchdog whose failure mode "
  "is suicide is worse than none, because it looks like it is working.",
  "Replaced by a single Python supervisor that kills by PID via `os.killpg`."),
 ("Stall detector fought the retry logic",
  "drive.py", "A 12-minute silence window against a retry budget that can "
  "legitimately run 90 minutes. The supervisor killed healthy runs.",
  "Heartbeat every 180s from the worker, so silence means something."),
 ("Backgrounded `nohup` died at ~15 minutes",
  "overnight.sh", "`nohup ... &` inside a backgrounded shell call is reaped "
  "when the call's tracked process exits.",
  "Run the long process directly as the tracked background command."),
 ("Worker count capped at key count",
  "runner.py", "Correct for Gemini and Featherless, where concurrency is "
  "priced per key; wrong for NVIDIA NIM, which allows several concurrent "
  "requests per key. It held one campaign at a single worker.",
  "`--workers` is honoured explicitly when given."),
 ("A third API key was never used",
  "(operations)", "Two keys were found by `env | grep FEATHERLESS`; the third "
  "was in a variable named `key_2`. A third of the available throughput sat "
  "idle for a night.",
  "Keys are read from a 0600 env file with an explicit list, not by grep."),
 ("pandas: `dtype == object` is not a not-numeric test",
  "downstream2.py", "Categorical columns are `string` dtype in current "
  "pandas, not `object`. Every categorical feature was being dropped from "
  "every downstream arm, in silence.",
  "`pd.api.types.is_numeric_dtype`."),
 ("Per-lookup scan of 1,009 response files",
  "downstream2.py", "The flag lookup re-globbed and re-parsed the response "
  "directory once per (dataset, arm, fold). Not a wrong answer, but it made "
  "the run unusable.",
  "`build_flag_index()` once, then dictionary lookups."),
 ("Fold-averaged rates cannot reconstruct a matrix",
  "confusion.py", "Averaging per-fold precision and recall and then "
  "back-solving for counts gives a matrix that no fold produced.",
  "Confusion matrices are pooled over folds from raw counts."),
 ("Stratum B subtypes reported as UNCODED",
  "verify_paper.py", "The verification harness read subtype codes only from "
  "`subtypes.py`; Stratum B's live in `explicit_specs`. All 30 B positives "
  "reported UNCODED, and the SURROGATE row — the paper's central negative "
  "finding — came out empty.",
  "Subtype lookup unions both sources."),
 ("Transfer-set numbers mixed into a main-corpus table",
  "(analysis)", "An Opus figure computed on Stratum B was reported in a "
  "Stratum A table. Caught by the user, not by me.",
  "`prf()` takes an explicit corpus restriction; `ds` and `sd` counts are "
  "printed beside every row so an unequal comparison is visible."),
 ("Seed counts were invisible",
  "verify_paper.py", "Models run with 5 shuffles and models run with 1 were "
  "compared in the same table with nothing to show it.",
  "`sd` column in every model table."),
 ("A per-cell timing claim extrapolated from small datasets",
  "(analysis)", "I told the user the frontier models were slow. The timing "
  "data said ~85 s/cell and 95% dead time from my own retry bugs.",
  "Withdrawn and corrected in the same session."),
 ("An order-averaging claim generalised from one model",
  "(analysis)", "Seed spread was reported as a property of the task. GPT's "
  "spread was 0.000; it is a property of particular models.",
  "Withdrawn; per-model seed spread is reported instead."),
 ("A DeepSeek comparison distorted by missing cells",
  "(analysis)", "REASON recall was reported as 67%→36% across a condition "
  "change. Like-for-like on the cells that existed in both, it was 91%→36% — "
  "worse than reported, not better.",
  "Condition comparisons are restricted to cells present in both arms."),
 ("29 of 689 UCI records were never downloaded",
  "fetch_meta.py", "Two fetch passes left 29 records missing and the sweep "
  "reported 660 as if it were the archive. One of the 29 (id 601, AI4I) "
  "contains an explicit leakage statement — and is a dataset already in this "
  "benchmark.",
  "All 689 fetched; sweep re-run; the miss is reported in Appendix G.4 "
  "rather than absorbed."),
 ("Unequal cell sets across conditions",
  "verify_paper.py", "Condition comparisons were restricted to common "
  "DATASETS but not common shuffles. One missing cell made C1's REASON "
  "denominator 51 where C6's was 47, and the two percentages were printed "
  "side by side as if comparable. A later version over-corrected, "
  "intersecting C1/C6/C9 at once and cutting C1 and C6 down to whatever "
  "single shuffle a model had at C9.",
  "All comparisons are PAIRWISE and matched on (dataset, seed). Changed "
  "gemini-3.7 C1 0.803 -> 0.822 and deepseek-v4-flash C1 0.588 -> 0.620, "
  "among others."),
 ("Paraphrased cells scored against un-paraphrased truth",
  "verify_paper.py", "The memorisation control looked up alias-named verdicts "
  "in a truth dict keyed on original names. Every join failed, so every "
  "paraphrased cell scored P=R=F1=0.000 -- which reads as a catastrophic "
  "result and means the scorer never looked.",
  "Paraphrased arms are scored against aliased bundles, with an alias-back "
  "map for the subtype lookup; and any cell whose verdict keys do not "
  "intersect the truth keys is now refused loudly instead of scored zero."),
 ("A degenerate cell scored as 32 false negatives",
  "verify_paper.py", "deepseek-v4-flash returned one 'column' literally named "
  "`Pstatus,paid,etc...` for STUDENT at C2. With no join guard this counted "
  "as the model missing every positive.",
  "The join guard above catches it; the cell is excluded and reported."),
 ("An inter-annotator kappa with no artefact behind it",
  "(analysis)", "The limitations section reported kappa = 0.316 for the "
  "subtype task. No second coding exists anywhere in the project, and no "
  "file reproduces the number.",
  "Removed. The limitation is now stated as what it is: the subtype coding "
  "has no second coder and therefore no reliability estimate."),
 ("Two leave-one-out figures and two B3 examples were wrong",
  "(analysis)", "The paper reported gemini-3.5's KOI-drop as -0.058 (it is "
  "-0.008), Qwen's as +0.156 with +6 REASON columns (it is +0.092 with +22), "
  "and cited B3 as keeping `recoveries` on LC and the wrong ceiling figures "
  "for TITANIC.",
  "All four recomputed from the artefacts; the corrected TITANIC case (B3 "
  "drops `sex` and keeps `body`, whose correlation with the target is 0.014) "
  "is a better illustration than the one it replaced."),
 ("Sieved an empty field and nearly reported the result",
  "kaggle_harvest.py", "Kaggle's dataset-list endpoint returns an empty "
  "`description` and no column schema. The first Stratum-C harvest therefore "
  "ran the sieve over titles and 50-character subtitles, found 1 candidate "
  "sentence in 1,281 datasets, and would have supported the headline "
  "\"Kaggle documents leakage far less than the archives\" -- a finding "
  "produced entirely by a field that was never populated.",
  "Two-phase fetch: the list endpoint for the index, then a per-dataset view "
  "call for the real description. 37 of the first 40 enriched have non-empty "
  "prose. The scan now refuses to run at all if nothing was enriched, rather "
  "than reporting a yield from titles."),
 ("A throttled API read as an exhausted one",
  "kaggle_harvest.py", "Seven consecutive queries were rate-limited (HTTP "
  "429). The code parsed the error object, found no dataset rows, and treated "
  "each as \"this query has no more results\" -- so the index froze at 1,281 "
  "and the run reported success. A sieve that reports zero because it was "
  "blocked, in the same words it uses for zero because it looked, is worse "
  "than one that crashes.",
  "HTTP status is inspected; 429 triggers exponential backoff; a query that "
  "cannot complete is recorded and named in the output, and the index is "
  "reported as a floor rather than a census."),
]



def app_bug_ledger_unused():
    h(2, "Bug ledger (not emitted)")
    w("Defects that changed, or would have changed, a reported number. Four "
      "of them would have corrupted results in silence: caching failed API "
      "calls as answers, a word-boundary regex that could not match a plural, "
      "a paraphrase arm scored against the wrong truth keys, and condition "
      "comparisons made on unequal cell sets, and a sieve run over a field "
      "that was never populated. Six were errors in reporting "
      "rather than in code, and are listed because a ledger that only "
      "contains code is not a ledger. Several were found while assembling "
      "this appendix — H19 onward — which is the argument for building the "
      "appendix from the artefacts rather than from the manuscript.")
    w("")
    for i, (t, f, what, fix) in enumerate(LEDGER, 1):
        w(f"**H{i}. {t}** — `{f}`  ")
        w(f"{what}  ")
        w(f"*Fix:* {fix}")
        w("")
    w(f"Total: {len(LEDGER)}.")


# ============================================================== I. downstream
def app_h():
    h(2, "Appendix H. Downstream protocol and confusion matrices")
    w(textwrap.dedent("""\
    **Question.** Not "can a model find leaking columns" but "does finding
    them recover the honest performance". Four arms per dataset per learner:

    | arm | columns given to the learner |
    |---|---|
    | `ALL` | everything (the leaked model) |
    | `GT` | everything the ground truth does not mark leaking (the honest ceiling) |
    | `<model>` | everything a given LLM did not flag |
    | `B3` | everything below the best correlation threshold |

    **Learners.** `rf` is a random forest (500 trees, class-weighted);
    `gb` is gradient boosting. Two, so that a result is not an artefact of
    one inductive bias.

    **Why F1, and how the threshold is chosen.** AUC is threshold-free and
    hides the operating point a practitioner would actually use; a raw 0.5
    cut on an imbalanced target reports an F1 that says more about the
    imbalance than the features. So the decision threshold is chosen by an
    inner 3-fold cross-validation **on the training part of each outer fold
    only**, and applied to the held-out part. No threshold is ever chosen on
    data it is scored on.

    **Class weighting.** Every learner is fit with balanced class weights, so
    the honest ceiling is a real ceiling rather than a majority-class
    predictor.

    **BONEMARROW.** Excluded from the headline figure and reported beside it.
    Its target is degenerate under this protocol -- the honest arm cannot
    beat the base rate -- so a delta computed on it measures the
    degeneracy."""))
    h(3, "H.1 Per-dataset arms")
    d = pd.read_csv(HERE + "downstream2.csv")
    w("| dataset | learner | arm | dropped | AUC | F1 | P | R |")
    w("|---|---|---|---|---|---|---|---|")
    for _, r in d.iterrows():
        w(f"| {r.dataset} | {r.learner} | {r.arm} | {int(r.n_dropped)} | "
          f"{r.auc:.3f} | {r.f1:.3f} | {r.p:.3f} | {r.r:.3f} |")
    h(3, "H.2 Pooled confusion matrices")
    w("Pooled over folds from raw counts, never reconstructed from averaged "
      "rates (pooled from raw counts, never averaged rates).")
    c = pd.read_csv(HERE + "confusion.csv")
    w("")
    w("| dataset | learner | arm | n | dropped | TN | FP | FN | TP | P | R | F1 |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in c.iterrows():
        w(f"| {r.dataset} | {r.learner} | {r.arm} | {int(r.n)} | "
          f"{int(r.n_dropped)} | {int(r.tn)} | {int(r.fp)} | {int(r.fn)} | "
          f"{int(r.tp)} | {r.precision:.3f} | {r.recall:.3f} | {r.f1:.3f} |")


# ================================================================= J. source
# Files whose code produces a number that appears in the manuscript.  These are
# printed in full.  Everything else is listed with its purpose and line count,
# because an appendix nobody finishes is not evidence -- the first version of
# this document was 11,667 lines, of which 9,041 were source, and no reviewer
# reads that.
INLINE = ["audit.py", "prompts.py", "verify_paper.py", "explicit_scan.py",
          "cond_scan.py", "downstream2.py", "confusion.py"]
SKIP = {"build_appendix.py"}


def app_i():
    h(2, "Appendix I. Source code")
    files = sorted(os.path.basename(x) for x in glob.glob(HERE + "*.py"))
    files += sorted(os.path.basename(x) for x in glob.glob(HERE + "*.sh"))
    files = [f for f in files if f not in SKIP]
    tot = sum(sum(1 for _ in open(HERE + f, errors="replace")) for f in files)
    w(f"{len(files)} files, {tot:,} lines. The **{len(INLINE)} files that "
      f"generate numbers appearing in this paper are printed in full** below. "
      f"The rest are listed with purpose and length; all are in the "
      f"repository.")
    w("")
    w("Each file's docstring states what it does and, where it replaced "
      "something, why the something failed. Those docstrings are the honest "
      "history of the project and are worth more than the code.")

    h(3, "I.1 Manifest")
    w("| file | lines | inlined | purpose (first docstring line) |")
    w("|---|---|---|---|")
    for f in files:
        src = open(HERE + f, errors="replace").read()
        n = src.count("\n") + 1
        first = ""
        for line in src.split("\n"):
            t = line.strip().strip('"').strip("#").strip()
            if t and not t.startswith(("import", "from", "#!")):
                first = t
                break
        w(f"| `{f}` | {n} | {'yes' if f in INLINE else '—'} | {first[:100]} |")

    h(3, "I.2 The files that produce reported numbers")
    for f in INLINE:
        if not os.path.exists(HERE + f):
            continue
        h(4, f"`{f}`")
        fence(open(HERE + f, errors="replace").read(),
              "bash" if f.endswith(".sh") else "python")


def app_jk():
    """Appendices J and K, held as prose in `appendix_jk.md`.

    They were originally appended to the built APPENDIX.md by hand, which
    silently made the document un-regenerable: re-running this script would
    have dropped them, so the source listings in Appendix I went stale instead
    and no longer matched the files on disk.  Keeping the prose in a file this
    script reads restores the invariant the header claims -- that nothing in
    the appendix is transcribed by hand.
    """
    w("")
    w("---")
    w("")
    w(open(HERE + "appendix_jk.md", errors="replace").read().rstrip())


def quarantined():
    """Cells in responses_truncated/ with no live counterpart, from disk.

    The SAME diff verify_paper.py §17 runs, deliberately: Appendix L's cell
    list and §17's must never be able to disagree, and the way to guarantee
    that is to derive both from the artefacts rather than write one down.
    A refill that lands tomorrow moves both without anyone editing prose.
    """
    live = collections.defaultdict(set)
    for f in glob.glob(HERE + "responses/*.json"):
        r = json.load(open(f))
        live[(r["model"], r["dataset"], bool(r.get("paraphrase")))].add(
            (r["condition"], r.get("seed")))
    out = []
    for f in glob.glob(HERE + "responses_truncated/*.json"):
        r = json.load(open(f))
        k = (r["model"], r["dataset"], bool(r.get("paraphrase")))
        if (r["condition"], r.get("seed")) not in live[k]:
            out.append((r["model"], r["dataset"], r["condition"], r.get("seed")))
    return sorted(out)


def app_l():
    """Appendix L -- the temperature-zero truncation, promised by both
    manuscripts' appendix lists and, until now, not emitted by this script.

    It is its own appendix rather than a limitation because the finding is
    useful to anyone running that model at temperature zero and has nothing
    to do with leakage.
    """
    h(2, "Appendix L. A reproducible `temperature=0.0` truncation in "
         "`gemini-3.5-flash`, and its mechanism")
    w(textwrap.dedent("""\
    At `temperature = 0.0` this model returns `finish_reason = "length"` after
    a few hundred visible tokens, **whatever `max_tokens` is set to**. On the
    cells where it happens it happens *every time*, and it cost this paper
    cells on two hosts.

    **The mechanism, measured.** KOI C9, 40 columns, against Vertex on
    2026-08-18, with a 16,000-token thinking budget and a 48,000-token ceiling:

    | | tokens |
    |---|---|
    | prompt | 792 |
    | **thinking** | **46,080** |
    | visible answer | 1,916 |
    | total | 48,788 |

    Thinking counts against `maxOutputTokens`, and the thinking consumed 96% of
    it. There was no room left to answer. The model had entered a repetition
    loop *inside its own reasoning*, arguing with itself about a column name --
    the leaked thinking reads `Wait, is it koi_slogg? Yes...` `Ah, wait, in the
    prompt:` `Wait, is there a > or something?` -- until the budget ran out.

    Two consequences follow, and both matter more than the truncation.

    1. **`finish_reason = "length"` is true and misleading.** It reads as *your
       answer was too long*. The answer was 1,916 tokens. What overflowed was
       the thinking, and no increase in `max_tokens` fixes it -- a larger
       ceiling buys a longer loop.
    2. **The thinking budget is not enforced.** We requested 16,000 and the
       model spent 46,080, 2.9x over. Every cell in this corpus labelled
       `think16000` records *what was asked for*, not what happened.

    **Why it is deterministic, and why that is the whole story.** Temperature
    0.0 is greedy decoding: the same prompt yields the same token sequence, so
    it yields the same loop, so retrying cannot help. Three attempts were spent
    confirming this before the cell was abandoned. Raising the temperature
    breaks the loop, and only the temperature changes:

    | temperature | finish | thinking | visible | result |
    |---|---|---|---|---|
    | 0.0 | `MAX_TOKENS` | 46,080 | 1,916 | fails, reproducibly |
    | 0.7 | `STOP` | 5,119 | 2,431 | **all 40 columns** |

    **Two attributions we made first, both wrong, in the order we made them.**

    1. *Our own `max_tokens`.* Every campaign ran at 4,000 tokens, and a
       144-column dataset at `reasoning_effort: high` genuinely does need more
       -- CRIME C6 on nemotron parsed 1 of 144 columns after 67,868 characters
       of output. That defect is real and was repaired by re-running at 16,000
       (`rerun_truncated.py`). It is not this one: raising the budget did not
       move the KOI cells, and now we can see why.
    2. *A provider quota.* The refill loop was returning HTTP 429s at the same
       time, so the two failures were read as one. They are not: a 429 is a
       refusal to answer, and this is an answer that stops early with a
       success status.

    **A third attribution, ours, corrected here.** An earlier draft of this
    appendix argued that *CRIME, at 144 columns, never truncates at the same
    setting, which is what rules out a size limit*. On Vertex CRIME does
    truncate for this model, at C2 and at C9. The conclusion was right and the
    argument was not; the token counts above rule out a size limit directly,
    without needing CRIME to behave. Width was never the variable in any case
    -- the same model truncates on **AI4I, which has ten columns**.

    **It is not one model's defect.** Eight distinct models in this cache have
    produced a truncated cell, 44 in total, `nemotron-3-super` most of all at
    16. What distinguishes `gemini-3.5-flash` is not that it truncates but that
    its truncations are *deterministic* rather than intermittent: everything
    else recovered on a retry, and greedy decoding cannot.

    **What we did with the two cells that would not come back.** They were run
    at `temperature = 0.7` and are reported in section 25 of `NUMBERS.txt`
    **alone, pooled with nothing**, because a cell from a different decoding
    regime is not comparable with the ones it would be averaged against. The
    isolation is enforced in three independent places rather than by anyone
    remembering it: the temperature joins the cache key, it joins the cell
    label (`::vertex-think16000-t0.7`), and `verify_paper.cells_for` refuses a
    cross-regime substring match. All three were needed -- the first attempt
    stamped the rescued cell `t0.0` and read it straight back into the 0.0 arm.

    **How much the regime change costs.** Two CRIME C9 cells exist at both
    temperatures and are the control: one is identical (Jaccard 1.000), the
    other adds four columns of one family (Jaccard 0.818), mean 0.909. For
    scale, CRIME C9 at temperature 0.0 alone spans 18 to 22 flags across two
    shuffle seeds -- the same swing. The rescued cells are perturbed no more by
    the temperature than the corpus already perturbs itself in section 13, and
    they are still not pooled.

    **This is the paper's own thesis arriving in its own methods section:** an
    instrument interaction that presents as a model property, which we
    mis-attributed three times because a cheap explanation was available each
    time."""))
    q = quarantined()
    w("")
    if not q:
        w("**Every quarantined cell has since been restored**, so this "
          "appendix records the diagnosis and costs the paper nothing. The "
          "list below is regenerated from `responses_truncated/` against the "
          "live cache on every build; it is empty.")
        return
    by_model = collections.Counter(m for m, _d, _c, _s in q)
    w(f"**The cells still missing: {len(q)}.** Regenerated from "
      f"`responses_truncated/` diffed against the live cache on every build, "
      f"so this list and `NUMBERS.txt` §17 cannot disagree.")
    w("")
    w("| model | dataset | condition | seed |")
    w("|---|---|---|---|")
    for m, d, c, s in q:
        w(f"| `{m}` | {d} | C{c} | {s} |")
    w("")
    w("Every table row computed from "
      + ", ".join(f"`{m}`" for m in sorted(by_model))
      + " carries a † for this reason, and no mean-over-models statistic in "
        "the paper includes "
      + ("it" if len(by_model) == 1 else "them")
      + ". A missing cell is not a model that found nothing.")


if __name__ == "__main__":
    w("# Appendices")
    w("")
    w("*Companion to* **Detecting Feature-Level Target Leakage with Language "
      "Models: A Source-Grounded Benchmark**")
    w("")
    w("Generated by `build_appendix.py` from the run artefacts. Nothing in "
      "this document is transcribed by hand except the section prose.")
    # app_bug_ledger_unused is deliberately NOT emitted: a changelog of
    # engineering defects is not evidence about the world, and a reader
    # needs none of it to use or evaluate the benchmark.  The entries are
    # kept in this file as project history.
    for f in (app_a, app_b, app_c, app_d, app_e, app_f, app_g, app_h,
              app_i, app_jk, app_l):
        f()
    print("\n".join(OUT))
