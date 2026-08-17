"""Figures for the paper. Only figures whose inputs are FINAL.

WHY ONLY SOME

  Most of the paper's numbers are still moving: eleven repaired cells are
  outstanding behind a provider quota, so every per-model table could change by
  a decimal.  A figure drawn from those would have to be redrawn, and a stale
  PNG is worse than no PNG because nothing checks it against the artefacts the
  way consistency.py checks the prose.

  The Stratum C funnel does not depend on any of that.  The sweeps are complete
  and their numbers are closed, so it can be drawn once and left alone.

FIGURE 1 — the funnel collapses in every population

  This is §6.4's argument in one picture: the sieve FIRES at a comparable rate
  in four documentation cultures, and then loses almost everything at the same
  two steps, for the same two reasons.  Anchoring is the dominant loss -- the
  one pattern that transferred cleanly across populations -- and reading the
  sentence
  removes nearly all of what survives.

  Drawn on a log axis because the funnel spans four orders of magnitude, and
  a linear axis would render every interesting stage as a flat line at zero.
  Zero cannot be plotted on a log axis, so admissible-zero is drawn as an open
  marker at the floor and labelled: an absent bar and a zero bar must not look
  the same, and the zero IS the finding.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"

# Every number below is closed.  Sources, in order: kaggle_sieve.out /
# kaggle_anchor.log (Kaggle), hf_harvest + hf_anchor.log (HF), openml_harvest
# (OpenML), kaggle_comp.py (competitions).  UCI is the Stratum A population and
# is shown for reference -- it is where the sieve was written.
STAGES = ["swept", "sentence\nsurvives", "schema\nreadable",
          "anchored to\na column", "admissible"]
POPS = [
    ("Kaggle datasets",     [8693, 258, 117, 30, 0],  "#2c6fbb"),
    ("Hugging Face cards",  [14420, 233, 195, 34, 2], "#d9822b"),
    ("OpenML (re-sweep)",   [6418, 101, 101, 30, 0],  "#3f9c53"),
    ("Kaggle competitions", [605, 0, 0, 0, 0],        "#8d6cab"),
]
UCI = ("UCI (Stratum A source)", [689, 13, 13, 13, 12], "#888888")


def funnel():
    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    x = range(len(STAGES))
    series = POPS + [UCI]
    for n, (label, vals, colour) in enumerate(series):
        style = dict(marker="o", lw=2.0, ms=6, color=colour, label=label)
        if label.startswith("UCI"):
            style.update(ls="--", lw=1.6, ms=5, zorder=1)
        # a log axis cannot show 0; plot the positive prefix as a line and mark
        # each zero explicitly at the floor so it reads as MEASURED-zero
        pos = [(i, v) for i, v in zip(x, vals) if v > 0]
        ax.plot([i for i, _ in pos], [v for _, v in pos], **style)
        # Offset the zero markers per series.  Kaggle, OpenML and competitions
        # all end at zero admissible, and drawn at the same point they landed
        # exactly on top of each other -- the figure showed ONE open marker and
        # read as "one population reached zero" when three did.  The overlap is
        # the finding, so it has to be visible.
        dx = (n - (len(series) - 1) / 2) * 0.085
        for i, v in zip(x, vals):
            if v == 0:
                ax.plot(i + dx, 0.55, marker="o", ms=7, mfc="white",
                        mec=colour, mew=1.8, zorder=3)

    ax.set_yscale("log")
    ax.set_ylim(0.4, 40000)
    ax.set_xticks(list(x))
    ax.set_xticklabels(STAGES)
    ax.set_ylabel("datasets (log scale)")
    ax.set_title("The sieve fires at a comparable rate everywhere, then "
                 "collapses at the same two steps", fontsize=11.5, pad=12)
    ax.grid(axis="y", alpha=0.25, ls=":")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    ax.annotate("open marker = measured zero,\nnot missing data",
                xy=(4, 0.55), xytext=(3.02, 2.6), fontsize=8.5,
                color="#444444",
                arrowprops=dict(arrowstyle="->", color="#888888", lw=1))
    ax.annotate("anchoring is the dominant loss\n(17–30% in every population)",
                xy=(2.5, 120), xytext=(1.15, 900), fontsize=8.5, color="#444444",
                arrowprops=dict(arrowstyle="->", color="#888888", lw=1))

    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{HERE}fig_stratc_funnel.{ext}", dpi=200)
    plt.close(fig)
    print("wrote fig_stratc_funnel.png / .pdf")




# =========================================================== FIGURE 2
# The C1 -> C6 forest plot.
#
# WHY THIS ONE IS DRAWN DESPITE THE POLICY ABOVE
#
#   Figure 1's rule is "only figures whose inputs are final", and these inputs
#   are not: eleven gemini-3.5-flash cells are outstanding behind a provider
#   quota and six cells remain truncated by our own token budget.  The figure
#   is drawn anyway because it carries the paper's most easily MISREAD claim --
#   that C6 lifts detection -- and a table of ten intervals does not make the
#   pattern visible the way a plot does: every interval excluding zero belongs
#   to a model that was failing at C1.  A reader who sees that once does not
#   have to be argued into it.
#
#   The provisional models are marked on the figure itself rather than in a
#   caption a reader may not reach.  Redraw after the quota clears.
FOREST = [
    # model, F1 C1, dF1, CI low, CI high, provisional
    ("claude-opus-5",      0.905, +0.004, -0.018, +0.050, False),
    ("gpt-5.6-sol",        0.864, +0.053, +0.000, +0.206, False),
    ("Kimi-K3",            0.876, +0.000, +0.000, +0.000, False),
    ("GLM-5.2",            0.815, +0.056, +0.000, +0.206, False),
    ("gemini-3.5-flash",   0.833, +0.035, -0.027, +0.181, True),
    ("gemini-3.7-flash",   0.834, +0.067, -0.004, +0.234, False),
    ("nemotron-3-super",   0.652, +0.132, +0.006, +0.318, False),
    ("deepseek-v4-flash",  0.559, +0.142, +0.019, +0.362, False),
    ("Qwen3-Coder-480B",   0.595, +0.168, +0.036, +0.344, False),
    ("DeepSeek-V4-Pro",    0.703, -0.121, -0.346, +0.169, False),
]


def fig_forest():
    rows = sorted(FOREST, key=lambda r: r[1])          # weakest at C1 first
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for i, (name, f1c1, d, lo, hi, prov) in enumerate(rows):
        excl = lo > 0 or hi < 0
        col = "#1a1a1a" if excl else "#9aa0a6"
        ax.plot([lo, hi], [i, i], color=col, lw=2.0, solid_capstyle="butt",
                zorder=2)
        ax.plot([d], [i], "o", ms=6, color=col, zorder=3)
        ax.text(hi + 0.012, i, f"C1 {f1c1:.3f}" + ("  \u26a0" if prov else ""),
                va="center", fontsize=7.6, color="#3c4043")
    ax.axvline(0, color="#c0392b", lw=1.0, ls="--", zorder=1)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.4)
    ax.set_xlabel("\u0394F1 from adding the derivation criterion (C1 \u2192 C6)\n"
                  "95% CI, 2,000 bootstrap draws resampling the 12 datasets",
                  fontsize=8.6)
    ax.set_title("The derivation criterion repairs weak detectors and does not "
                 "move strong ones", fontsize=9.6, pad=10)
    ax.tick_params(labelsize=8)
    ax.set_xlim(-0.42, 0.50)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    # The note sat at the top of the axes and collided with the title.  Put it
    # under the plot, where it reads as a key rather than as a second heading.
    ax.set_ylim(-1.15, len(rows) - 0.4)
    ax.text(-0.41, -0.95,
            "solid = interval excludes zero      \u26a0 = cache incomplete "
            "(11 cells behind provider quota)",
            fontsize=7.2, color="#5f6368")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{HERE}fig_c6_forest.{ext}", dpi=200)
    print("wrote fig_c6_forest.png / .pdf")


if __name__ == "__main__":
    funnel()
    fig_forest()
