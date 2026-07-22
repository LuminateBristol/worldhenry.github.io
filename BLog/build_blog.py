#!/usr/bin/env python3
"""
build_blog.py — generate The Build Log index from the posts/ folder.

How it works:
  - Scans posts/ for files named as a date: YYYYMMDD.html  (e.g. 20260718.html)
  - Reads each post's <meta name="post-title|post-summary|post-tag"> tags
  - Sorts posts by date, newest first
  - Rewrites the preview list in blog.html between the POSTS markers

Usage:
  python3 build_blog.py

Add a post: drop a new YYYYMMDD.html file in posts/ (copy an existing one),
then run this script again. No need to edit blog.html by hand.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
INDEX = ROOT / "blog.html"

START = "<!-- POSTS:START -->"
END = "<!-- POSTS:END -->"

DATE_FILE = re.compile(r"^(\d{8})\.html$")


def meta(content: str, name: str, default: str = "") -> str:
    """Pull a <meta name="..." content="..."> value from an HTML string."""
    m = re.search(
        r'<meta\s+name=["\']%s["\']\s+content=["\'](.*?)["\']\s*/?>' % re.escape(name),
        content,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip() if m else default


def collect_posts():
    posts = []
    if not POSTS_DIR.is_dir():
        return posts
    for f in POSTS_DIR.iterdir():
        m = DATE_FILE.match(f.name)
        if not m:
            continue
        raw = m.group(1)
        try:
            date = datetime.strptime(raw, "%Y%m%d")
        except ValueError:
            print(f"  ! skipping {f.name}: not a valid YYYYMMDD date")
            continue
        html = f.read_text(encoding="utf-8")
        posts.append({
            "date": date,
            "iso": date.strftime("%Y-%m-%d"),
            "href": f"posts/{f.name}",
            "title": meta(html, "post-title", f.stem),
            "summary": meta(html, "post-summary", ""),
            "tag": meta(html, "post-tag", ""),
        })
    # newest first
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def render(posts) -> str:
    if not posts:
        return (
            '\n      <p class="log-empty" style="color:var(--muted);'
            'font-family:var(--mono);font-size:.85rem;">no posts yet — '
            'add one to the posts/ folder and run build_blog.py</p>\n'
        )
    blocks = []
    for p in posts:
        tag = (
            f'\n          <span class="log-tag">{escape(p["tag"])}</span>'
            if p["tag"] else ""
        )
        blocks.append(
            f'''
      <a class="log-entry" href="{escape(p["href"])}">
        <div class="log-meta">
          <span class="log-date">{escape(p["iso"])}</span>{tag}
        </div>
        <h2>{escape(p["title"])}</h2>
        <p class="log-summary">{escape(p["summary"])}</p>
        <span class="log-readmore">read <span class="arrow">&rarr;</span></span>
      </a>'''
        )
    return "\n" + "\n".join(blocks) + "\n\n      "


def main():
    if not INDEX.exists():
        sys.exit(f"error: {INDEX} not found")
    html = INDEX.read_text(encoding="utf-8")
    if START not in html or END not in html:
        sys.exit(f"error: markers {START} / {END} not found in blog.html")

    posts = collect_posts()
    generated = render(posts)
    new_html = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        START + generated + END,
        html,
        flags=re.DOTALL,
    )
    INDEX.write_text(new_html, encoding="utf-8")
    print(f"Built {len(posts)} post(s) into blog.html:")
    for p in posts:
        print(f"  {p['iso']}  {p['title']}")


if __name__ == "__main__":
    main()
