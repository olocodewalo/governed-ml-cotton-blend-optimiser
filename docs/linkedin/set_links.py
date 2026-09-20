"""Swap the placeholder links for real ones across the LinkedIn kit.

    python docs/linkedin/set_links.py --repo https://github.com/you/repo
    python docs/linkedin/set_links.py --article https://www.linkedin.com/pulse/...
    python docs/linkedin/set_links.py --repo ... --article ...   --check

Placeholders: XXXX-GITHUB-LINK, XXXX-ARTICLE-LINK. Run to_linkedin.py afterwards
so article_linkedin.txt picks the change up. --check only reports what is still
unresolved (exit 1 if anything is), which is the pre-publish check.
"""
from __future__ import annotations

import argparse
from pathlib import Path

HERE = Path(__file__).parent
FILES = ["post.md", "article.md", "article_linkedin.txt"]
REPO = "XXXX-GITHUB-LINK"
ARTICLE = "XXXX-ARTICLE-LINK"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", help="public GitHub URL")
    ap.add_argument("--article", help="published LinkedIn article URL")
    ap.add_argument("--check", action="store_true", help="only report what is unresolved")
    args = ap.parse_args()

    pending = 0
    for name in FILES:
        path = HERE / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        if args.repo:
            text = text.replace(REPO, args.repo)
        if args.article:
            text = text.replace(ARTICLE, args.article)
        if text != original:
            path.write_text(text, encoding="utf-8")
            print(f"updated {name}")
        left = {p: text.count(p) for p in (REPO, ARTICLE) if text.count(p)}
        pending += sum(left.values())
        if left:
            print(f"  {name}: still placeholder -> " +
                  ", ".join(f"{k} x{v}" for k, v in left.items()))

    if pending:
        print(f"\n{pending} placeholder(s) left. Fill them before publishing.")
    else:
        print("\nno placeholders left")
    raise SystemExit(1 if (pending and args.check) else 0)


if __name__ == "__main__":
    main()
