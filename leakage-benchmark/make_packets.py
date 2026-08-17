"""Build the foreground work packets for the two `ui`-provider models.

WHY THESE EXIST

  claude-opus-5 and gpt-5.6-sol were run through an agent loop, not an HTTP
  endpoint, so there is no key a background process can use and they have NO
  PARAPHRASE ARM.  That is the largest hole in the memorisation control: §6.3(d)
  reports a renaming experiment over six models, and the two the headline rests
  on are not among them.

  A packet is a self-contained brief: the exact prompts, in the exact order,
  with the output format and the destination file.  It is written so the run can
  be done by hand in a fresh session with no access to this directory.

MATCHING IS THE WHOLE POINT

  The paraphrase control is a DIFFERENCE — score on real column names minus
  score on aliases, on the SAME cells.  So the grid here is not "some datasets
  at some conditions"; it is read off each model's existing normal cells and
  mirrored exactly: same datasets, same conditions, same seeds, same shuffle.
  An unmatched arm is how the paraphrase number came out 0.000 the first time,
  and how a join failure inflated nemotron's decrement later.

  Conditions are C1 and C6 only.  Those are the two the paper's claims rest on
  and the two the cross-model decrement table reports; adding C2/C9 would double
  a hand-run pass for numbers no table uses.
"""
import glob, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE)
import runner as RN
import prompts
import paraphrase as PP

OUTDIR = "/root/Desktop/packets/"
CONDS = [1, 6]

MODELS = {
    "claude-opus-5-max": dict(
        packet="opus5_paraphrase_packet.md",
        verdicts="opus5_paraphrase_verdicts.md",
        label="Claude Opus 5"),
    "gpt-5.6-sol-xhigh": dict(
        packet="gpt56_paraphrase_packet.md",
        verdicts="gpt56_paraphrase_verdicts.md",
        label="GPT-5.6-sol"),
}


def existing_grid(model):
    """(dataset, cond, seed) triples this model already has on REAL names."""
    out = set()
    for f in glob.glob(HERE + "responses/*.json"):
        d = json.load(open(f))
        if d.get("model") == model and not d.get("paraphrase"):
            if d.get("condition") in CONDS:
                out.add((d["dataset"], d["condition"], d.get("seed")))
    return sorted(out)


def build():
    if PP.check() != 0:
        sys.exit("paraphrase map failed its own checks; refusing to emit packets")
    os.makedirs(OUTDIR, exist_ok=True)

    written = []
    for model, meta in MODELS.items():
        grid = existing_grid(model)
        dsets = sorted({d for d, _, _ in grid})
        # The cache stores the DISPLAY name ("AI4I"); spec_bundle wants the
        # loader key ("ai4i").  Build the map from the specs themselves rather
        # than assuming lowercase, so a spec whose display name is not just the
        # key upper-cased cannot silently go missing.
        name2key = {}
        for k in RN.ALLSETS + RN.EXPLICIT:
            try:
                name2key[RN.spec_bundle(k)["name"]] = k
            except Exception:
                continue
        missing = [d for d in dsets if d not in name2key]
        if missing:
            sys.exit(f"no loader key for {missing} — refusing to emit a packet "
                     f"that silently drops cells")

        # Some datasets have no entry in paraphrase.json and so cannot appear
        # in a paraphrase arm.  As of writing that is MI alone -- and NOT for
        # any reason the map documents: CRIME is wider (144 columns vs 122) and
        # IS mapped, so it is not a size limit, and both are Stratum B, so it is
        # not a stratum rule.  It looks like an omission rather than a decision.
        # Drop it LOUDLY and say exactly that in the packet; inventing a
        # principled-sounding reason for a gap is how a gap stops getting fixed.
        bundles, unmapped = {}, []
        for d in dsets:
            try:
                bundles[d] = PP.apply_to(RN.spec_bundle(name2key[d]))
            except KeyError:
                unmapped.append(d)
        if unmapped:
            print(f"  {model}: no alias map for {', '.join(unmapped)} "
                  f"(Stratum B) — excluded from the packet")
        grid = [g for g in grid if g[0] in bundles]
        dsets = sorted(bundles)

        unmapped_note = (", ".join(unmapped) if unmapped else "")
        blocks = []
        for i, (dname, cond, seed) in enumerate(grid, 1):
            b = bundles[dname]
            cols = b["columns"][:]
            # SAME shuffle as the normal arm: seeded identically, so alias k
            # sits where the real name sat.  Anything else compares different
            # orderings as well as different strings.
            random.Random(seed).shuffle(cols)
            if cond == 6:
                user = prompts.build_derivation(b["name"], cols, b["target"])
            else:
                user = prompts.build(b["name"], cols, cond, b["target"],
                                     b["prediction_point"], b["description"],
                                     b["sample"])
            blocks.append((i, b["name"], cond, seed, len(cols), user))

        p = OUTDIR + meta["packet"]
        with open(p, "w") as fh:
            fh.write(header(meta, model, grid, dsets, blocks, unmapped_note))
            for i, name, cond, seed, ncol, user in blocks:
                fh.write(f"\n\n---\n\n### Prompt {i} of {len(blocks)} — "
                         f"`{name}` · condition C{cond} · seed {seed} · "
                         f"{ncol} columns\n\n"
                         f"````text\n{user}\n````\n")
            fh.write(footer(meta))
        written.append((p, len(blocks), os.path.getsize(p)))

    for p, n, sz in written:
        print(f"  {p}   {n} prompts   {sz/1024:.0f} KB")


