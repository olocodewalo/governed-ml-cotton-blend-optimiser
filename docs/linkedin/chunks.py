"""Split the article body into paste-sized chunks of HTML.

    python docs/linkedin/chunks.py            # list the chunks and their sizes
    python docs/linkedin/chunks.py --part 2   # print one chunk, ready to paste

LinkedIn's editor is ProseMirror: a synthetic paste event carrying text/html is
the only reliable way to get formatted content in, and the content has to travel
inside the script rather than be fetched (LinkedIn's CSP blocks outside origins).
Chunks split on <h2> boundaries so no element is ever cut in half.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "article_body_clean.html"
TARGET = 5200          # characters per chunk

RAW = "https://raw.githubusercontent.com/olocodewalo/governed-ml-cotton-blend-optimiser/main/"
FIX = {"slides/slide_4.png": "docs/linkedin/slides/slide_4.png"}


def body_html() -> str:
    raw = SRC.read_text(encoding="utf-8")
    raw = re.sub(r"<style>.*?</style>", "", raw, flags=re.S)
    raw = re.sub(r"<meta[^>]*>|<title>.*?</title>", "", raw, flags=re.S)
    # turn the upload markers into real <img> tags pointing at the public repo.
    # LinkedIn's editor fetches an external image on paste and re-hosts it on its
    # own CDN, so the images land in position with no manual upload step.
    def as_img(path: str) -> str:
        path = FIX.get(path.strip(), path.strip())
        return f'<img src="{RAW}{path}">'

    raw = re.sub(r'<p class="upload">UPLOAD IMAGE HERE: ([^<]+)<br>.*?</p>',
                 lambda m: as_img(m.group(1)), raw, flags=re.S)
    raw = re.sub(r'<p class="upload">UPLOAD IMAGE HERE: ([^<]+?)\s*\(([^)]*)\)</p>',
                 lambda m: as_img(m.group(1)), raw)
    raw = re.sub(r">\n+<", "><", raw)     # newlines only: a space between tags can be real
    return raw.strip()


def split(html: str, target: int = TARGET) -> list[str]:
    parts = re.split(r"(?=<h[23]>)", html)
    chunks, cur = [], ""
    for p in parts:
        if cur and len(cur) + len(p) > target:
            chunks.append(cur)
            cur = p
        else:
            cur += p
    if cur:
        chunks.append(cur)
    return chunks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", type=int)
    args = ap.parse_args()
    chunks = split(body_html())
    if args.part:
        text = chunks[args.part - 1]
        # the JS payload wraps this in a template literal
        print(text.replace("`", "'").replace("${", "$ {"))
        return
    for i, c in enumerate(chunks, 1):
        head = re.search(r"<h[23]>(.*?)</h[23]>", c)
        print(f"part {i}: {len(c):>6} chars   starts at: {head.group(1)[:60] if head else '(intro)'}")
    print(f"total: {sum(len(c) for c in chunks)} chars in {len(chunks)} parts")


if __name__ == "__main__":
    main()
