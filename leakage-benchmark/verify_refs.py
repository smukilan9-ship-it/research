"""Every cross-reference in the manuscripts resolves to something real.

WHY THIS EXISTS

  PAPER.md carried "(§7None)" in THREE places, including the second paragraph
  of contribution (2) in the Introduction -- the first page a reviewer reads.
  It is the residue of the section-8-to-section-7 renumbering, where a
  formatter interpolated a None into the reference.  Fourteen checkers were
  green the whole time, because every one of them checks NUMBERS, prose
  quantities, tables, citations, the environment or the appendix, and a section
  reference is none of those.

  verify_appendix.py already checks that every "Appendix X" reference in
  APPENDIX.md resolves.  This is that idea applied to the thing it was never
  applied to: the manuscripts' own section numbers.

THREE NAMESPACES, AND THEY ARE NOT INTERCHANGEABLE

  bare "§4.7"      a section of the manuscript it appears in.  PAPER.md and
                   PAPER_SHORT.md number their sections DIFFERENTLY -- the
                   short paper has ten sections to the long one's eleven -- so
                   each file is resolved against its own headings, never the
                   other's.
  "[N §21]"        a section of NUMBERS.txt.
  "[NE §5]"        a section of NUMBERS_E.txt.

  The same token, "§21", is a NUMBERS section inside brackets and would be a
  missing manuscript section outside them.  Bracketed spans are therefore
  removed before the manuscript pass rather than filtered afterwards.

TWO ALLOWANCES, WRITTEN OUT RATHER THAN PATTERN-MATCHED

  "§6b"                     NUMBERS.txt genuinely has a section 6b (FULL
                            LADDER); it is a real label, not a typo.
  "`verify_paper.py` §17"   prose that names the SCRIPT and then its output
                            section.  The file name carries the namespace, so
                            this is a NUMBERS reference written longhand.

  Anything else of the form "§<digits><letters>" is malformed and fails --
  which is exactly the shape of §7None, and the reason a plain
  "does it resolve" test would have missed it: "§7None" resolves to §7 if you
  stop reading at the first non-digit.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
MANUSCRIPTS = ("PAPER.md", "PAPER_SHORT.md")
FAIL = []

# a reference qualified by the script that emits it: the file name is the
# namespace, so these are NUMBERS references and not manuscript sections
QUALIFIED = re.compile(r"`verify_paper\.py`\s+§[0-9]+[a-z]?")


def sections(path, pat=r"^#{2,4} ([0-9]+(?:\.[0-9]+)*)\.? "):
    out = set()
    for line in open(HERE + path, encoding="utf-8"):
        m = re.match(pat, line)
        if m:
            out.add(m.group(1))
    return out


def numbers_sections(path):
    out = set()
    for line in open(HERE + path, encoding="utf-8"):
        m = re.match(r"^([0-9]+[a-z]?)\. [A-Z]", line)
        if m:
            out.add(m.group(1))
    return out


def lineno(text, idx):
    return text.count("\n", 0, idx) + 1


def check(path, N, NE):
    text = open(HERE + path, encoding="utf-8").read()
    heads = sections(path)
    n_ok = 0

    # --- malformed: digits then letters, anywhere outside a [N ...] span ----
    outside = re.sub(r"\[N ?E? ?[^\]]*\]|\[NE [^\]]*\]", lambda m: " " * len(m.group(0)), text)
    outside = QUALIFIED.sub(lambda m: " " * len(m.group(0)), outside)
    for m in re.finditer(r"§[0-9]+(?:\.[0-9]+)*[A-Za-z]+", outside):
        FAIL.append(f"{path} L{lineno(text, m.start())}: malformed reference "
                    f"{m.group(0)!r}")

    # --- bracketed refs resolve in their own file ---------------------------
    for tag, pool, fname in (("N", N, "NUMBERS.txt"), ("NE", NE, "NUMBERS_E.txt")):
        for bm in re.finditer(r"\[" + tag + r" ([^\]]*)\]", text):
            for r in re.findall(r"§([0-9]+[a-z]?)", bm.group(1)):
                if r in pool:
                    n_ok += 1
                else:
                    FAIL.append(f"{path} L{lineno(text, bm.start())}: "
                                f"[{tag} §{r}] — {fname} has no section {r}")

    # --- bare refs resolve to this manuscript's own headings ----------------
    for m in re.finditer(r"§([0-9]+(?:\.[0-9]+)*)", outside):
        r = m.group(1)
        if r in heads:
            n_ok += 1
        else:
            FAIL.append(f"{path} L{lineno(text, m.start())}: §{r} — "
                        f"{path} has no section {r}")
    return n_ok, len(heads)


def main():
    print("=" * 74)
    print("CROSS-REFERENCES — every §, [N §k] and [NE §k] resolves")
    print("=" * 74)
    N, NE = numbers_sections("NUMBERS.txt"), numbers_sections("NUMBERS_E.txt")
    print(f"  NUMBERS.txt {len(N)} sections   NUMBERS_E.txt {len(NE)} sections\n")
    total = 0
    for path in MANUSCRIPTS:
        n, h = check(path, N, NE)
        total += n
        print(f"  {path:<16} {h:>3} headings   {n:>4} references resolved")
    print()
    if FAIL:
        for f in FAIL:
            print(f"  FAIL  {f}")
        print(f"\n  {len(FAIL)} failure(s).")
        return 1
    print(f"  {total} references, 0 failure(s).")
    print("  Every section a manuscript points at is a section that exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
