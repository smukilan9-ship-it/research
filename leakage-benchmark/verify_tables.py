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
    # NUMBERS.txt truncates model labels to a fixed width, so these keys are
    # the TRUNCATED forms section 19 actually prints.  The paper writes the
    # Vertex six with a marker; check_mcnemar strips it before lookup.
    "nemotron-3-super §19": "nemotron-3-super-120b-a12b::high",
    "gemini-3.1-pro-preview": "gemini-3.1-pro-preview::vertex-t",
    "gemini-2.5-pro": "gemini-2.5-pro::vertex-think1600",
    "grok-4.20-reasoning": "grok-4.20-reasoning::vertex-t0.0",
    "grok-4.20-non-reasoning": "grok-4.20-non-reasoning::vertex-",
    "grok-4.1-fast-reasoning": "grok-4.1-fast-reasoning::vertex-",
    "grok-4.1-fast-non-reasoning": "grok-4.1-fast-non-reasoning::ver",
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


def check_mcnemar(txt, md, fail):
    """The §6.5 uncertainty table: `model | F1 C1 | F1 C6 | dF1 | CI | b | c | p`.

    Eight cells, so paper_tables() -- which wants a condition cell -- skipped
    it, and check_c9_delta wants exactly four.  It was therefore checked by
    NOTHING, and it drifted: `gemini-3.5-flash` read 0.833/0.868 against
    NUMBERS section 19's 0.837/0.871, and six Vertex models that had gained
    rows in section 19 were simply missing from the table.  A table carrying
    every confidence interval in the paper had no checker at all.
    """
    truth = {}
    seg = txt[txt.index("19. UNCERTAINTY"):txt.index("20. STRATUM D")]
    for line in seg.split("\n"):
        # nine capture groups now: the Holm-adjusted p was added beside the raw
        # one.  The paper's table grew a column to match, which took this
        # checker from 16 rows to 0 without failing -- it simply stopped
        # matching, which is why the row count is printed.
        m = re.match(r"^  (\S.*?)\s+([\d.]+)\s+([\d.]+)\s+([+-][\d.]+)\s+"
                     r"\[([+-][\d.]+), ([+-][\d.]+)\]\s+n=\d+\s+(\d+)\s+(\d+)\s+"
                     r"([\d.]+)\s*\**\s*([\d.]+)",
                     line)
        if m:
            truth[m.group(1).strip()] = dict(
                c1=float(m.group(2)), c6=float(m.group(3)), d=float(m.group(4)),
                lo=float(m.group(5)), hi=float(m.group(6)),
                b=int(m.group(7)), c=int(m.group(8)), p=float(m.group(9)),
                holm=float(m.group(10)))
    n = 0
    for ln, line in md:
        cells = [re.sub(r"[`*†‡]", "", x).strip() for x in
                 line.strip().strip("|").split("|")]
        if len(cells) != 9:
            continue
        key = ALIAS.get(cells[0])
        if key not in truth:
            # tolerate either truncation width, and a display name that is
            # simply a prefix of the label section 19 prints
            cand = [k for k in truth
                    if key and (k.startswith(key) or key.startswith(k))]
            if not cand:
                cand = [k for k in truth if k.startswith(cells[0])]
            if len(cand) != 1:
                continue
            key = cand[0]
        t = truth[key]
        num = lambda x: float(x.replace("−", "-").replace("+", ""))
        try:
            c1, c6, d = num(cells[1]), num(cells[2]), num(cells[3])
            lo, hi = [num(x) for x in cells[4].strip("[]").split(",")]
            bb, cc = int(cells[5]), int(cells[6])
        except (ValueError, IndexError):
            continue
        bad = []
        if abs(c1 - t["c1"]) > 0.0011: bad.append(f"F1C1 {c1} vs {t['c1']}")
        if abs(c6 - t["c6"]) > 0.0011: bad.append(f"F1C6 {c6} vs {t['c6']}")
        if abs(d - t["d"]) > 0.0011: bad.append(f"dF1 {d} vs {t['d']}")
        if abs(lo - t["lo"]) > 0.0011: bad.append(f"CIlo {lo} vs {t['lo']}")
        if abs(hi - t["hi"]) > 0.0011: bad.append(f"CIhi {hi} vs {t['hi']}")
        if bb != t["b"]: bad.append(f"b {bb} vs {t['b']}")
        if cc != t["c"]: bad.append(f"c {cc} vs {t['c']}")
        # Holm is the column the footnote tells the reader to use, so it is
        # checked; "<0.001" is accepted for anything below 0.0005.
        hs = cells[8].replace("<", "").strip()
        try:
            hv = float(hs)
            if hs.startswith("0.001") and t["holm"] < 0.0005:
                pass
            elif abs(hv - t["holm"]) > 0.0011:
                bad.append(f"Holm {hv} vs {t['holm']:.4f}")
        except ValueError:
            bad.append(f"Holm unparseable: {cells[8]!r}")
        if bad:
            fail.append(f"L{ln:<5} MCNEMAR {cells[0]}: " + "; ".join(bad))
        else:
            n += 1
    # Every model NUMBERS has a row for must appear, or the table is a silent
    # subset -- which is how six Vertex models went missing.
    shown = set()
    for _, l in md:
        cs = l.strip().strip("|").split("|")
        if len(cs) != 9:
            continue
        nm = re.sub(r"[`*†‡]", "", cs[0]).strip()
        k = ALIAS.get(nm, nm)
        shown |= {t for t in truth if t.startswith(k) or k.startswith(t)}
    missing = [k for k in truth if k not in shown]
    if missing and n:
        fail.append(f"      MCNEMAR: NUMBERS section 19 has rows the paper omits: "
                    f"{', '.join(sorted(missing))}")
    return n


