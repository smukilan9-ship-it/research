"""Which sentences in PAPER.md carry a pinned number, and where they are.

WHY THIS EXISTS

  prose_pins.py checks 30 quantities that the paper states in SENTENCES rather
  than tables, by matching a pattern against the manuscript.  That design has
  one consequence worth making visible before a rewriting pass rather than
  after: REPHRASING A PINNED SENTENCE BREAKS ITS PIN.

  This is the correct behaviour and not a bug -- a pin that stops matching is
  reported as a FAILURE, never skipped, so prose_pins.py tells you exactly
  which sentence a number was moved out of.  But it tells you afterwards, and
  a writer editing prose would rather know beforehand which lines are load
  bearing.

  So this prints the map: line number, pin name, and the text the pin actually
  matched.  Rewrite anything not on the list freely.  Rewrite something on it
  and re-run prose_pins.py before committing.

    python3 pin_map.py                 # human-readable
    python3 pin_map.py --markdown      # a table to paste somewhere

  It asserts nothing and fails nothing.  prose_pins.py is the checker; this is
  a reading aid for the person holding the pen.
"""
import re, sys

# prose_pins.py takes its target manuscript from sys.argv[1], so this module's
# own flag must not be visible when it is imported -- otherwise "--markdown"
# is opened as a filename.  Read the flag, then hand prose_pins a clean argv.
MD = "--markdown" in sys.argv
sys.argv = sys.argv[:1]

import prose_pins as PP                                       # noqa: E402

PAPER = open("PAPER.md", encoding="utf-8").read()
FLAT = " ".join(PAPER.split())

def lineno(idx):
    return PAPER.count("\n", 0, idx) + 1


def collect():
    rows = []
    for pin in PP.pins():
        name, pat = pin[0], pin[1]
        m = re.search(pat, PAPER)
        if m:
            txt = " ".join(m.group(0).split())
            rows.append((lineno(m.start()), name, txt))
        elif re.search(pat, FLAT):
            # matches only once the line wrapping is removed: still pinned,
            # but it spans a line break and has no single anchor line
            rows.append((0, name, "(spans a line break; matches flattened text)"))
        else:
            # prose_pins reports this as n/a only for a duplicate-statement
            # guard whose primary matched; anything else it fails
            rows.append((0, name, "(no match — duplicate guard, or a live failure)"))
    return sorted(rows)


def main():
    rows = collect()
    anchored = [r for r in rows if r[0]]
    if MD:
        print("| line | pin | the text it matches |")
        print("|---|---|---|")
        for ln, name, txt in rows:
            t = (txt[:92] + "...") if len(txt) > 95 else txt
            print(f"| {ln or '—'} | {name} | {t.replace('|', chr(92) + '|')} |")
    else:
        print("=" * 78)
        print("PINNED SENTENCES — rephrasing these breaks prose_pins.py")
        print("=" * 78)
        for ln, name, txt in rows:
            t = (txt[:88] + "...") if len(txt) > 91 else txt
            loc = f"L{ln}" if ln else "—"
            print(f"  {loc:<7} {name:<38} {t}")
    print()
    print(f"  {len(anchored)} of {len(rows)} pins anchor to a specific line.")
    print("  Re-run prose_pins.py after any rewriting pass.")


if __name__ == "__main__":
    main()
