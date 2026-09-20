"""Render article.md as rich text you can paste into LinkedIn with formatting intact.

    python docs/linkedin/to_paste_html.py
    # then: open docs/linkedin/article_paste.html in a browser, Ctrl+A, Ctrl+C,
    #       and paste into LinkedIn's article editor

LinkedIn's editor accepts pasted rich text, so headings, bold, italics and lists
survive the clipboard — which saves reformatting ~25 headings by hand. Tables and
code blocks do not survive, so tables become plain lines and code blocks become a
visible red marker telling you which image to upload there.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "article.md"
DST = HERE / "article_paste.html"
CLEAN = HERE / "article_body_clean.html"

STYLE = """<style>
 body { font-family: Georgia, 'Times New Roman', serif; max-width: 760px; margin: 40px auto;
        padding: 0 24px; line-height: 1.6; color: #111; }
 h1 { font-size: 34px; line-height: 1.2; }
 h2 { font-size: 26px; margin-top: 34px; }
 h3 { font-size: 20px; margin-top: 26px; }
 .upload { background: #ffe9e6; border: 2px dashed #c0392b; color: #7b1c12;
           padding: 12px 16px; font-family: system-ui, sans-serif; font-weight: 700; }
 .note { background: #eef5f1; border-left: 4px solid #0f7a52; padding: 10px 16px;
         font-family: system-ui, sans-serif; font-size: 14px; }
</style>"""

HOWTO = """<p class="note">HOW TO USE: click anywhere in this page, press Ctrl+A then Ctrl+C,
and paste into LinkedIn's article editor. Headings, bold and lists come across with the
text. Then delete this box and the red UPLOAD markers, uploading the image each one names.
The title is the H1 below -- LinkedIn keeps it in its own field, so cut it from the body.</p>"""


def inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", s)
    # bold may wrap an italic span, e.g. **Micronaire *variance***
    s = re.sub(r"\*\*((?:[^*]|\*[^*]+\*)+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def table_lines(block: list[str]) -> list[str]:
    header, out = None, []
    for raw in block:
        cells = [c.strip() for c in raw.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if header is None:
            header = cells
            continue
        pairs = [f"{h}: {v}" for h, v in zip(header[1:], cells[1:]) if v]
        out.append(f"<li>{inline(cells[0])} — {inline('; '.join(pairs))}</li>")
    return ["<ul>"] + out + ["</ul>"]


def convert(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i, para, bullets = 0, [], []

    def flush():
        nonlocal para, bullets
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para = []
        if bullets:
            out.append("<ul>" + "".join(f"<li>{inline(b)}</li>" for b in bullets) + "</ul>")
            bullets = []

    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            flush()
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                i += 1
            out.append('<p class="upload">UPLOAD IMAGE HERE: slides/slide_4.png '
                       '(the architecture diagram)</p>')
            i += 1
            continue

        if line.startswith("|"):
            flush()
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            out.extend(table_lines(block))
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush()
            level = min(len(m.group(1)), 3)
            text = re.sub(r"^\d+(\.\d+)*\.?\s*", "", m.group(2))
            out.append(f"<h{level}>{inline(text)}</h{level}>")
            i += 1
            continue

        if line.strip() == "---":
            flush()
            i += 1
            continue

        mb = re.match(r"^\s*(?:[-*]|\d+\.)\s+(.*)$", line)
        if mb:
            if para:
                flush()
            bullets.append(mb.group(1))
            i += 1
            continue

        if not line.strip():
            flush()
            i += 1
            continue

        if bullets:                      # continuation line of the last bullet
            bullets[-1] += " " + line.strip()
        else:
            para.append(line.strip())
        i += 1

    flush()
    return "\n".join(out)


# Where the visuals go: (heading text to insert after, file, caption)
IMAGES = [
    ("The decision this system supports",
     "docs/screenshots/01_review_screen.png",
     "The review screen the mixing master sees: recommended blend, predicted quality with "
     "P10-P90 intervals, the confidence level and its reasons, and the price-age check."),
    ("Uncertainty — and why it decides everything downstream",
     "docs/linkedin/slides/slide_5.png",
     "Why the intervals mattered more than the predictions."),
    ("The optimiser — why two of them",
     "docs/linkedin/slides/slide_6.png",
     "MILP for speed and shadow prices; the genetic algorithm for the full non-linear model."),
    ("Results, and how they shrank",
     "docs/linkedin/slides/slide_9.png",
     "Every headline number, before and after the audit."),
    ("Governance — the part that actually changed the outcome",
     "docs/linkedin/slides/slide_10.png",
     "The promotion gate refusing its own author."),
]


def add_image_markers(body: str) -> str:
    for heading, path, caption in IMAGES:
        pattern = re.compile(rf"(<h[23]>{re.escape(html.escape(heading))}</h[23]>)")
        marker = (f'<p class="upload">UPLOAD IMAGE HERE: {path}<br>'
                  f'<span style="font-weight:400">caption: {html.escape(caption)}</span></p>')
        body, n = pattern.subn(rf"\1\n{marker}", body, count=1)
        if not n:
            print(f"  [warn] no heading matched for {path}")
    return body


def main() -> None:
    body = add_image_markers(convert(SRC.read_text(encoding="utf-8")))
    DST.write_text(f"<meta charset='utf-8'><title>Paste into LinkedIn</title>{STYLE}\n{HOWTO}\n{body}\n",
                   encoding="utf-8")
    # clean variant: no instructions box, no H1 -- a select-all copy of this file is
    # exactly what belongs in the article body
    clean = re.sub(r"<h1>.*?</h1>", "", body, flags=re.S)
    CLEAN.write_text(f"<meta charset='utf-8'><title>Article body</title>{STYLE}\n{clean}\n",
                     encoding="utf-8")
    marker = 'class="upload"'
    print(f"wrote {DST}\nwrote {CLEAN}")
    print(f"headings: {body.count('<h2>') + body.count('<h3>')}, "
          f"lists: {body.count('<ul>')}, bold: {body.count('<strong>')}, "
          f"image markers: {body.count(marker)}")


if __name__ == "__main__":
    main()
