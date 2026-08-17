"""Tolerant re-parse of cached responses.

Models sometimes emit structurally invalid JSON: Qwen3-Next produced an orphan
string value with no key inside one of 40 column objects. Discarding the whole
response over one bad entry throws away 39 valid verdicts, so a regex salvage
recovers name/verdict pairs directly from the text.

Salvage recovers the model's ACTUAL verdicts. It never invents one.
"""
import json, re

VERDICT = r"(AVAILABLE|UNAVAILABLE|ABSTAIN)"


def parse(text):
    """Return (dict_or_None, mode) with mode in {json, salvage, none}."""
    if not text:
        return None, "none"
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    cands = [t]
    m = re.search(r"\{.*\"columns\".*\}", t, re.S)
    if m:
        cands.append(m.group(0))
    for c in cands:
        try:
            d = json.loads(c)
            if isinstance(d, dict) and isinstance(d.get("columns"), list):
                return d, "json"
        except Exception:
            pass
    pairs = re.findall(r'"name"\s*:\s*"([^"]+)".{0,400}?"verdict"\s*:\s*"' + VERDICT + r'"',
                       t, re.S)
    if pairs:
        seen, cols = set(), []
        for n, v in pairs:
            if n in seen:
                continue
            seen.add(n)
            cols.append({"name": n, "verdict": v})
        return {"columns": cols}, "salvage"
    return None, "none"
