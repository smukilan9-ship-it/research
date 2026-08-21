"""Every in-text citation has a reference entry, and every entry is cited.

WHY THIS EXISTS

  There was no reference section in any manuscript.  Ten works are cited
  in-text across PAPER.md, PAPER_SHORT.md and APPENDIX.md, and none of them
  resolved to anything — which meant `RELATED_WORK.md`'s recorded citation
  warnings were live landmines rather than fixed errors, waiting for whoever
  wrote the bibliography:

    * Bordt et al. (2024) is FIVE authors; an earlier draft had three, dropping
      Rodrigues and Nushi.  Two papers share the title prefix -- 2403.06644 is
      the earlier "Testing Language Models for Memorization of Tabular Data",
      2404.06209 is the COLM paper this work uses.  It is the citation a
      reviewer of section 6.3 is most likely to check, since tabmemcheck is
      theirs.
    * Hegselmann et al. (2023) is SIX authors; an earlier draft had three.
    * Larsen & Becker's YEAR disagrees between RELATED_WORK.md (2019) and all
      three manuscripts (2021).

  An in-text citation that resolves to nothing cannot be checked by a reader
  and cannot be checked by a script either.  This closes both.

WHAT IT DOES NOT DO

  It does not verify that a reference is CORRECT -- that the year is right, the
  authors complete, the venue real.  Only a human with the source can do that,
  and RELATED_WORK.md records which entries were verified against a source and
  which were not.  This checks correspondence, not truth, and says so.

    python3 verify_citations.py
"""
import re
import sys

DOCS = ("PAPER.md", "PAPER_SHORT.md", "APPENDIX.md")
FAIL = []

# Names that look like citations but are not: dataset names, section labels.
NOT_A_CITATION = {"ChessFraud", "Data", "Separately", "Appendix", "Table",
                  "Figure", "Stratum", "Section",
                  # a venue and a dataset host, not authors -- LeakageDetector
                  # is cited by arXiv id inline, and ChessFraud by provenance
                  "ICSME", "Kaggle"}


def cited():
    """Surnames appearing in an in-text citation, across all manuscripts."""
    out = {}
    # TWO forms, and the first version of this file caught only one:
    #   narrative   Sculley et al. (2015)   Larsen and Becker (2021, ch. 24)
    #   parenthetical   (Breck et al., 2019)
    # Requiring a ")" straight after the year missed every citation that
    # continues -- "(2021, ch. 24 of ...)" -- and the checker then reported
    # those works as UNCITED while passing.  A locator that under-matches
    # reports absence as cleanliness.
    pats = [
        re.compile(r"\b([A-Z][A-Za-z\-']+)"
                   r"(?:\s+et al\.|\s*(?:,|&|and)\s*[A-Z][A-Za-z\-']+)*"
                   r"\s*\((\d{4})[a-z]?[,)]"),
        re.compile(r"\(([A-Z][A-Za-z\-']+)"
                   r"(?:\s+et al\.|\s*(?:,|&|and)\s*[A-Z][A-Za-z\-']+)*"
                   r",?\s*(\d{4})[a-z]?\)"),
    ]
    for d in DOCS:
        try:
            s = open(d).read()
        except FileNotFoundError:
            continue
        for pat in pats:
            for m in pat.finditer(s):
                name = m.group(1)
                if name in NOT_A_CITATION:
                    continue
                out.setdefault(name, set()).add(m.group(2))
    return out


def entries():
    """Surnames and years from REFERENCES.md."""
    try:
        s = open("REFERENCES.md").read()
    except FileNotFoundError:
        FAIL.append("REFERENCES.md missing — the manuscripts cite ten works "
                    "and none of them resolve")
        return {}
    out = {}
    # \**  inside the parens too: corrected years are bolded in REFERENCES.md
    # -- "(**2021**)" -- and requiring bare digits made two entries invisible,
    # which the checker then reported as UNCITED.  Under-matching again.
    for m in re.finditer(r"^\**([A-Z][A-Za-z\-']+),[^(]*\(\**(\d{4})\**\)", s, re.M):
        out.setdefault(m.group(1), set()).add(m.group(2))
    return out


def main():
    c, e = cited(), entries()
    print("=" * 74)
    print("CITATIONS — in-text against REFERENCES.md")
    print("=" * 74)
    print(f"  {len(c)} distinct works cited in-text; {len(e)} entries in REFERENCES.md\n")

    for name, years in sorted(c.items()):
        if name not in e:
            FAIL.append(f"cited but NOT in REFERENCES.md: {name} {sorted(years)}")
        elif not (years & e[name]):
            FAIL.append(f"YEAR MISMATCH for {name}: manuscripts say "
                        f"{sorted(years)}, REFERENCES.md says {sorted(e[name])}")
    for name in sorted(e):
        if name not in c:
            print(f"  note   {name} is in REFERENCES.md but never cited in-text "
                  f"(fine for a related-work entry; remove if unintended)")

    # The three warnings RELATED_WORK.md records must be visibly handled.
    try:
        R = open("REFERENCES.md").read()
        if "2404.06209" not in R:
            FAIL.append("Bordt: the COLM arXiv id 2404.06209 is not in "
                        "REFERENCES.md — 2403.06644 is a DIFFERENT paper")
        if "Rodrigues" not in R or "Nushi" not in R:
            FAIL.append("Bordt: five authors, and Rodrigues/Nushi are missing")
        if R.count("Hegselmann") and "Sontag" not in R:
            FAIL.append("Hegselmann: six authors, and the list looks truncated")
    except FileNotFoundError:
        pass

    print()
    for f in FAIL:
        print(f"  FAIL  {f}")
    if not FAIL:
        print("  Every in-text citation resolves, every year agrees, and the")
        print("  three warnings RELATED_WORK.md records are handled.")
        print("  This checks CORRESPONDENCE, not correctness: whether an entry")
        print("  is factually right is recorded in RELATED_WORK.md, not here.")
    print(f"\n  {len(FAIL)} failure(s).")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
