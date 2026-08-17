"""Render the blind coding packet as a click-through HTML instrument.

WHY AN HTML VERSION AND NOT JUST THE MARKDOWN

  Sixty-eight items typed by hand into a text file is where transcription
  errors come from, and a transcription error in a reliability study is
  indistinguishable from a genuine disagreement -- it lands in kappa either
  way.  Clicking cannot produce a malformed line, cannot skip an item number,
  and cannot mistype a category.  The page emits the exact format
  coding_score.py parses, so the coder never sees the format at all.

TWO DESIGN DECISIONS THAT ARE METHODOLOGICAL, NOT COSMETIC

  1. The four category buttons are IDENTICAL until chosen.  Giving each
     category its own colour would draw the eye to one of them, and a coding
     instrument that makes one answer more visually available is biased in
     exactly the way an instrument must not be.

  2. Neither answer is pre-filled.  Defaulting the licence question to "yes"
     would have made each item one click instead of two -- and would have
     biased the binary check toward agreement, which is the one question whose
     value depends on the coder being free to say no.  Two clicks, no default.

  State is written to localStorage on every change, because forty minutes of
  work lost to a refresh is forty minutes nobody codes a second time.

  The page contains NO subtype.  It is generated from the same item list as
  the markdown packet, with the answer key withheld; grep the output for
  REASON outside the codebook and the buttons if you want to confirm it.
"""
import os, sys, json, html, random
import verify_paper as V
import runner as RN
import coding_packet as CP

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "coding_packet.html"