def header(meta, model, grid, dsets, blocks, unmapped_note=""):
    conds = sorted({c for _, c, _ in grid})
    seeds = sorted({s for _, _, s in grid})
    return f"""# Paraphrase-arm packet — {meta['label']}

**Run this whole packet in one sitting, in a fresh session, and write the
answers to `{meta['verdicts']}`.**

## What this is for

This is the memorisation control for a paper on whether language models can
detect feature-level target leakage from a column list. Every column name below
has been replaced with a **string-distinct alias**, and the dataset name is
renamed too, so nothing in the prompt identifies the underlying table.

The question the control answers: *does the model still identify the leaking
columns when it cannot recognise them by name?* Your answers will be scored
against the same model's answers on the real names, cell for cell.

**Do not try to work out which real dataset each one is.** If you recognise it,
that is exactly the confound being measured — answer from the structure and the
stated prediction point, not from recognition. Do not look anything up.

## Grid

| | |
|---|---|
| model | `{model}` |
| datasets | {len(dsets)} |
| conditions | {', '.join('C'+str(c) for c in conds)} |
| seeds | {', '.join(str(s) for s in seeds)} |
| prompts in this packet | **{len(blocks)}** |

{('**Excluded, and the honest reason:** `' + unmapped_note + '` has no entry '
   'in the alias map, so it cannot be paraphrased. No documented rule explains '
   'the gap — CRIME is wider (144 columns) and is mapped, and both sit in the '
   'same stratum — so this looks like an omission rather than a decision, and '
   'is recorded as one. It is named here so the coverage is not inferred from a '
   'count.' + chr(10) + chr(10))
  if unmapped_note else ''}The grid mirrors this model's existing real-name cells exactly — same datasets,
same conditions, same seeds, same column ordering. That matching is what makes
the comparison a difference rather than two unrelated scores.

## How to answer

For **each** prompt below, in order:

1. Answer the prompt exactly as written. It asks for JSON; return JSON.
2. Judge **every** column listed. A column you omit is scored as "not flagged",
   which is indistinguishable from you deciding it is legitimate.
3. If you genuinely cannot decide, use the prompt's own abstention verdict
   rather than guessing — abstentions are counted separately and are not
   penalised as misses.
4. Do not carry context between prompts. Treat each as independent; if the same
   alias appears in two prompts, that is not a signal.

## Where to write the answers

Create **`{meta['verdicts']}`** in this same folder, with one section per
prompt:

````markdown
## Prompt 1 — <DATASET_ALIAS> C<cond> seed <seed>
```json
{{ "columns": [ {{ "name": "...", "verdict": "...", "reason": "..." }} ] }}
```
````

Keep the prompt number, alias, condition and seed on every section heading —
they are the join key. A section without them cannot be matched back and the
cell is lost.
"""


def footer(meta):
    return f"""

---

## When you are done

`{meta['verdicts']}` should contain exactly as many sections as there are
prompts above, each with its number, alias, condition and seed in the heading.

Two failure modes worth checking before you finish, because both have happened
in this project and neither is visible afterwards:

* **A truncated JSON object** parses into a partial column list, and every
  missing column silently scores as "not flagged". If an answer was cut off,
  redo that prompt rather than leaving it short.
* **A section whose heading lost its seed or condition** cannot be joined to the
  matching real-name cell, so the pair is dropped from the comparison.

Do not summarise, rank, or comment on the results. The scoring is done
elsewhere, and an interpretation written here would be read as data.
"""


if __name__ == "__main__":
    build()
