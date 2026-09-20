"""Check each block in post.md against LinkedIn's limits.

    python docs/linkedin/check.py

Post body: 3000 characters. Comment: 1250. Blocks are the '> ' quoted sections
of post.md and followups.md.
"""
from __future__ import annotations

import re
from pathlib import Path

POST_LIMIT = 3000
COMMENT_LIMIT = 1250
HERE = Path(__file__).parent
SRCS = [HERE / "post.md", HERE / "followups.md"]


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
    bad = 0
    for src in SRCS:
        if not src.exists():
            continue
        print(f"\n{src.name}")
        bad += check_file(src)
    raise SystemExit(1 if bad else 0)


def check_file(src) -> int:
    bad = 0
    for heading, body in blocks(src.read_text(encoding="utf-8")):
        limit = POST_LIMIT if heading.lower().startswith("post ") else COMMENT_LIMIT
        n = len(body)
        ok = n <= limit
        bad += not ok
        safe = heading.encode("ascii", "replace").decode()   # Windows console is cp1252
        print(f"  {'ok  ' if ok else 'OVER'} {safe:<42} {n:>5} / {limit}"
              f"{'' if ok else f'   trim {n - limit}'}")
    return bad


if __name__ == "__main__":
    main()