CSS = """
:root{
  --paper:#F7F8FA; --card:#FFFFFF; --ink:#161C24; --ink-soft:#4A5763;
  --ink-faint:#7C8894; --rule:#DDE3EA; --rule-soft:#EDF1F5;
  --accent:#0E6E6E; --accent-ink:#FFFFFF; --accent-wash:#E3F1F0;
  --quote-ground:#F2F5F8; --warn:#8A5A00;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#10151A; --card:#171E25; --ink:#E6ECF2; --ink-soft:#A9B6C2;
    --ink-faint:#7A8794; --rule:#2A343E; --rule-soft:#212A33;
    --accent:#4FBFB4; --accent-ink:#0B1013; --accent-wash:#1B2E30;
    --quote-ground:#121A20; --warn:#D8A544;
  }
}
:root[data-theme="dark"]{
  --paper:#10151A; --card:#171E25; --ink:#E6ECF2; --ink-soft:#A9B6C2;
  --ink-faint:#7A8794; --rule:#2A343E; --rule-soft:#212A33;
  --accent:#4FBFB4; --accent-ink:#0B1013; --accent-wash:#1B2E30;
  --quote-ground:#121A20; --warn:#D8A544;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:ui-sans-serif,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  font-size:16px; line-height:1.55; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:52rem; margin:0 auto; padding:0 1.25rem 6rem}
code,.mono{font-family:ui-monospace,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace}

/* ---------- sticky progress ---------- */
header.bar{
  position:sticky; top:0; z-index:20; background:var(--paper);
  border-bottom:1px solid var(--rule);
}
.bar-in{max-width:52rem;margin:0 auto;padding:.7rem 1.25rem;
  display:flex;align-items:center;gap:1rem;flex-wrap:wrap}
.bar h1{font-size:.95rem;font-weight:650;margin:0;letter-spacing:-.01em}
.count{font-variant-numeric:tabular-nums;color:var(--ink-soft);font-size:.9rem;
  margin-left:auto}
.track{flex:0 0 100%;height:3px;background:var(--rule-soft);border-radius:2px;
  overflow:hidden}
.fill{height:100%;width:0;background:var(--accent);transition:width .25s ease}
.saved{font-size:.78rem;color:var(--ink-faint)}

/* ---------- intro ---------- */
.intro{padding:2.5rem 0 1rem}
.intro h2{font-size:1.6rem;line-height:1.2;margin:0 0 .6rem;
  letter-spacing:-.02em;text-wrap:balance}
.lede{color:var(--ink-soft);max-width:38rem}
details.book{margin:1.5rem 0;border:1px solid var(--rule);border-radius:8px;
  background:var(--card)}
details.book>summary{cursor:pointer;padding:.85rem 1.1rem;font-weight:600;
  font-size:.95rem;list-style:none;display:flex;align-items:center;gap:.5rem}
details.book>summary::-webkit-details-marker{display:none}
details.book>summary::before{content:"▸";color:var(--accent);font-size:.8rem}
details.book[open]>summary::before{content:"▾"}
.book-body{padding:0 1.1rem 1.1rem;border-top:1px solid var(--rule-soft)}
.book-body h3{font-size:.82rem;text-transform:uppercase;letter-spacing:.07em;
  color:var(--ink-faint);margin:1.4rem 0 .5rem;font-weight:650}
.defs{display:grid;gap:.7rem;margin:.4rem 0}
.def{display:grid;grid-template-columns:8.5rem 1fr;gap:1rem;
  padding:.65rem .8rem;border:1px solid var(--rule-soft);border-radius:6px}
.def b{font-size:.8rem;letter-spacing:.05em}
.def p{margin:0;font-size:.92rem;color:var(--ink-soft)}
.def em{color:var(--ink);font-style:normal;font-weight:600}
ol.order{margin:.4rem 0 0;padding-left:1.2rem;font-size:.94rem;color:var(--ink-soft)}
ol.order li{margin:.3rem 0}
ol.order b{color:var(--ink)}
.rules{font-size:.92rem;color:var(--ink-soft);padding-left:1.2rem;margin:.4rem 0 0}

/* ---------- cards ---------- */
.card{background:var(--card);border:1px solid var(--rule);border-radius:10px;
  padding:1.15rem 1.25rem 1rem;margin:1rem 0;scroll-margin-top:5.5rem}
.card.done{border-color:var(--accent-wash)}
.card.is-cur{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-wash)}
.card.is-cur .num::after{content:" \2190 current";color:var(--accent);
  font-weight:650;letter-spacing:.02em}
.card-head{display:flex;align-items:baseline;gap:.7rem;flex-wrap:wrap;
  margin-bottom:.5rem}
.num{font-variant-numeric:tabular-nums;color:var(--ink-faint);font-size:.82rem;
  font-weight:600}
.col{font-size:1.06rem;font-weight:650;letter-spacing:-.01em;word-break:break-word}
.meta{font-size:.85rem;color:var(--ink-soft);margin:0 0 .1rem}
.meta b{color:var(--ink);font-weight:600}
.pp{font-size:.85rem;color:var(--ink-soft);margin:.15rem 0 .9rem}
blockquote{
  margin:0 0 1rem; padding:.85rem 1rem; background:var(--quote-ground);
  border-left:2px solid var(--accent); border-radius:0 6px 6px 0;
  font-family:Charter,"Bitstream Charter","Iowan Old Style",Georgia,serif;
  font-size:1.02rem; line-height:1.5; max-width:62ch;
}
blockquote.noquote{font-family:inherit;font-size:.9rem;color:var(--ink-soft);
  border-left-color:var(--warn)}
.tag{display:inline-block;font-size:.7rem;letter-spacing:.06em;font-weight:700;
  text-transform:uppercase;color:var(--warn);border:1px solid currentColor;
  border-radius:3px;padding:.05rem .35rem;vertical-align:.1em}
.check{font-size:.84rem;color:var(--ink-faint);margin:-.5rem 0 1rem;
  max-width:62ch}
.ask{font-size:.74rem;text-transform:uppercase;letter-spacing:.07em;
  color:var(--ink-faint);font-weight:650;margin:0 0 .4rem}
.opts{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.85rem}
button.opt{
  font:inherit;font-size:.88rem;font-weight:550;cursor:pointer;
  padding:.45rem .8rem;border-radius:6px;border:1px solid var(--rule);
  background:transparent;color:var(--ink);transition:background .12s,border-color .12s;
}
button.opt:hover{border-color:var(--accent);background:var(--accent-wash)}
button.opt[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);
  color:var(--accent-ink)}
button.opt:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.opts.small button.opt{padding:.35rem .75rem;font-size:.85rem}
button.unsure[aria-pressed="true"]{background:transparent;color:var(--warn);
  border-color:var(--warn)}

/* ---------- output ---------- */
.out{margin:3rem 0 0;border:1px solid var(--rule);border-radius:10px;
  background:var(--card);padding:1.25rem}
.out h3{margin:0 0 .3rem;font-size:1.05rem}
.out p{margin:0 0 .9rem;color:var(--ink-soft);font-size:.92rem}
textarea{width:100%;min-height:11rem;resize:vertical;padding:.8rem;
  border:1px solid var(--rule);border-radius:6px;background:var(--quote-ground);
  color:var(--ink);font-family:ui-monospace,Menlo,Consolas,monospace;
  font-size:.84rem;line-height:1.5}
.row{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;margin-top:.7rem}
button.act{font:inherit;font-size:.9rem;font-weight:600;cursor:pointer;
  padding:.5rem 1rem;border-radius:6px;border:1px solid var(--accent);
  background:var(--accent);color:var(--accent-ink)}
button.act.ghost{background:transparent;color:var(--ink);border-color:var(--rule)}
button.act:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.note{font-size:.85rem;color:var(--warn)}
kbd{font-family:ui-monospace,Menlo,monospace;font-size:.78rem;
  border:1px solid var(--rule);border-bottom-width:2px;border-radius:4px;
  padding:.05rem .3rem;color:var(--ink-soft)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
@media (max-width:520px){.def{grid-template-columns:1fr;gap:.2rem}}
"""

