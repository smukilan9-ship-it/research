"""Verify every table cell in the manuscript against its actual source row.

WHY claim_audit.py WAS NOT ENOUGH

  claim_audit asks: does this decimal appear somewhere in NUMBERS.txt?  That
  cannot catch a STALE number, because a stale number usually still exists
  somewhere in the file.  Two got through:

    0.658  passed because TITANIC's B3 downstream F1 is 0.6577
    0.894  passed as a "derived" difference of two unrelated numbers

  Both were pre-audit values sitting in post-audit tables.  A number is not
  verified by existing.  It is verified by matching THE ROW IT CLAIMS TO BE.

WHAT THIS DOES

  Parses NUMBERS.txt into (block, model, condition) -> metrics, parses every
  markdown table in PAPER.md that carries a model name and a condition, and
  compares cell against cell.  Anything that does not match, or cannot be
  located at all, is printed.  No number is trusted for existing.
"""
import re, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
# Optional manuscript override: the 12-page PAPER_SHORT.md is built from
# the same NUMBERS.txt and must pass the same checks.
TARGET = sys.argv[1] if len(sys.argv) > 1 else "PAPER.md"

# paper label -> NUMBERS.txt model string
# A trailing dagger is a FOOTNOTE MARKER, not part of a model's name:
# S8 marks gemini-3.5-flash's rows provisional in the tables themselves, and
# a checker that read the marker as part of the label would have reported
# every one of those rows UNMAPPED instead of verifying it.
ALIAS = {
    "gpt-5.6-sol": "gpt-5.6-sol-xhigh", "gpt-5.6-sol xhigh": "gpt-5.6-sol-xhigh",
    "claude-opus-5": "claude-opus-5-max", "claude-opus-5 max": "claude-opus-5-max",
    "gemini-3.7": "gemini-3.7-flash", "gemini-3.7-flash": "gemini-3.7-flash",
    "gemini-3.5": "gemini-3.5-flash", "gemini-3.5-flash": "gemini-3.5-flash",
    "Kimi-K3": "Kimi-K3::high", "Kimi-K3 high": "Kimi-K3::high",
    "GLM-5.2": "GLM-5.2::high", "GLM-5.2 high": "GLM-5.2::high",
    "Qwen3-480B": "Qwen3-Coder-480B", "Qwen3-Coder-480B": "Qwen3-Coder-480B",
    "nemotron-3-super": "nemotron-3-super-120b-a12b::hig",
    "DeepSeek-V4-Pro": "DeepSeek-V4-Pro::high",
    "DeepSeek-V4-Pro high": "DeepSeek-V4-Pro::high",
    "deepseek-v4-flash": "deepseek-v4-flash-0731::high",
}

BLOCKS = {
    "C1vC6": ("--- C1 vs C6  (matched cells)", "--- subtype recall, C1 vs C6"),
    "C6vC9": ("--- C6 vs C9  (matched cells)", "--- subtype recall, C6 vs C9"),
    "transfer": ("7. TRANSFER SET", "--- subtype recall on Stratum B"),
}


def load_numbers():
    txt = open(HERE + "NUMBERS.txt").read()
    out = collections.defaultdict(dict)
    for tag, (a, b) in BLOCKS.items():
        try:
            seg = txt[txt.index(a):txt.index(b)]
        except ValueError:
            print(f"  !! block {tag} not found in NUMBERS.txt"); continue
        for line in seg.split("\n"):
            m = re.match(r"^(\S.*?)\s+C(\d)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", line)
            if m:
                out[tag][(m.group(1).strip(), int(m.group(2)))] = (
                    float(m.group(3)), float(m.group(4)), float(m.group(5)))
    # baselines live in their own block
    seg = txt[txt.index("5. BASELINES"):txt.index("6. MAIN CORPUS")]
    for line in seg.split("\n"):
        m = re.match(r"^(B\d) .*?P ([\d.]+)\s+R ([\d.]+)\s+F1 ([\d.]+)", line)
        if m:
            out["baseline"][(m.group(1), None)] = (
                float(m.group(2)), float(m.group(3)), float(m.group(4)))
    return out


def paper_tables():
    """Every markdown table row carrying model + condition + three metrics."""
    rows, cur = [], None
    for ln, line in enumerate(open(HERE + TARGET), 1):
        t = line.strip()
        if not t.startswith("|"):
            continue
        cells = [c.strip().strip("*").strip() for c in t.strip("|").split("|")]
        cells = [re.sub(r"[`*†]", "", c).strip() for c in cells]
        if len(cells) < 4:
            continue
        name, cond = cells[0], cells[1]
        if name:
            cur = name
        m = re.match(r"^C(\d)$", cond)
        if not m or cur is None:
            continue
        nums = []
        for c in cells[2:]:
            try:
                nums.append(float(c))
            except ValueError:
                pass
        if len(nums) >= 3:
            rows.append((ln, cur, int(m.group(1)), tuple(nums[:3])))
    return rows


