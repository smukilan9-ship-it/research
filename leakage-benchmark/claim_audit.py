"""Check every claim in the manuscript against the evidence behind it.

WHY, AND WHY THIS SHAPE

  TMLR accepts on two questions, and the first is whether the claims are
  supported by accurate, convincing and clear evidence.  Novelty and
  significance are explicitly NOT acceptance criteria.  So the failure mode
  that matters here is not "this isn't new enough" -- it is "this sentence
  says more than the numbers underneath it".

  That makes priority claims strictly bad trades: "the first benchmark" buys
  nothing at TMLR because novelty is not scored, and costs something because
  it is a claim a reviewer can ask us to support.

WHAT IT FLAGS

  PRIORITY   first / no X exists / novel / unprecedented -- unsupportable in
             general, and worthless under TMLR's criteria.
  UNIVERSAL  all / every / never / always / none / only -- true or false, and
             a reviewer will pick one and check it.
  CAUSAL     proves / demonstrates / shows that / because -- claims a
             mechanism the design may not identify.
  NUMBER     a decimal in prose.  Classified as DIRECT (the token appears in
             NUMBERS.txt), DERIVED (it is a difference of two tokens that do,
             within rounding), or UNSOURCED.

  Nothing here is automatic.  The output is a worklist for a human read; the
  script's job is to make sure no sentence escapes the read.
"""
import re, sys, os, itertools

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
# Optional manuscript override: the 12-page PAPER_SHORT.md is built from
# the same NUMBERS.txt and must pass the same checks.
TARGET = sys.argv[1] if len(sys.argv) > 1 else "PAPER.md"

PRIORITY = re.compile(r"\b(the first\b|first benchmark|no (?:such )?benchmark|"
                      r"novel|unprecedented|nobody has|has never been|"
                      r"we are the first)\b", re.I)
UNIVERSAL = re.compile(r"\b(all |every |each of|never|always|none of|only |"
                       r"exclusively|cannot|impossible|no [a-z]+ can)\b", re.I)
CAUSAL = re.compile(r"\b(proves?|demonstrates? that|shows? that|establishes?|"
                    r"confirms? that|therefore|hence|because)\b", re.I)


def sentences(md):
    """(line number, sentence) for prose only -- no tables, code or headings."""
    out, buf, start = [], [], 0
    fence = False
    for i, raw in enumerate(md.split("\n"), 1):
        t = raw.strip()
        if t.startswith("```"):
            fence = not fence
            continue
        if fence or t.startswith(("|", "#", ">", "*[")):
            buf = []
            continue
        if not t:
            buf = []
            continue
        if not buf:
            start = i
        buf.append(t)
        joined = " ".join(buf)
        for s in re.split(r"(?<=[.!?])\s+", joined):
            if len(s) > 25 and s[-1] in ".!?":
                out.append((start, s))
        if joined and joined[-1] in ".!?":
            buf = []
    # dedupe, keep first occurrence
    seen, uniq = set(), []
    for ln, s in out:
        k = s[:80]
        if k not in seen:
            seen.add(k); uniq.append((ln, s))
    return uniq


def number_status(sent, have):
    """DIRECT / DERIVED / UNSOURCED for each decimal in the sentence."""
    out = []
    for m in re.finditer(r"(?<![\w.])(\d+\.\d{2,3})(?![\w])", sent):
        v = m.group(1)
        if v in have:
            out.append((v, "DIRECT")); continue
        # a difference of two reported numbers, within rounding
        try:
            f = float(v)
            hit = any(abs(abs(float(a) - float(b)) - f) < 0.0015
                      for a, b in itertools.combinations(list(have)[:4000], 2)
                      if a.count(".") == 1 and b.count(".") == 1)
        except Exception:
            hit = False
        out.append((v, "DERIVED" if hit else "UNSOURCED"))
    return out


def main():
    md = open(HERE + TARGET).read()

    # ---- do the [N §x] citations point at sections that EXIST? -------------
    # Nothing checked this, and the paper shipped a "[N §22]" for a section
    # NUMBERS.txt does not have -- the numbering runs 21, 23, and the citation
    # was written from the section's position rather than its number.  A
    # citation to a missing section is worse than no citation: it reads as
    # sourced.
    have = set(re.findall(r"^(\d+)\. [A-Z]", open(HERE + "NUMBERS.txt",
                                                  errors="replace").read(),
                          re.M))
    cited = set(re.findall(r"\[N ((?:§\d+(?:, )?)+)\]", md))
    bad = sorted({n for grp in cited for n in re.findall(r"\d+", grp)}
                 - have, key=int)
    print(f"\nNUMBERS SECTION CITATIONS  ({len(bad)} dangling)")
    if bad:
        for n in bad:
            for line in md.split("\n"):
                if f"§{n}]" in line or f"§{n}," in line:
                    print(f"  §{n} does not exist in NUMBERS.txt: "
                          f"{line.strip()[:90]}")
                    break
    else:
        print("  every [N §x] points at a section NUMBERS.txt emits")
    nums = open(HERE + "NUMBERS.txt").read()
    have = set(re.findall(r"\d+\.\d{2,4}", nums))
    rows = []
    for ln, s in sentences(md):
        tags = []
        if PRIORITY.search(s): tags.append("PRIORITY")
        if UNIVERSAL.search(s): tags.append("UNIVERSAL")
        if CAUSAL.search(s): tags.append("CAUSAL")
        ns = number_status(s, have)
        if any(st == "UNSOURCED" for _, st in ns): tags.append("UNSOURCED-NUM")
        if tags:
            rows.append((ln, tags, ns, s))
    print(f"{len(sentences(md))} prose sentences; {len(rows)} carry a claim "
          f"that needs checking\n")
    for tag in ("PRIORITY", "UNSOURCED-NUM", "UNIVERSAL", "CAUSAL"):
        sel = [r for r in rows if tag in r[1]]
        print("=" * 78)
        print(f"{tag}  ({len(sel)})")
        print("=" * 78)
        for ln, tags, ns, s in sel:
            extra = " ".join(f"[{v}:{st}]" for v, st in ns if st != "DIRECT")
            print(f"L{ln:<5} {s[:200]}")
            if extra:
                print(f"       {extra}")
        print()


if __name__ == "__main__":
    main()