CATS = ["REASON", "CONSEQUENCE", "TIMING", "CONTESTED"]

DEFS = [
    ("REASON", "The target was <em>computed, derived or decided from</em> this "
     "column. The label is the downstream thing — change the column and the "
     "label changes, by definition."),
    ("CONSEQUENCE", "The column <em>exists because the outcome occurred</em>. "
     "The column is the downstream thing — it would be blank, absent or "
     "meaningless had the outcome gone the other way."),
    ("TIMING", "Neither of the above, but the value is <em>recorded after</em> "
     "the moment of prediction. An ordinary measurement, taken too late."),
    ("CONTESTED", "The quotation genuinely supports both a case for and a case "
     "against, and does not settle it. Rare — use it sparingly."),
]


def build():
    items = CP.collect()
    rows = []
    for i, it in enumerate(items, 1):
        q = html.escape(it["quote"])
        chk = html.escape(it["check"])
        if it["quote"]:
            quote = f'<blockquote>{q}</blockquote>'
            extra = (f'<p class="check">Checked in the data: {chk}</p>'
                     if chk else "")
        else:
            quote = ('<blockquote class="noquote"><span class="tag">no source '
                     'sentence</span><br>This column has no retrievable '
                     'documentation. It rests on its documented name plus a '
                     'check in the data: ' + (chk or "none recorded") +
                     '</blockquote>')
            extra = ""
        opts = "".join(
            f'<button class="opt" type="button" data-i="{i}" data-cat="{c}" '
            f'aria-pressed="false">{c[0]}{c[1:].lower()}</button>' for c in CATS)
        rows.append(f"""
<section class="card" id="i{i}" data-i="{i}">
  <div class="card-head"><span class="num">{i} / {len(items)}</span>
    <span class="col mono">{html.escape(it['column'])}</span></div>
  <p class="meta"><b>{html.escape(it['dataset'])}</b> &middot; predicting
     <code>{html.escape(it['target'])}</code></p>
  <p class="pp">Prediction point — {html.escape(it['pp'])}</p>
  {quote}{extra}
  <p class="ask">Why is this column inadmissible?</p>
  <div class="opts">{opts}</div>
  <p class="ask">Does the evidence above support calling it inadmissible at all?</p>
  <div class="opts small">
    <button class="opt lic" type="button" data-i="{i}" data-lic="Y"
            aria-pressed="false">Yes</button>
    <button class="opt lic" type="button" data-i="{i}" data-lic="N"
            aria-pressed="false">No</button>
    <button class="opt unsure" type="button" data-i="{i}"
            aria-pressed="false">Not sure</button>
  </div>
</section>""")

    defs = "".join(f'<div class="def"><b class="mono">{n}</b><p>{d}</p></div>'
                   for n, d in DEFS)

    doc = f"""<title>Column Leakage Coding</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<header class="bar"><div class="bar-in">
  <h1>Column coding</h1>
  <span class="count"><span id="n">0</span> / {len(items)} answered</span>
  <span class="saved" id="saved"></span>
  <div class="track"><div class="fill" id="fill"></div></div>
</div></header>
<div class="wrap">
<div class="intro">
  <h2>Why does each of these columns give the answer away?</h2>
  <p class="lede">Every column below comes from a public dataset and has been
  judged unusable for prediction. Your job is to say <b>why</b> — and whether
  the evidence shown supports that judgement at all. No expertise is needed;
  everything required is on each card. About 40 minutes.</p>

  <details class="book" open><summary>Read this first</summary>
  <div class="book-body">
    <p>You are judging <b>one column against one target, at one moment in
    time</b> — the <b>prediction point</b>, the instant the model is asked for
    its answer. A value that does not honestly exist yet at that moment, or
    that exists only because the outcome already happened, is inadmissible.</p>

    <h3>The four categories</h3>
    <div class="defs">{defs}</div>
    <p style="font-size:.92rem;color:var(--ink-soft);margin:.6rem 0 0">
    The distinction between the first two is one question:
    <b>Reason is about how the <i>label</i> was made. Consequence is about how
    the <i>column</i> was made.</b> Both correlate with the outcome — every
    leaking column does — so correlation tells you nothing. Ask which way the
    arrow points.</p>

    <h3>When two seem to apply</h3>
    <p style="font-size:.92rem;color:var(--ink-soft);margin:0">Some columns are
    genuinely both a trace of the outcome and an input to the label. Check in
    this order and stop at the first yes:</p>
    <ol class="order">
      <li>Does the quotation say the target was <b>computed, derived or decided
          from</b> this column? → <b>Reason</b></li>
      <li>Else — would the column be <b>blank, absent or meaningless</b> if the
          outcome had gone the other way? → <b>Consequence</b></li>
      <li>Else — is it simply <b>recorded after</b> the prediction point?
          → <b>Timing</b></li>
      <li>Else, and only else → <b>Contested</b></li>
    </ol>

    <h3>Rules</h3>
    <ul class="rules">
      <li><b>Judge the quotation, not the domain.</b> If the sentence only tells
      you <i>when</i> a value was recorded, that is Timing even if you suspect
      something deeper.</li>
      <li><b>Work alone.</b> Do not discuss items with anyone else who is
      coding them.</li>
      <li><b>Answer &ldquo;No&rdquo; freely</b> on the second question. A
      disagreement there is more useful than a polite yes.</li>
      <li>Do not go back and change earlier answers once you spot a pattern.</li>
    </ul>
    <p style="font-size:.9rem;color:var(--ink-soft);margin:.9rem 0 0">
    Keyboard: <kbd>1</kbd>–<kbd>4</kbd> pick a category,
    <kbd>y</kbd> / <kbd>n</kbd> answer the second question,
    <kbd>?</kbd> marks it unsure, <kbd>j</kbd>&nbsp;/&nbsp;<kbd>k</kbd> move between cards. Keys apply to the card outlined as <b>current</b>. Your answers save automatically.</p>
  </div></details>
</div>

{''.join(rows)}

<div class="out">
  <h3>Your answers</h3>
  <p>When every card is answered, copy this and send it back. Nothing is
  uploaded from this page.</p>
  <textarea id="out" readonly spellcheck="false"></textarea>
  <div class="row">
    <button class="act" type="button" id="copy">Copy answers</button>
    <button class="act ghost" type="button" id="jump">Go to first unanswered</button>
    <button class="act ghost" type="button" id="reset">Start over</button>
    <span class="note" id="warn"></span>
  </div>
</div>
</div>
<script>
const N = {len(items)}, KEY = "leakcoding.v1";
let S = {{}};
try {{ S = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{ S = {{}}; }}

const el = (s, r) => (r || document).querySelector(s);
const all = (s, r) => Array.from((r || document).querySelectorAll(s));
const rec = i => (S[i] = S[i] || {{}});
const complete = i => S[i] && S[i].cat && S[i].lic;

function save() {{
  try {{
    localStorage.setItem(KEY, JSON.stringify(S));
    const s = el("#saved"); s.textContent = "saved";
    clearTimeout(save._t); save._t = setTimeout(() => s.textContent = "", 1200);
  }} catch (e) {{ el("#saved").textContent = "not saved — copy before closing"; }}
}}

function paint(i) {{
  const card = el("#i" + i); if (!card) return;
  const r = S[i] || {{}};
  all("button.opt[data-cat]", card).forEach(b =>
    b.setAttribute("aria-pressed", String(r.cat === b.dataset.cat)));
  all("button.opt.lic", card).forEach(b =>
    b.setAttribute("aria-pressed", String(r.lic === b.dataset.lic)));
  el("button.unsure", card).setAttribute("aria-pressed", String(!!r.unsure));
  card.classList.toggle("done", !!complete(i));
}}

function render() {{
  let done = 0, lines = [];
  for (let i = 1; i <= N; i++) {{
    if (complete(i)) {{
      done++;
      lines.push(i + " " + S[i].cat + " " + S[i].lic + (S[i].unsure ? " ?" : ""));
    }}
  }}
  el("#n").textContent = done;
  el("#fill").style.width = (100 * done / N) + "%";
  el("#out").value = lines.join("\\n");
  el("#warn").textContent = done === N ? "" : (N - done) + " still to answer";
}}

// One decision per click; nothing is pre-selected, because a default on the
// second question would bias it toward agreement.
document.addEventListener("click", e => {{
  const b = e.target.closest("button.opt"); if (!b) return;
  const i = +b.dataset.i, r = rec(i);
  if (b.dataset.cat) r.cat = (r.cat === b.dataset.cat) ? null : b.dataset.cat;
  else if (b.dataset.lic) r.lic = (r.lic === b.dataset.lic) ? null : b.dataset.lic;
  else r.unsure = !r.unsure;
  paint(i); render(); save();
}});

// The current card is EXPLICIT and visibly marked.  An earlier version
// inferred it from scroll position, and a browser test caught it applying a
// keystroke to the card above the one intended -- a coder would have silently
// answered the wrong item, which in a reliability study is indistinguishable
// from a real disagreement.  Never guess which item the user means.
let cur = 1;
function setCur(i, scroll) {{
  cur = Math.max(1, Math.min(N, i));
  all("section.card").forEach(c =>
    c.classList.toggle("is-cur", +c.dataset.i === cur));
  if (scroll !== false) {{
    const c = el("#i" + cur);
    if (c) c.scrollIntoView({{behavior: "smooth", block: "start"}});
  }}
}}

document.addEventListener("click", e => {{
  const c = e.target.closest("section.card");
  if (c) setCur(+c.dataset.i, false);
}}, true);

document.addEventListener("keydown", e => {{
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) return;
  const k = e.key.toLowerCase();
  if (k === "j" || e.key === "ArrowDown") {{ e.preventDefault(); return setCur(cur + 1); }}
  if (k === "k" || e.key === "ArrowUp")   {{ e.preventDefault(); return setCur(cur - 1); }}
  const i = cur, r = rec(i);
  const cats = {json.dumps(CATS)};
  if (k >= "1" && k <= "4") r.cat = cats[+k - 1];
  else if (k === "y" || k === "n") r.lic = k.toUpperCase();
  else if (k === "?" || k === "/") r.unsure = !r.unsure;
  else return;
  e.preventDefault(); paint(i); render(); save();
  if (complete(i) && i < N) setCur(i + 1);
}});

el("#copy").addEventListener("click", async () => {{
  const t = el("#out");
  try {{ await navigator.clipboard.writeText(t.value); }}
  catch (err) {{ t.removeAttribute("readonly"); t.select();
                document.execCommand("copy"); t.setAttribute("readonly",""); }}
  const b = el("#copy"); b.textContent = "Copied";
  setTimeout(() => b.textContent = "Copy answers", 1400);
}});

el("#jump").addEventListener("click", () => {{
  for (let i = 1; i <= N; i++) if (!complete(i)) {{
    el("#i" + i).scrollIntoView({{behavior: "smooth", block: "start"}}); return;
  }}
  el(".out").scrollIntoView({{behavior: "smooth"}});
}});

el("#reset").addEventListener("click", () => {{
  if (!confirm("Delete every answer on this page and start again?")) return;
  S = {{}}; try {{ localStorage.removeItem(KEY); }} catch (e) {{}}
  for (let i = 1; i <= N; i++) paint(i);
  render(); window.scrollTo({{top: 0, behavior: "smooth"}});
}});

for (let i = 1; i <= N; i++) paint(i);
render();
let first = 1;
while (first < N && complete(first)) first++;
setCur(first, false);
</script>"""
    open(OUT, "w").write(doc)
    print(f"wrote {OUT}  ({len(items)} items, {len(doc)/1024:.0f} KB)")
    leaked = [c for c in CATS if doc.count(c) and c not in ("REASON",)]
    print("  subtype key withheld:",
          "coding_key.json is NOT referenced by the page:",
          "coding_key" not in doc)


if __name__ == "__main__":
    build()
