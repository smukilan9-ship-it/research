Second round of verification for a TMLR submission. Five open items, in
priority order. Please use web search, and **read the sources rather than
working from search snippets** where I say so.

Same rules as before: do NOT guess, mark anything you cannot confirm as
UNVERIFIED and say what you searched, and give me the URL you verified against.
An invented answer here is worse than an open question.

---

## 1. HIGHEST VALUE — a possible convergent taxonomy. Please actually read it.

**"A taxonomy for detecting and preventing temporal data leakage in machine
learning-based build prediction: A dual-platform empirical validation."**
PLOS One, DOI 10.1371/journal.pone.0340167.

I have this from a single search snippet and have not read it. Reportedly its
three types are **Direct Outcome Encoding**, **Execution-Dependent Metrics**,
and **Future Information Leakage**.

My paper defines three mechanisms of feature-level target leakage, as
sub-categories of "a feature that is not legitimate at the prediction point":

- **REASON** — the column was an *input used to assign the label*. The target
  was computed, decided or derived FROM this column. Example: four failure
  flags OR-ed together to produce a `Machine failure` target.
- **CONSEQUENCE** — the column *exists because the outcome occurred*. It would
  be blank, absent or meaningless had the outcome gone the other way. Example:
  a body-recovery number, which exists only for passengers who did not survive.
- **TIMING** — the column is *recorded after the prediction point*, but is
  neither an input to the label nor a product of the outcome. An ordinary
  measurement taken too late.

**What I need:**
a) Their three types, quoted verbatim with their own definitions and examples.
b) Your honest assessment of whether the mapping to mine is **real or
   superficial**. Specifically: is "Direct Outcome Encoding" about a column the
   label was *derived from* (= REASON), or about a column that *encodes* the
   outcome after the fact (= CONSEQUENCE)? The distinction matters a lot to me
   and the name is ambiguous.
c) Is their taxonomy derived empirically from observed cases, or proposed a
   priori? Over how many projects/builds?
d) Do they cite Kapoor & Narayanan (2023) or Larsen & Becker (2021)?
e) Is it peer-reviewed and published, or a preprint? Date?

**Tell me plainly if the mapping does NOT hold.** A forced convergence claim
would be worse for me than no claim — I would rather cite them as related work
than overclaim agreement.

## 2. A label I QUOTE and could not verify

Kapoor, S. & Narayanan, A. (2023), *Patterns* 4(9), 100804,
DOI 10.1016/j.patter.2023.100804.

My §3.2 quotes their type **L2** as **"model uses features that are not
legitimate"** and states that L2 is the only one of their eight types they do
NOT decompose into sub-types, on the grounds that judging feature legitimacy
requires domain knowledge.

**What I need:** the **exact wording of the L2 label** from Figure 1 (or
wherever the taxonomy is enumerated) in the *published* version, and
confirmation or refutation that (a) L2 has no sub-types while others do, and
(b) they give that reason for it. Quote their sentence if so.

## 3–4. Two entries a previous pass did not check

- **Quinlan, J. R. (1993). *C4.5: Programs for Machine Learning.* Morgan
  Kaufmann. ISBN 1-55860-238-0.** Confirm publisher, year, ISBN.
- **Sculley, D., Holt, G., Golovin, D., Davydov, E., Phillips, T., Ebner, D.,
  Chaudhary, V., Young, M., Crespo, J.-F. & Dennison, D. (2015). "Hidden
  Technical Debt in Machine Learning Systems." NeurIPS 2015.** Confirm the
  ten-author order, the venue name for that year, and the page range.

## 5. A coinage I was told NOT to assert

Does the term **"anachronistic variable"**, for a feature whose value could not
have been known at prediction time, originate with **Pyle, D. (1999), *Data
Preparation for Data Mining*, Morgan Kaufmann**? A previous pass flagged this
as unverified recollection with no retrieved source.

**If you cannot confirm it from the book or a source that cites the book for
that term specifically, say UNVERIFIED.** I will simply not use the term. Do
not reason from plausibility.
