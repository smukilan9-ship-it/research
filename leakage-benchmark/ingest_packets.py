"""Ingest the hand-run paraphrase packets into the response cache.

WHY THIS IS NOT JUST A FILE COPY

  claude-opus-5 and gpt-5.6-sol have provider `ui` -- they were answered in an
  agent loop, so the verdicts arrive as markdown rather than as cache entries.
  This turns them into cells the scorer already knows how to read, in exactly
  the shape runner.py writes:

      dataset     the REAL name          (TITANIC)
      shown_as    the alias the model saw (OCEAN_LINER_VOYAGE)
      alias       {alias column -> real column}, so verdicts join back to truth
      paraphrase  True

  The alias dict is the load-bearing part.  Without it every verdict key is an
  alias, no key matches the truth dict, and verify_paper's join guard drops the
  whole cell -- which reads as "the model found nothing" rather than "the cell
  was never joined".

WHAT IS CHECKED BEFORE ANYTHING IS WRITTEN

  A hand-run pass is exactly where quiet damage happens, so nothing is admitted
  until it survives:

    1. section count matches the packet's prompt count
    2. every (dataset, condition, seed) is one the packet actually asked for --
       no invented cells
    3. the alias dataset name resolves to a real dataset via the SAME map the
       packet was generated from
    4. every column judged is a column that was offered, and every column
       offered was judged -- a short answer scores as "not flagged", which is
       indistinguishable from a considered AVAILABLE
    5. verdicts are from the allowed vocabulary

  A file failing any of these is reported and NOT written.  Partial ingestion of
  a control arm is worse than none: it produces a decrement over a subset while
  looking complete.
"""
import glob, hashlib, json, os, random, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN
import paraphrase as PP

CACHE = HERE + "responses/"
VERDICTS = {"AVAILABLE", "UNAVAILABLE", "ABSTAIN"}
CONDS = [1, 6]

JOBS = [
    ("claude-opus-5-max",
     "/root/.claude/uploads/1dfa598a-70c3-5cb5-8d7b-ecd921e451d9/"
     "1032400d-opus5_paraphrase_verdicts.md"),
    ("gpt-5.6-sol-xhigh",
     "/root/.claude/uploads/1dfa598a-70c3-5cb5-8d7b-ecd921e451d9/"
     "7ce6e041-gpt56_paraphrase_verdicts1.md"),
]

# heading forms seen in practice: "## Prompt 3 — ALIAS C1 seed 1000" and the
# same with a hyphen instead of an em dash.
HEAD = re.compile(
    r"^#{1,3}\s*Prompt\s+(\d+)\s*[—\-–]\s*([A-Z0-9_]+)\s+C(\d)\s+seed\s+(\d+)",
    re.M)


def expected_grid(model):
    """The (real dataset, cond, seed) cells the packet asked this model for."""
    out = set()
    for f in glob.glob(CACHE + "*.json"):
        d = json.load(open(f))
        if d.get("model") == model and not d.get("paraphrase") \
                and d.get("condition") in CONDS:
            out.add((d["dataset"], d["condition"], d.get("seed")))
    # MI has no alias map, so the packet could not include it
    return {t for t in out if t[0] in PP.MAP}


def sections(path):
    body = open(path, errors="replace").read()
    hits = list(HEAD.finditer(body))
    for i, m in enumerate(hits):
        seg = body[m.end(): hits[i + 1].start() if i + 1 < len(hits) else len(body)]
        j = re.search(r"```(?:json)?\s*(.*?)```", seg, re.S)
        yield (int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4)),
               j.group(1).strip() if j else None)


def main():
    alias2real = {v["dataset"]: k for k, v in PP.MAP.items()
                  if isinstance(v, dict) and "dataset" in v}
    rc = 0
    for model, path in JOBS:
        print(f"\n=== {model}")
        if not os.path.exists(path):
            print(f"  MISSING {path}"); rc = 1; continue
        want = expected_grid(model)
        secs = list(sections(path))
        print(f"  {len(secs)} sections parsed; packet asked for {len(want)} cells")

        rows, errs = [], []
        seen = set()
        for n, alias_ds, cond, seed, blob in secs:
            tag = f"prompt {n} ({alias_ds} C{cond} s{seed})"
            real = alias2real.get(alias_ds)
            if real is None:
                errs.append(f"{tag}: alias dataset not in the map"); continue
            key = (real, cond, seed)
            if key not in want:
                errs.append(f"{tag}: not a cell the packet requested"); continue
            if key in seen:
                errs.append(f"{tag}: duplicate cell"); continue
            if not blob:
                errs.append(f"{tag}: no JSON block"); continue
            try:
                obj = json.loads(blob)
            except Exception as e:
                errs.append(f"{tag}: JSON did not parse ({e})"); continue

            b = PP.apply_to(RN.spec_bundle(NAME2KEY[real]))
            offered = set(b["columns"])
            got = {c.get("name") for c in obj.get("columns", [])
                   if isinstance(c, dict)}
            if got - offered:
                errs.append(f"{tag}: judged {len(got - offered)} column(s) never "
                            f"offered, e.g. {sorted(got - offered)[:3]}"); continue
            if offered - got:
                errs.append(f"{tag}: {len(offered - got)} column(s) unjudged, "
                            f"e.g. {sorted(offered - got)[:3]}"); continue
            badv = {c.get("verdict") for c in obj["columns"]} - VERDICTS
            if badv:
                errs.append(f"{tag}: bad verdict(s) {badv}"); continue

            seen.add(key)
            rows.append((real, cond, seed, b, json.dumps(obj)))

        for e in errs[:12]:
            print(f"    REJECT {e}")
        if errs:
            print(f"  {len(errs)} section(s) rejected")
        missing = want - seen
        if missing:
            print(f"  MISSING {len(missing)} requested cell(s): "
                  f"{sorted(missing)[:5]}")

        if errs or missing:
            print("  NOT INGESTED — a partial control arm is worse than none")
            rc = 1
            continue

        for real, cond, seed, b, raw in rows:
            cid = hashlib.sha256(
                f"{model}|para|{b['name']}|{cond}|{seed}".encode()).hexdigest()[:20]
            json.dump(dict(
                model=model, provider="ui", dataset=real, shown_as=b["name"],
                paraphrase=True, alias=b["alias"], condition=cond, seed=seed,
                status="ok", raw=raw,
                ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
                ingested_from=os.path.basename(dict(JOBS)[model])),
                open(CACHE + cid + ".json", "w"), indent=1)
        print(f"  INGESTED {len(rows)} cells")
    return rc


NAME2KEY = {}
for _k in RN.ALLSETS + RN.EXPLICIT:
    try:
        NAME2KEY[RN.spec_bundle(_k)["name"]] = _k
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
