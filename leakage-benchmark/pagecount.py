"""Page count of a manuscript, measured rather than estimated.

WHY THIS EXISTS

  The 12-page target is a submission constraint, and every estimate of it so far
  has been words-per-page arithmetic -- which cannot see a table that breaks
  across a page, a figure that reserves its own block, or a heading that forces
  a break.  Two estimates of the same file differed by three pages depending on
  whether 550 or 600 words per page was assumed, and neither was checkable.

  So: render the markdown at TMLR's approximate geometry (US Letter, 1in
  margins, 10pt serif, single column) and ask a real layout engine where the
  pages fall.  The number is still an approximation of the LaTeX template --
  fonts and spacing differ -- but it is an approximation produced by paginating
  the actual text, not by dividing it.

  Body only.  Appendices and references do not count against a page limit the
  way body text does, and the split is `## Appendices`.
"""
import os, re, sys, asyncio
import markdown
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
# The pinned Chromium build; the bare `chromium` symlink is a different version
# than the installed playwright package expects and refuses to launch.
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

CSS = """
@page { size: letter; margin: 1in; }
body { font: 10pt/1.20 'Times New Roman', Times, serif; margin: 0;
       text-align: justify; }
h1 { font-size: 15pt; text-align: center; margin: 0 0 10pt; }
h2 { font-size: 12pt; margin: 11pt 0 4pt; }
h3 { font-size: 10.5pt; margin: 9pt 0 3pt; }
p  { margin: 0 0 5pt; }
ul { margin: 0 0 5pt 14pt; padding: 0; }
li { margin: 0 0 3pt; }
table { border-collapse: collapse; font-size: 8.5pt; margin: 5pt 0 8pt;
        width: 100%; }
th, td { border: 0.4pt solid #999; padding: 1.2pt 4pt; }
code { font-family: 'Courier New', monospace; font-size: 9pt; }
img { display: block; height: 2.2in; margin: 6pt auto; }
hr { border: 0; border-top: 0.4pt solid #ccc; margin: 8pt 0; }
"""


async def count(path):
    src = open(HERE + path, errors="replace").read()
    body = src.split("## Appendices")[0]
    html = markdown.markdown(body, extensions=["tables", "sane_lists"])
    page = f"<html><head><meta charset=utf-8><style>{CSS}</style></head>" \
           f"<body>{html}</body></html>"
    tmp = HERE + f".pagecount_{os.path.basename(path)}.html"
    open(tmp, "w").write(page)
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=CHROME)
        pg = await b.new_page()
        await pg.goto("file://" + tmp)
        pdf = await pg.pdf(format="Letter",
                           margin={k: "1in" for k in
                                   ("top", "bottom", "left", "right")},
                           print_background=True)
        await b.close()
    out = HERE + path.replace(".md", "_body.pdf")
    open(out, "wb").write(pdf)
    n = pdf.count(b"/Type /Page\n") or pdf.count(b"/Type/Page")
    n = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
    words = len(re.findall(r"\S+", body))
    print(f"  {path:<18} {n:>3} pages   {words:>6} body words   -> {out}")
    return n


async def main():
    print("=" * 72)
    print("PAGE COUNT — body only, paginated at TMLR-like geometry")
    print("=" * 72)
    for p in (sys.argv[1:] or ["PAPER.md", "PAPER_SHORT.md"]):
        await count(p)
    print("\n  Chromium at 10pt Times, not the LaTeX template: read these as"
          "\n  +/- one page, and as a comparison between the two versions.")


if __name__ == "__main__":
    asyncio.run(main())
