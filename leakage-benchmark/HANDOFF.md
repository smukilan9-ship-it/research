# Where this is, and how to continue

Written 2026-08-23. Read this before touching the manuscript.

## The job

Rewriting `PAPER.md` section by section for TMLR. Each section: verify every
claim against `NUMBERS.txt` first, rewrite, then verify AGAIN, then get the
author's approval before applying. Nothing lands without both passes.

**Done:** Abstract, §1, §2, §3 (§3 drafted, approval pending at compaction).
**Next:** §4 Benchmark construction (3,127 words).
**Author is not writing sections** — earlier plan changed; drafts come from
here and the author approves or redirects.

## Style constraints, all author-specified

- **No first person.** No `we`, `our`, `us`. Exception: text inside a verbatim
  quotation is never altered.
- **No em dashes or en dashes.** Comma, period, colon, or restructure.
- **Readable over compliant.** The first abstract draft kept every verified
  number and was unreadable (`condition ladder`, `complete rosters`,
  `positives`, `deficit`). Plain English wins; length is second.
- **Abstract is one paragraph.**
- `sieve` is being renamed to `screen`, section by section. `consistency.py`
  prints the remaining count on every run. ~70 left at compaction.
- The `humanizer` skill is the style reference.

## Two failure modes that have recurred all day

**1. Compression into plain English is where claims grow.** Twice: `F1 0.905`
became "finds 90% of them" (it is recall 0.950), and "each licensed by a
written record" became "every one backed by a sentence" (six of 68 have no
quotation). Both introduced while making prose clearer. **Verify after the
rewrite, not just before.**

**2. Removing `we` removes the actor and the scope expands to fill it.**
"We hand-read the survivors" became "reading 7,109 archive records surfaced
six", which credits a human with what a regex did. Same shape as the Roberts
overstatement the citation audit caught.

## What is verified and what is not

Fifteen checkers, all green, run them as a block and gate any commit on the
count. **Do not chain a commit after `echo` — that always succeeds and a red
state gets committed.** That happened once (c91cf75) and needed correcting.

    /usr/local/bin/python3   <- the pinned stack. System python3 has no numpy
                                and every checker dies on import, which looks
                                like fifteen failures and is none.

Green does not mean correct. Today an external memo found nine numeric defects
while fifteen checkers passed, and reading claims by hand found eight more.
The checkers cover NUMBERS, tables, pins, citations, refs, the cover sheet.
Nothing covers an un-nominated integer in a paragraph.

## Open items

- **§4.7 says "we went back and read every licensing quote"** and 99 records
  carry `coder: SM`. The author has now glanced through `LABELS_76.md` and
  considers the quotation-backing defensible as a rigour standard. Wording in
  §4.7 and §9 should match whatever the tools-and-authorship statement says.
- **Tools-and-authorship statement not written.** The venue memo recommends it.
  Author's instruction: describe how the generator was built and why it is
  rigorous, in the appendix, WITHOUT naming who wrote it. Methods describe
  construction, not typists.
- **Length.** 25.9k words, ~43 pages markdown, ~65 formatted. §6 is 37%.
  Biggest free win: Appendices F and I inline `NUMBERS.txt` and the source
  code, 53 of the appendix's 80 pages, and both ship as separate files.
- **Rotate the Gemini and NVIDIA keys.** Outstanding since they passed through
  a chat window. Author's action.
- `PAPER_SHORT.md` is NOT submitted. It tracks `PAPER.md` via `verify_short.py`
  and needs the same rewrites eventually.

## Facts worth not rediscovering

- Sample size is **n=12 clusters** for Stratum A intervals, n=3 for Stratum B,
  **n=20** for Stratum E. There is no n=15 result: A and B are never pooled.
- **76 labels took a human decision** (68 leaks + 8 withdrawn). The other 536
  columns are legitimate-by-default under §4.6, which is why precision is a
  lower bound. `make_review_packet.py --labels` prints the 76.
- D1 = CONSEQUENCE recall − REASON recall at C1. D2 = REASON C6 − C1. Real
  corpus +23.2 / +24.8; Stratum E +33.0 / +22.0. The gap widens on unseen
  tables because REASON falls further than CONSEQUENCE.
- `PREREG.md` forbids the phrase "pre-registered" in any derived text. It is a
  stated commitment, not a registration, and `PREREG.md` and `synth/tables.py`
  entered git in the same commit.
- Two Stratum C tables are restored by `fetch_stratc_data.py`, not committed.