# ------------------------------------------------------- other table kinds
def check_corpus(txt, md, fail):
    """Stratum tables: dataset | cols | pos."""
    truth = {}
    seg = txt[txt.index("1. CORPUS"):txt.index("2. EVIDENCE RECORDS")]
    for line in seg.split("\n"):
        m = re.match(r"^([A-Z][A-Z0-9]+)\s+(\d+)\s+(\d+)\s", line)
        if m:
            truth[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    n = 0
    for ln, line in md:
        c = [re.sub(r"[`*†]", "", x).strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 3:
            continue
        name = c[0].split(" (")[0].strip()
        if name not in truth:
            continue
        nums = [x for x in c[1:] if re.fullmatch(r"[\d,]+", x)]
        if len(nums) < 2:
            continue
        got = tuple(int(x.replace(",", "")) for x in nums[:2])
        # Stratum B tables carry an extra `rows` column before cols/pos
        cand = [got, tuple(int(x.replace(",", "")) for x in nums[1:3])] \
            if len(nums) >= 3 else [got]
        if truth[name] in cand:
            n += 1
        else:
            fail.append(f"L{ln:<5} CORPUS {name}: paper {cand} vs NUMBERS "
                        f"{truth[name]}")
    return n


def check_baselines(txt, md, fail):
    truth = {}
    seg = txt[txt.index("5. BASELINES"):txt.index("6. MAIN CORPUS")]
    for line in seg.split("\n"):
        m = re.match(r"^(B\d) .*?P ([\d.]+)\s+R ([\d.]+)\s+F1 ([\d.]+)", line)
        if m:
            truth[m.group(1)] = tuple(float(m.group(i)) for i in (2, 3, 4))
        # B1-tuned lives in its own per-stratum block and is a DIFFERENT rule
        # from B1.  Truncating a label to two characters filed its row under
        # B1 and reported the fitted rule as a mismatched frozen one -- the
        # checker was right that the numbers disagreed and wrong about which
        # claim it was reading.
        m = re.match(r"^  Stratum A\s+(B1-tuned)\s+([\d.]+)\s+([\d.]+)\s+"
                     r"([\d.]+)", line)
        if m:
            truth["B1-tuned"] = tuple(float(m.group(i)) for i in (2, 3, 4))
    n = 0
    for ln, line in md:
        c = [re.sub(r"[`*\\]", "", x).strip() for x in line.strip().strip("|").split("|")]
        if not c or not re.match(r"^B\d", c[0]):
            continue
        b = "B1-tuned" if c[0].startswith("B1-tuned") else c[0][:2]
        nums = []
        for x in c[1:]:
            try: nums.append(float(x))
            except ValueError: pass
        if b not in truth or len(nums) < 3:
            continue
        if all(abs(a - t) < 0.0011 for a, t in zip(nums[:3], truth[b])):
            n += 1
        else:
            fail.append(f"L{ln:<5} BASELINE {b}: paper {tuple(nums[:3])} vs "
                        f"NUMBERS {truth[b]}")
    return n


def check_downstream(txt, md, fail):
    """GT ceiling and inflation rows."""
    truth = {}
    seg = txt[txt.index("8. DOWNSTREAM"):txt.index("9. CONFUSION")]
    for line in seg.split("\n"):
        m = re.match(r"^(rf|gb)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)", line)
        if m:
            truth.setdefault(m.group(1), []).append(
                tuple(float(m.group(i)) for i in (2, 3, 4)))
    n = 0
    for ln, line in md:
        c = [re.sub(r"[`*†]", "", x).strip() for x in line.strip().strip("|").split("|")]
        if not c:
            continue
        lab = c[0].lower()
        key = "rf" if "random forest" in lab or lab.startswith("rf") else (
              "gb" if "gradient" in lab or lab.startswith("gb") else None)
        if not key or key not in truth:
            continue
        nums = []
        for x in c[1:]:
            try: nums.append(float(x))
            except ValueError: pass
        if len(nums) < 3:
            continue
        if any(all(abs(a - t) < 0.0011 for a, t in zip(nums[:3], v))
               for v in truth[key]):
            n += 1
        else:
            fail.append(f"L{ln:<5} DOWNSTREAM {key}: paper {tuple(nums[:3])} "
                        f"not among {truth[key]}")
    return n


def check_c9_delta(txt, md, fail):
    """The §7.3 table is `model | F1 C6 | F1 C9 | delta` with no condition
    cell, so paper_tables() skips it entirely -- a silent coverage hole in a
    table that carries the paper's brittleness claim."""
    truth = {}
    seg = txt[txt.index("--- C6 vs C9  (matched cells)"):
              txt.index("--- subtype recall, C6 vs C9")]
    for line in seg.split("\n"):
        m = re.match(r"^(\S.*?)\s+C(\d)\s+[\d.]+\s+[\d.]+\s+([\d.]+)", line)
        if m:
            truth.setdefault(m.group(1).strip(), {})[int(m.group(2))] = \
                float(m.group(3))
    n = 0
    for ln, line in md:
        c = [re.sub(r"[`*†]", "", x).strip() for x in
             line.strip().strip("|").split("|")]
        # EXACTLY four cells: `model | F1 C6 | F1 C9 | delta`.  A >=4 test also
        # matched the six-column paraphrase-decrement table added to S6.3,
        # whose first cell is likewise a model name and whose next three cells
        # are likewise decimals -- so a table about renaming was checked
        # against C9 truth and reported as a mismatch.  A locator that matches
        # on shape must match the shape exactly.
        if len(c) != 4:
            continue
        key = ALIAS.get(c[0])
        if not key or key not in truth or 6 not in truth[key] \
                or 9 not in truth[key]:
            continue
        try:
            f6, f9 = float(c[1]), float(c[2])
            dl = float(c[3].replace("−", "-").replace("+", ""))
        except ValueError:
            continue
        exp6, exp9 = truth[key][6], truth[key][9]
        if abs(f6 - exp6) < 0.0011 and abs(f9 - exp9) < 0.0011 \
                and abs(dl - (exp9 - exp6)) < 0.0011:
            n += 1
        else:
            fail.append(f"L{ln:<5} C9-DELTA {c[0]}: paper ({f6}, {f9}, {dl}) "
                        f"vs NUMBERS ({exp6}, {exp9}, {exp9-exp6:+.3f})")
    return n


def check_subtype(txt, md, fail):
    """The §6.2 table: `model | REASON C1 -> C6 | CONSEQ | TIMING` as
    percentages.  Carries the paper's central mechanism claim."""
    truth = {}
    seg = txt[txt.index("--- subtype recall, C1 vs C6"):
              txt.index("--- C6 vs C9  (matched cells)")]
    for line in seg.split("\n"):
        m = re.match(r"^(\S.*?)\s+C(\d)\s+.*?(\d+)/(\d+)\s+(\d+)%\s+"
                     r"(\d+)/(\d+)\s+(\d+)%\s+(\d+)/(\d+)\s+(\d+)%", line)
        if m:
            truth.setdefault(m.group(1).strip(), {})[int(m.group(2))] = (
                int(m.group(5)), int(m.group(8)), int(m.group(11)))
    n = 0
    for ln, line in md:
        c = [re.sub(r"[`*†]", "", x).strip() for x in
             line.strip().strip("|").split("|")]
        # EXACTLY four cells: `model | F1 C6 | F1 C9 | delta`.  A >=4 test also
        # matched the six-column paraphrase-decrement table added to S6.3,
        # whose first cell is likewise a model name and whose next three cells
        # are likewise decimals -- so a table about renaming was checked
        # against C9 truth and reported as a mismatch.  A locator that matches
        # on shape must match the shape exactly.
        if len(c) != 4:
            continue
        key = ALIAS.get(c[0])
        if not key or key not in truth or 1 not in truth[key]:
            continue
        pcts = [[int(x) for x in re.findall(r"(\d+)%", cell)] for cell in c[1:4]]
        if not all(len(x) == 2 for x in pcts):
            continue
        got1 = tuple(p[0] for p in pcts); got6 = tuple(p[1] for p in pcts)
        if got1 == truth[key][1] and got6 == truth[key].get(6):
            n += 1
        else:
            fail.append(f"L{ln:<5} SUBTYPE {c[0]}: paper C1{got1} C6{got6} vs "
                        f"NUMBERS C1{truth[key][1]} C6{truth[key].get(6)}")
    return n


def main():
    N = load_numbers()
    rows = paper_tables()
    print(f"{len(rows)} model/condition table rows found in {TARGET}\n")
    bad = miss = ok = 0
    for ln, name, cond, got in rows:
        key = ALIAS.get(name)
        if not key:
            print(f"L{ln:<5} UNMAPPED MODEL LABEL {name!r}"); miss += 1; continue
        hits = [(tag, N[tag][(key, cond)]) for tag in N
                if (key, cond) in N[tag]]
        if not hits:
            print(f"L{ln:<5} NO SOURCE ROW  {name} C{cond}"); miss += 1; continue
        if any(all(abs(a - b) < 0.0011 for a, b in zip(got, v)) for _, v in hits):
            ok += 1
        else:
            bad += 1
            print(f"L{ln:<5} MISMATCH  {name} C{cond}")
            print(f"       paper : {got}")
            for tag, v in hits:
                print(f"       {tag:<9}: {v}")
    print(f"\n{ok} model/condition rows verified against their source row")
    print(f"{bad} MISMATCHED, {miss} unlocatable")

    txt = open(HERE + "NUMBERS.txt").read()
    md = [(i, l) for i, l in enumerate(open(HERE + TARGET), 1)
          if l.strip().startswith("|")]
    fail = []
    nc = check_corpus(txt, md, fail)
    nb = check_baselines(txt, md, fail)
    nd = check_downstream(txt, md, fail)
    n9 = check_c9_delta(txt, md, fail)
    ns = check_subtype(txt, md, fail)
    print(f"\ncorpus rows verified     {nc}")
    print(f"baseline rows verified   {nb}")
    print(f"downstream rows verified {nd}")
    print(f"C9-delta rows verified   {n9}")
    print(f"subtype rows verified    {ns}")
    for f in fail:
        print("  " + f)
    print(f"\nTOTAL VERIFIED {ok+nc+nb+nd+n9+ns}   FAILURES {bad+miss+len(fail)}")
    if bad or miss or fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
