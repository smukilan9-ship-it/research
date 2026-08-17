"""Build a blind subtype-coding packet for an independent second coder.

WHAT THIS IS FOR

  §8 concedes that the subtype partition -- REASON / CONSEQUENCE / TIMING /
  CONTESTED -- is one coder's reading, and §6.2 is an entire results section
  built on it.  The binary label is licensed by a quotation a reader can check;
  the SUBTYPE is not.  No source says "this is a REASON leak".  That is a
  category chosen off a menu by a reader, which is precisely the object
  inter-rater reliability was invented to measure.

WHAT MAKES A CODING PACKET WORTH ANYTHING

  blind      the existing subtype is never shown.  A coder who can see the
             answer is performing confirmation, not coding.
  shuffled   a fixed seed permutes the items so dataset blocks do not cue the
             coder -- eleven MI columns in a row would teach the pattern.
  complete   all 68 positives, declared in advance.  Coding "until it looks
             good" is choosing a sample by its result.
  isolated   the coder gets THIS FILE ONLY.  Appendix B lists every positive
             with its subtype; it is the answer key.  So is PAPER.md.

  The packet also asks the BINARY question -- does the quote license calling
  this column inadmissible at all.  It costs the coder nothing extra and it
  answers the larger worry: the §4.7 audit moved eight labels once, so a reader
  wants to know whether they would move again.  The expected result is that the
  binary reproduces near-perfectly (it is quotation-licensed) while the subtype
  is softer.  That asymmetry, if it holds, is the useful finding: it localises
  the uncertainty to §6.2 and clears §6.1.

THE SIX RECORDS WITH NO QUOTATION

  TITANIC `boat`/`body` and COMPAS's four `r_*` columns are tier E3: their
  documentation was not retrievable, and they rest on the column's documented
  name plus an exact check in the data.  They are included, marked, and given
  their data check instead of a quote, so the scorer can report agreement with
  and without them.  Dropping them silently would flatter the result.
"""
import os, sys, json, random
import verify_paper as V
import runner as RN

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
SEED = 20260816
OUT = HERE + "CODING_PACKET.md"
KEY = HERE + "coding_key.json"

CODEBOOK = """\
## Codebook — read this once, then do not look back at it mid-item

You are judging **one column against one target, at one moment in time**.
That moment is the *prediction point*: the instant the model is asked to
produce its answer. A value that does not honestly exist yet at that moment,
or that exists only because the outcome already happened, is inadmissible.

Assign **exactly one** category to every item.

The single distinction that separates the first two: **REASON is about how the
LABEL was made. CONSEQUENCE is about how the COLUMN was made.** Both correlate
with the outcome — every leaking column does — so correlation tells you nothing.
Ask which way the arrow points.

| code | the column… | worked example |
|---|---|---|
| **REASON** | was an *input used to assign the label*. The target was computed, decided or derived FROM this column — the label is the downstream thing. | four failure flags that are OR-ed together to produce `Machine failure`: flip one and the label flips, by definition |
| **CONSEQUENCE** | *exists because the outcome occurred* — the column is the downstream thing. It would be blank, absent or meaningless had the outcome gone the other way. | `body` — a body-recovery number, which exists only for passengers who did not survive. Nobody used it to decide who survived; the drowning caused both |
| **TIMING** | is *recorded after the prediction point*, but is neither an input to the label nor a product of the outcome. It is an ordinary measurement taken too late. | 1995 crime counts, in a model predicting a 1995 rate from a 1990 census |
| **CONTESTED** | you can see a real case for inadmissibility **and** a real case against, and the quotation does not settle it. | use this sparingly — it is an admission that the evidence is genuinely two-sided, not a way to avoid choosing |

**The categories overlap, so check them in this order and stop at the first
yes.** Some columns are genuinely both a trace of the outcome and an input to
the label; the order below decides those deterministically rather than leaving
them to taste.

1. Does the quotation say the target was **computed, derived or decided from**
   this column?  →  **REASON**
2. Else — would this column be **blank, absent or meaningless** if the outcome
   had gone the other way?  →  **CONSEQUENCE**
3. Else — is it simply **recorded after** the prediction point?  →  **TIMING**
4. Else, and only else  →  **CONTESTED**

**Code the evidence, not the intuition.** Judge from the quotation shown, not
from what you suspect about the domain. If the sentence only tells you *when* a
value was recorded, that is TIMING even if you think something deeper is going
on.

**The second question.** For each item also answer: does the quotation license
calling this column inadmissible **at all**? `Y` or `N`. Answer `N` freely — a
disagreement here is more informative than a polite `Y`, and nothing bad
happens to anyone if you say no.

**Rules.**

1. Work **alone**. Do not discuss items with anyone else who is coding.
2. Do **not** read the paper or its appendices. They contain the answers.
3. Do not skip items. If you are unsure, choose anyway and write `?` after
   your answer — the scorer counts flagged items separately.
4. Do not go back and change earlier answers after you spot a pattern.

---

## How to answer

Write one line per item, in this exact form, into a plain text file:

```
12  REASON  Y
13  TIMING  N
14  CONSEQUENCE  Y ?
```

Item number, then the category, then `Y`/`N`, then an optional `?`.
Separators can be spaces or tabs. Case does not matter. Save it as
`coding_<yourname>.txt` and hand it back.
"""


