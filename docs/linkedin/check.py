"""Check every drafted block against the limit LinkedIn enforces on it.

    python docs/linkedin/check.py

Blocks are the '> ' quoted sections of the drafts; the heading above each one
decides which limit applies. Exits 1 if anything is over, so it doubles as a
pre-publish check.
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent
SRCS = [HERE / "post.md", HERE / "followups.md", HERE.parent / "press" / "connect_notes.md"]

# heading keyword -> LinkedIn's limit for that surface
LIMITS = [
    ("connect", 300),        # invitation note
    ("inmail", 1900),        # Premium InMail body
    ("subject", 1900),       # the InMail body sits under its subject line
    ("follow-up", 8000),     # direct message
    ("post ", 3000),         # feed post
]
DEFAULT_LIMIT = 1250         # comment / reply


def limit_for(heading: str) -> int:
    h = heading.lower()
    for key, limit in LIMITS:
        if key in h:
            return limit
    return DEFAULT_LIMIT


def blocks(text: str):
    """(heading, body) for every '> ' quoted block, under its nearest heading."""
    out, heading, buf = [], "?", []
    for line in text.splitlines():
        is_heading = line.startswith("#") or (line.startswith("**") and not line.startswith("> "))
        if is_heading:
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


def check_file(src: Path) -> int:
    bad = 0
    for heading, body in blocks(src.read_text(encoding="utf-8")):
        limit = limit_for(heading)
        n = len(body)
        ok = n <= limit
        bad += not ok
        safe = heading.encode("ascii", "replace").decode()   # Windows console is cp1252
        print(f"  {'ok  ' if ok else 'OVER'} {safe[:46]:<46} {n:>5} / {limit}"
              f"{'' if ok else f'   trim {n - limit}'}")
    return bad


def main() -> None:
    bad = 0
    for src in SRCS:
        if not src.exists():
            continue
        print(f"\n{src.relative_to(HERE.parent)}")
        bad += check_file(src)
    print()
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