def check_stratb_c9(txt, md, fail):
    """The §7.3 Stratum B table: `model | P C6→C9 | fp | R C6→C9 | dF1`.

    Five cells with arrows inside them, so no existing locator matches it.
    Added when §7.3 was rewritten; without this the table would have been
    unchecked prose, which is how the §6.5 table drifted.

    Names resolve by PREFIX rather than through ALIAS.  NUMBERS.txt truncates
    model labels to a different width in every section -- 31 chars in section
    7, 31 in section 6, 32 in section 19 -- and a single alias map cannot
    carry all three without one of them silently failing to resolve.
    """
    try:
        seg = txt[txt.index("--- C6 vs C9 on Stratum B (MATCHED cells)"):
                  txt.index("--- C9 - C6 on Stratum B")]
    except ValueError:
        fail.append("      STRATB-C9: NUMBERS.txt has no matched Stratum B block")
        return 0
    truth = {}
    for line in seg.split("\n"):
        m = re.match(r"^(\S.*?)\s+C(\d)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+"
                     r"(\d+)\s+(\d+)\s+(\d+)", line)
        if m:
            truth.setdefault(m.group(1).strip(), {})[int(m.group(2))] = dict(
                P=float(m.group(3)), R=float(m.group(4)), F1=float(m.group(5)),
                fp=int(m.group(7)))
    n = 0
    for ln, line in md:
        c = [re.sub(r"[`*†‡]", "", x).strip() for x in
             line.strip().strip("|").split("|")]
        if len(c) != 5 or "→" not in c[1]:
            continue
        cand = [k for k in truth if k.startswith(c[0])]
        if len(cand) != 1:
            if c[0] not in ("model",):
                fail.append(f"L{ln:<5} STRATB-C9 {c[0]}: resolves to "
                            f"{len(cand)} rows in NUMBERS section 7")
            continue
        t = truth[cand[0]]
        if 6 not in t or 9 not in t:
            continue
        num = lambda x: float(x.replace("−", "-").replace("+", ""))
        try:
            p6, p9 = [num(x) for x in c[1].split("→")]
            f6, f9 = [int(x) for x in c[2].split("→")]
            r6, r9 = [num(x) for x in c[3].split("→")]
            d = num(c[4])
        except ValueError:
            continue
        bad = []
        for lbl, got, exp in (("P C6", p6, t[6]["P"]), ("P C9", p9, t[9]["P"]),
                              ("fp C6", f6, t[6]["fp"]), ("fp C9", f9, t[9]["fp"]),
                              ("R C6", r6, t[6]["R"]), ("R C9", r9, t[9]["R"]),
                              ("dF1", d, t[9]["F1"] - t[6]["F1"])):
            if abs(got - exp) > 0.0011:
                bad.append(f"{lbl} {got} vs {exp:.3f}")
        if bad:
            fail.append(f"L{ln:<5} STRATB-C9 {c[0]}: " + "; ".join(bad))
        else:
            n += 1
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
    nm = check_mcnemar(txt, md, fail)
    nx = check_stratb_c9(txt, md, fail)
    ns = check_subtype(txt, md, fail)
    print(f"\ncorpus rows verified     {nc}")
    print(f"baseline rows verified   {nb}")
    print(f"downstream rows verified {nd}")
    print(f"C9-delta rows verified   {n9}")
    print(f"McNemar rows verified    {nm}")
    print(f"StratB-C9 rows verified  {nx}")
    print(f"subtype rows verified    {ns}")
    for f in fail:
        print("  " + f)
    print(f"\nTOTAL VERIFIED {ok+nc+nb+nd+n9+nm+nx+ns}   FAILURES {bad+miss+len(fail)}")
    if bad or miss or fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
