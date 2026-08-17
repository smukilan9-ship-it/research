"""Does the appendix deliver what the manuscripts promise, and name the
conditions the instrument actually has?

WHY A SIXTH CHECKER

  The five existing checkers all read PAPER*.md against NUMBERS.txt, and all
  five check NUMBERS.  Between them they cannot see either of the errors that
  created this file, because neither is a number and neither is in PAPER*.md:

    verify_tables      a table row against its source row
    verify_arithmetic  a stated relation against itself
    claim_audit        a decimal against NUMBERS.txt
    prose_pins         a sentence's quantity against the function computing it
    consistency        a figure across the deliverables

  APPENDIX.md is not read by any of them.  It is generated, and the project
  treats generated artefacts as safe -- but regeneration protects the numbers
  inside a section, not the section's NAME, and not whether the section is
  emitted at all.  That is the same gap prose_pins closed one level down:
  regeneration protects the tables, nothing protected the sentences.

THE TWO ERRORS THAT CREATED IT

  1. APPENDIX L WAS PROMISED AND NEVER EMITTED.  Both manuscripts' appendix
     lists ended with "L. A reproducible temperature=0.0 truncation in
     gemini-3.5-flash".  build_appendix.py's emit list ran app_a..app_jk and
     stopped; APPENDIX.md ran A to K.  The blind audit's item 3 records the
     truncation finding as "promoted to Appendix L" -- it was promoted in the
     manuscripts and never written into the generator, so a referee following
     the §8 limitation to Appendix L found nothing.

  2. APPENDIX D NAMED A CONDITION THAT DOES NOT EXIST.  Its headings were one
     numbering scheme behind the instrument: C5's expert framing was labelled
     C6, C6's derivation clause was labelled **C8**, and both derivation
     clauses were described as "appended to C6" when prompts.py appends them
     to C1 -- which is load-bearing, because C6 - C1 is what isolates the
     single variable the paper's central claim rests on.  PAPER.md's own
     appendix list propagated the phantom: "the C6, C7, C8 and C9 clauses".
     There is no C8.  handoff/04_EXPERIMENT.md says so in as many words, and
     nothing checked the manuscripts against it.

WHAT IT CHECKS

  promised == delivered   every letter a manuscript's appendix list names is a
                          section APPENDIX.md emits, and vice versa.  An
                          orphan section is as much a defect as a missing one:
                          it means the manuscript stopped describing its own
                          companion.

  conditions are real     every C<n> named anywhere in the deliverables is a
                          condition prompts.CONDITIONS actually defines.  This
                          is what catches C8, and it generalises: renumbering
                          the ladder, or dropping a condition, fires it.

  D covers the ladder     every condition the instrument defines is mentioned
                          somewhere in Appendix D.  A prompt that ran and is
                          not in the appendix is unreproducible.

  cross-references land   every "Appendix X" reference inside APPENDIX.md
                          points at a letter that exists.  This is the check
                          claim_audit.py runs for [N §x] against NUMBERS.txt,
                          applied to the other generated document.

  Needs no raw data and no network, like the other five: it reads the three
  markdown files and imports prompts.py, which is pure strings.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import prompts as P

MANUSCRIPTS = ["PAPER.md", "PAPER_SHORT.md"]
APPENDIX = "APPENDIX.md"


def read(name):
    return open(HERE + name, errors="replace").read()


def promised(md):
    """Letters named in a manuscript's own appendix list.

    Scoped to the text after the `## Appendices` heading: a bold `**B.**` in
    the body is a record label (Appendix B numbers its records B1, B2, ...),
    not a promise about a section, and counting those would make the check
    fire on the paper's own prose.
    """
    m = re.search(r"^#+\s*Appendices\s*$", md, re.M)
    if not m:
        return None
    return set(re.findall(r"\*\*([A-Z])\.\*\*", md[m.end():]))


def delivered(app):
    return set(re.findall(r"^##\s+Appendix\s+([A-Z])\.", app, re.M))


def conditions_named(text):
    """Every C<n> token in a deliverable, as ints."""
    return {int(n) for n in re.findall(r"\bC(\d+)\b", text)}


def appendix_d(app):
    """The body of Appendix D, for the coverage check."""
    m = re.search(r"^##\s+Appendix\s+D\.", app, re.M)
    if not m:
        return ""
    nxt = re.search(r"^##\s+Appendix\s+[A-Z]\.", app[m.end():], re.M)
    return app[m.end():m.end() + nxt.start()] if nxt else app[m.end():]


def main():
    print("=" * 78)
    print("APPENDIX STRUCTURE — promised vs delivered, and the condition ladder")
    print("=" * 78)
    bad = 0

    if not os.path.exists(HERE + APPENDIX):
        print(f"  FAIL  {APPENDIX} is missing entirely.")
        return 1
    app = read(APPENDIX)
    got = delivered(app)
    print(f"\n  {APPENDIX} emits {len(got)} sections: "
          f"{', '.join(sorted(got))}")

    # ---- promised == delivered -----------------------------------------
    for name in MANUSCRIPTS:
        if not os.path.exists(HERE + name):
            continue
        want = promised(read(name))
        if want is None:
            print(f"  FAIL  {name} has no `## Appendices` section to check.")
            bad += 1
            continue
        missing = sorted(want - got)
        orphan = sorted(got - want)
        if missing:
            for L in missing:
                print(f"  FAIL  {name} promises Appendix {L}; "
                      f"{APPENDIX} does not emit it.")
                print(f"        Either add an app_{L.lower()}() to "
                      f"build_appendix.py and regenerate, or stop promising it.")
            bad += len(missing)
        if orphan:
            for L in orphan:
                print(f"  FAIL  {APPENDIX} emits Appendix {L}; "
                      f"{name} never mentions it.")
            bad += len(orphan)
        if not missing and not orphan:
            print(f"  ok    {name:<16} promises {len(want)} appendices, "
                  f"all delivered, none orphaned")

    # ---- every condition named is a condition that exists ---------------
    real = set(P.CONDITIONS)
    print(f"\n  prompts.CONDITIONS defines: "
          f"{', '.join('C' + str(c) for c in sorted(real))}")
    for name in MANUSCRIPTS + [APPENDIX]:
        if not os.path.exists(HERE + name):
            continue
        named = conditions_named(read(name))
        phantom = sorted(named - real)
        if phantom:
            for c in phantom:
                print(f"  FAIL  {name} names C{c}, which prompts.py does not "
                      f"define.")
                for ln, line in enumerate(read(name).split("\n"), 1):
                    if re.search(rf"\bC{c}\b", line):
                        print(f"        L{ln}: {line.strip()[:88]}")
                        break
            bad += len(phantom)
        else:
            print(f"  ok    {name:<16} names only real conditions "
                  f"({len(named)} distinct)")

    # ---- Appendix D covers the ladder -----------------------------------
    d = appendix_d(app)
    if d:
        shown = conditions_named(d)
        gap = sorted(real - shown)
        if gap:
            print(f"  FAIL  Appendix D never mentions "
                  f"{', '.join('C' + str(c) for c in gap)}; a prompt that ran "
                  f"and is not in the appendix is unreproducible.")
            bad += 1
        else:
            print(f"  ok    Appendix D    mentions every condition in the "
                  f"ladder")
    else:
        print(f"  FAIL  {APPENDIX} has no Appendix D to check.")
        bad += 1

    # ---- internal cross-references land ---------------------------------
    refs = {m for m in re.findall(r"Appendix ([A-Z])\b", app)}
    dangling = sorted(refs - got)
    if dangling:
        for L in dangling:
            print(f"  FAIL  {APPENDIX} refers to Appendix {L}, which it does "
                  f"not contain.")
        bad += len(dangling)
    else:
        print(f"  ok    {APPENDIX:<16} every internal 'Appendix X' reference "
              f"resolves")

    print(f"\n  {bad} failure(s).")
    if not bad:
        print("  The appendix delivers what the manuscripts promise, and every")
        print("  condition named is one the instrument defines.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