def collect():
    """The 68 positives, shuffled once on a fixed seed.

    Shared by the markdown and HTML renderers so item 34 is the same column in
    both.  If they drew their own orderings, two coders using different formats
    would be answering different questions under the same numbers, and the
    scorer -- which joins on the number -- would silently compare unrelated
    items.
    """
    recs = V.load_records()
    items = []
    for keys, lab in ((RN.ALLSETS, "A"), (RN.EXPLICIT, "B")):
        for k in keys:
            b = RN.spec_bundle(k)
            for c in b["columns"]:
                if not b["truth"].get(c):
                    continue
                r = recs.get((b["name"], c), {})
                items.append(dict(
                    dataset=b["name"], stratum=lab, column=c,
                    target=b["target"], pp=b["prediction_point"],
                    quote=(r.get("quote") or "").strip(),
                    check=(r.get("data_check") or "").strip(),
                    tier=r.get("evidence_tier", "?"),
                    subtype=r.get("subtype") or V.subtype(b["name"], c)))
    assert len(items) == 68, f"expected 68 positives, built {len(items)}"

    rng = random.Random(SEED)
    rng.shuffle(items)
    return items


def build():
    items = collect()
    out = [f"# Subtype coding packet — {len(items)} items",
           "",
           "*Generated by `coding_packet.py`, seed 20260816. Every item is a "
           "column from a public dataset that this project has coded as a "
           "target leak. Your job is to say **why** it leaks, and whether the "
           "evidence shown supports calling it a leak at all.*",
           "",
           "*Budget roughly 40 minutes. There are no trick items and no "
           "expertise is required — everything you need is on the card.*",
           "", CODEBOOK, "", "---", ""]

    for i, it in enumerate(items, 1):
        out.append(f"### {i}.  `{it['column']}`")
        out.append("")
        out.append(f"**dataset** {it['dataset']} &nbsp;·&nbsp; "
                   f"**target** `{it['target']}`")
        out.append("")
        out.append(f"**prediction point** — {it['pp']}")
        out.append("")
        if it["quote"]:
            out.append("**the source says:**")
            out.append("")
            out.append("> " + it["quote"].replace("#", "\\#"))
        else:
            out.append("**no quotation was obtainable for this column.** It is "
                       "coded from the column's documented name plus a check "
                       "in the data:")
            out.append("")
            out.append("> *(no source sentence)* — " +
                       (it["check"] or "no data check recorded"))
        out.append("")
        if it["quote"] and it["check"]:
            out.append(f"*check in the data:* {it['check']}")
            out.append("")
        out.append("**your answer** — REASON / CONSEQUENCE / TIMING / "
                   "CONTESTED, and licensed at all? Y / N")
        out.append("")
        out.append("---")
        out.append("")

    open(OUT, "w").write("\n".join(out))
    # `tier` and `has_quote` are NOT the same cut and the scorer needs both:
    # E3 is 28 of the 68 positives, while only 6 lack a quotation entirely.
    # Conflating them made the scorer label a 28-item exclusion as a 6-item one.
    json.dump([{**{k: it[k] for k in ("dataset", "column", "subtype", "tier")},
                "has_quote": bool(it["quote"])} for it in items],
              open(KEY, "w"), indent=1)
    print(f"wrote {OUT}  ({len(items)} items)")
    print(f"wrote {KEY}   <- the answer key.  Do NOT send this to a coder.")
    nq = sum(1 for it in items if not it["quote"])
    print(f"  {len(items)-nq} items carry a source quotation; {nq} are tier E3 "
          f"with a data check instead")


if __name__ == "__main__":
    build()
