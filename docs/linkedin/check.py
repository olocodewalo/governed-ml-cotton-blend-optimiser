"""Check each block in post.md against LinkedIn's limits.

    python docs/linkedin/check.py

Post body: 3000 characters. Comment: 1250. Blocks are the '> ' quoted sections.
"""
from __future__ import annotations

import re
from pathlib import Path

POST_LIMIT = 3000
COMMENT_LIMIT = 1250
SRC = Path(__file__).parent / "post.md"


def blocks(text: str):
    """(heading, body) for every '> ' quoted block, under its nearest heading."""
    out, heading, buf = [], "?", []
    for line in text.splitlines():
        if line.startswith("#") or line.startswith("**Comment"):
            if buf:
                out.append((heading, "\n".join(buf).strip()))
                buf = []
            heading = line.lstrip("#* ").rstrip("*").strip()
        elif line.startswith(">"):
            buf.append(line[1:].lstrip() if line.startswith("> ") else line[1:])
        elif buf and not line.strip():
            continue
        elif buf:
            out.append((heading, "\n".join(buf).strip()))
            buf = []
    if buf:
        out.append((heading, "\n".join(buf).strip()))
    return out


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    bad = 0
    for heading, body in blocks(text):
        limit = POST_LIMIT if heading.lower().startswith("post ") else COMMENT_LIMIT
        n = len(body)
        ok = n <= limit
        bad += not ok
        safe = heading.encode("ascii", "replace").decode()   # Windows console is cp1252
        print(f"{'ok  ' if ok else 'OVER'} {safe:<42} {n:>5} / {limit}"
              f"{'' if ok else f'   trim {n - limit}'}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
