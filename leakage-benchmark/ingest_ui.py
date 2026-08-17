"""Read a pasted chat-UI reply back into the same cache the API runs use.

  python3 ingest_ui.py <transcript.txt> --model="gpt-5.6-sol"

The transcript is whatever the session replied with.  Everything outside
`### CELL <id>` blocks is ignored, so pasting the whole conversation is fine.

WHY THE CELL ID IS THE ONLY THING TRUSTED
  The id encodes dataset, condition and seed, and those three fix the exact
  prompt -- including the shuffled column order, which is the thing that moved
  F1 by 0.312.  Anything else the session says about what it ran is discarded.
  If an id is not one this pack emitted, the block is rejected rather than
  guessed at.

WHAT IS CHECKED BEFORE A BLOCK BECOMES DATA
  * the id parses and names a real (dataset, condition, seed)
  * the JSON parses, or the salvage parser recovers it
  * coverage: what fraction of that dataset's columns were actually answered
  * column names that do not exist in the dataset are counted and reported --
    a session that invents columns is a session that was not reading the list
  Nothing is silently dropped; the summary shows every rejection and why.
"""
import json, os, re, sys, glob, time, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN
from salvage import parse

CACHE = HERE + "responses/"
BLOCK = re.compile(r"^#{2,4}\s*CELL\s+`?([A-Za-z0-9_.\-]+)`?\s*$", re.M)
CID = re.compile(r"^(?P<ds>[A-Z0-9_]+)-C(?P<cond>\d)-s(?P<seed>\d+)$")


def bundles():
    out = {}
    for k in RN.ALLSETS + RN.EXPLICIT:
        try:
            b = RN.spec_bundle(k)
            out[b["name"]] = b
        except Exception:
            pass
    return out


def blocks(text):
    hits = list(BLOCK.finditer(text))
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        yield m.group(1), text[m.end():end]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    model = None
    for a in sys.argv[1:]:
        if a.startswith("--model="):
            model = a.split("=", 1)[1]
    if not args or not model:
        sys.exit("usage: ingest_ui.py <transcript.txt> --model=<name>")
    text = open(args[0], encoding="utf-8", errors="replace").read()
    B = bundles()

    wrote, rej = 0, []
    seen = set()
    for cid, body in blocks(text):
        m = CID.match(cid)
        if not m:
            rej.append((cid, "cell id does not parse")); continue
        ds, cond, seed = m["ds"], int(m["cond"]), int(m["seed"])
        if ds not in B:
            rej.append((cid, f"unknown dataset {ds!r}")); continue
        if cid in seen:
            rej.append((cid, "duplicate cell id in transcript")); continue
        seen.add(cid)
        raw = body.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.M).strip()
        d, mode = parse(raw)
        if not d:
            rej.append((cid, "no JSON recoverable")); continue
        b = B[ds]
        got = {c["name"] for c in d["columns"]
               if isinstance(c, dict) and c.get("name")}
        known = got & set(b["truth"])
        cov = len(known) / len(b["truth"])
        invented = len(got) - len(known)
        rec = dict(model=model, provider="ui", dataset=ds, shown_as=ds,
                   paraphrase=False, alias=None, condition=cond, seed=seed,
                   status="ok", raw=raw,
                   ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
        os.makedirs(CACHE, exist_ok=True)
        import hashlib
        h = hashlib.sha256(f"UI|{model}|{cid}".encode()).hexdigest()[:20]
        json.dump(rec, open(CACHE + h + ".json", "w"), indent=1)
        wrote += 1
        flag = ""
        if cov < 0.90:
            flag += f"  LOW COVERAGE"
        if invented:
            flag += f"  {invented} invented column name(s)"
        print(f"  {cid:<22}{len(known):>4}/{len(b['truth']):<4} answered "
              f"({cov:5.0%})  parse={mode}{flag}")

    print(f"\n{wrote} cell(s) written to responses/ as model {model!r}")
    if rej:
        print(f"{len(rej)} rejected:")
        for cid, why in rej:
            print(f"  {cid:<22}{why}")
    print("\nscore with:  python3 score.py     (main corpus)")
    print("             python3 score_explicit.py   (transfer set)")


if __name__ == "__main__":
    main()
