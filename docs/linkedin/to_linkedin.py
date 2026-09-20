"""Convert article.md into text you can paste straight into LinkedIn's article editor.

    python docs/linkedin/to_linkedin.py

LinkedIn's editor has no markdown, no tables and no code blocks. So this:
  * strips ** and _ emphasis and `code` ticks (apply bold in the editor by hand),
  * turns tables into "label — value" lines,
  * replaces fenced code with an [IMAGE: ...] marker for the matching slide,
  * flattens headings to their own lines, marked so you can apply H2 quickly.

Writes article_linkedin.txt and reports the character count against the
~110,000 limit.
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "article.md"
DST = HERE / "article_linkedin.txt"
ARTICLE_LIMIT = 110_000
TITLE_LIMIT = 100


def strip_inline(s: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", s)   # links -> text (url)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s


def table_rows(lines: list[str]) -> list[str]:
    """Markdown table -> 'first column — rest' lines, dropping the separator row."""
    out = []
    header = None
    for raw in lines:
        cells = [strip_inline(c.strip()) for c in raw.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if header is None:
            header = cells
            continue
        label, rest = cells[0], cells[1:]
        pairs = [f"{h}: {v}" for h, v in zip(header[1:], rest) if v]
        out.append(f"• {label} — " + "; ".join(pairs))
    return out


def convert(md: str) -> tuple[str, str]:
    lines = md.splitlines()
    title = ""
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):                       # fenced block -> image marker
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                i += 1
            out.append("[IMAGE: slides/slide_4.png — the architecture diagram]")
            i += 1
            continue

        if line.startswith("|"):                          # table
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            out.extend(table_rows(block))
            continue

        if line.startswith("# "):
            title = strip_inline(line[2:].strip())
            i += 1
            continue

        m = re.match(r"^(#{2,4})\s+(.*)$", line)
        if m:
            text = strip_inline(m.group(2))
            text = re.sub(r"^\d+(\.\d+)*\.?\s*", "", text)   # drop 4.1 style numbering
            out.append("")
            out.append(f"[H{min(len(m.group(1)), 3)}] {text}")
            i += 1
            continue

        if line.strip() == "---":
            out.append("")
            i += 1
            continue

        if re.match(r"^\s*[-*]\s+", line):
            out.append("• " + strip_inline(re.sub(r"^\s*[-*]\s+", "", line)))
            i += 1
            continue

        out.append(strip_inline(line))
        i += 1

    text = "\n".join(out)
    # emphasis that wraps across a line break survives the per-line pass, so run
    # the same strip over the joined text ([^*] keeps a match inside one span)
    text = re.sub(r"\*\*([^*]{1,600}?)\*\*", r"\1", text, flags=re.S)
    text = re.sub(r"(?<!\w)\*([^*]{1,600}?)\*(?!\w)", r"\1", text, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text, flags=re.S)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return title, text


def main() -> None:
    title, body = convert(SRC.read_text(encoding="utf-8"))
    DST.write_text(
        "TITLE (<=100 chars, paste into the article title field):\n"
        f"{title}\n\n"
        "HOW TO USE: paste everything below the line into LinkedIn's article editor.\n"
        "Lines marked [H2]/[H3] are headings -- delete the marker and apply the heading\n"
        "style. Lines marked [IMAGE: ...] are where to upload that file.\n"
        + "=" * 78 + "\n\n" + body,
        encoding="utf-8")
    n = len(body)
    print(f"title      {len(title):>3} / {TITLE_LIMIT} chars"
          f"{'' if len(title) <= TITLE_LIMIT else '   TOO LONG'}")
    print(f"body    {n:>6} / {ARTICLE_LIMIT} chars"
          f"{'' if n <= ARTICLE_LIMIT else '   TOO LONG'}")
    print(f"wrote {DST}")
    raise SystemExit(0 if n <= ARTICLE_LIMIT and len(title) <= TITLE_LIMIT else 1)


if __name__ == "__main__":
    main()
