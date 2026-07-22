#!/usr/bin/env python3
"""
build_portfolio.py — generate the art & robots project pages from projects/.

How it works:
  - Scans projects/art/ and projects/robots/ for folders named YYYYMMDD-slug
    (e.g. 20240101-space-pride/)
  - Reads each project's description.txt for a "title:" line, an optional
    "date:" line (free text, just for display — sort order always comes
    from the YYYYMMDD folder prefix), any number of "link: Label | URL"
    lines, then a blank line, then the body text (blank-line-separated
    paragraphs)
  - Finds every image/video file in the folder and builds a carousel from
    them; an empty folder gets a placeholder slide
  - Sorts projects newest-first by folder date
  - Rewrites the project list in art.html / copy.html between the
    PROJECTS markers

Naming media files:
  Name each image/video 1.<ext>, 2.<ext>, 3.<ext>, ... (any extension,
  mixed images and videos in one sequence) — that's the carousel order.
  Files not named as a plain number still work, sorted alphabetically
  after the numbered ones, so nothing breaks if one is missed.

Usage:
  python3 build_portfolio.py

Add a project: create projects/art/YYYYMMDD-slug/ (or projects/robots/...),
drop numbered images/videos and a description.txt in it, then run this
script again (or just commit — the pre-commit hook runs it for you).
"""

import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parent
PROJECTS_DIR = ROOT / "projects"

START = "<!-- PROJECTS:START -->"
END = "<!-- PROJECTS:END -->"

FOLDER_RE = re.compile(r"^(\d{8})-(.+)$")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v"}

POSTERS_DIRNAME = ".posters"

PAGES = {
    "art": ROOT / "art.html",
    "robots": ROOT / "copy.html",
}

FFMPEG = shutil.which("ffmpeg")
_warned_no_ffmpeg = False


def ensure_poster(video_path: Path) -> str | None:
    """Extract a first-frame thumbnail for a video, cached in .posters/.
    Returns the poster filename (relative to the project folder) or None."""
    global _warned_no_ffmpeg
    if not FFMPEG:
        if not _warned_no_ffmpeg:
            print("  ! ffmpeg not found — videos will show without a poster thumbnail")
            _warned_no_ffmpeg = True
        return None

    posters_dir = video_path.parent / POSTERS_DIRNAME
    poster_path = posters_dir / f"{video_path.name}.jpg"

    if poster_path.exists() and poster_path.stat().st_mtime >= video_path.stat().st_mtime:
        return f"{POSTERS_DIRNAME}/{poster_path.name}"

    posters_dir.mkdir(exist_ok=True)
    result = subprocess.run(
        [
            FFMPEG, "-y", "-ss", "0.1", "-i", str(video_path),
            "-frames:v", "1", "-q:v", "3", str(poster_path),
        ],
        capture_output=True,
    )
    if result.returncode != 0 or not poster_path.exists():
        print(f"  ! failed to generate poster for {video_path.name}")
        return None
    return f"{POSTERS_DIRNAME}/{poster_path.name}"


def parse_description(path: Path) -> dict:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines()

    title = ""
    date = ""
    links = []
    body_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "":
            body_start = i + 1
            break
        m = re.match(r"^(title|date|link)\s*:\s*(.*)$", stripped, re.IGNORECASE)
        if not m:
            body_start = i
            break
        key, value = m.group(1).lower(), m.group(2).strip()
        if key == "title":
            title = value
        elif key == "date":
            date = value
        elif key == "link":
            if "|" in value:
                label, url = value.split("|", 1)
                links.append((label.strip(), url.strip()))
        body_start = i + 1

    body_text = "\n".join(lines[body_start:]).strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body_text) if p.strip()]

    return {"title": title, "date": date, "links": links, "paragraphs": paragraphs}


def media_sort_key(f: Path):
    """Numbered files (1.png, 2.mp4, 10.jpg, ...) sort numerically and come
    first; anything else falls back to alphabetical, after the numbered
    ones — so a stray non-numbered file doesn't break the build."""
    if re.fullmatch(r"\d+", f.stem):
        return (0, int(f.stem))
    return (1, f.name.lower())


def prune_posters(folder: Path, current_video_names: set):
    """Delete cached posters for videos that no longer exist (renamed/removed)."""
    posters_dir = folder / POSTERS_DIRNAME
    if not posters_dir.is_dir():
        return
    valid = {f"{name}.jpg" for name in current_video_names}
    for poster in posters_dir.iterdir():
        if poster.is_file() and poster.name not in valid:
            poster.unlink()


def collect_media(folder: Path):
    media = []
    video_names = set()
    for f in sorted(folder.iterdir(), key=media_sort_key):
        if f.name.startswith(".") or not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in IMAGE_EXTS:
            media.append(("image", f.name, None))
        elif ext in VIDEO_EXTS:
            media.append(("video", f.name, ensure_poster(f)))
            video_names.add(f.name)
    prune_posters(folder, video_names)
    return media


def collect_projects(category: str):
    projects = []
    cat_dir = PROJECTS_DIR / category
    if not cat_dir.is_dir():
        return projects
    for folder in cat_dir.iterdir():
        if not folder.is_dir():
            continue
        m = FOLDER_RE.match(folder.name)
        if not m:
            print(f"  ! skipping {folder}: not named YYYYMMDD-slug")
            continue
        raw, slug = m.group(1), m.group(2)
        try:
            sort_date = datetime.strptime(raw, "%Y%m%d")
        except ValueError:
            print(f"  ! skipping {folder}: invalid date prefix {raw!r}")
            continue
        desc = parse_description(folder / "description.txt")
        media = collect_media(folder)
        projects.append({
            "slug": slug,
            "sort_date": sort_date,
            "href_base": f"projects/{category}/{folder.name}",
            "title": desc["title"] or slug.replace("-", " ").title(),
            "date": desc["date"],
            "links": desc["links"],
            "paragraphs": desc["paragraphs"],
            "media": media,
        })
    projects.sort(key=lambda p: p["sort_date"], reverse=True)
    return projects


def render_carousel(project) -> str:
    media = project["media"]
    href_base = project["href_base"]

    if not media:
        return (
            '\n      <div class="carousel carousel-empty">\n'
            '        <div class="carousel-track">\n'
            '          <div class="carousel-slide is-active">\n'
            '            <div class="media-placeholder">no media yet</div>\n'
            "          </div>\n"
            "        </div>\n"
            "      </div>"
        )

    slides = []
    for i, (kind, name, poster) in enumerate(media):
        active = " is-active" if i == 0 else ""
        src = f"{href_base}/{name}"
        if kind == "image":
            inner = f'<img src="{escape(src)}" alt="{escape(project["title"])}" loading="lazy">'
        else:
            poster_attr = (
                f' poster="{escape(f"{href_base}/{poster}")}"' if poster else ""
            )
            inner = (
                f'<video src="{escape(src)}"{poster_attr} controls muted preload="none" '
                f"playsinline></video>"
            )
        slides.append(f'          <div class="carousel-slide{active}">{inner}</div>')

    nav = ""
    dots = ""
    if len(media) > 1:
        nav = (
            '\n        <button type="button" class="carousel-arrow carousel-prev" '
            'aria-label="Previous">&larr;</button>'
            '\n        <button type="button" class="carousel-arrow carousel-next" '
            'aria-label="Next">&rarr;</button>'
        )
        dot_items = "\n".join(
            f'          <button type="button" class="carousel-dot{" is-active" if i == 0 else ""}" '
            f'aria-label="Go to slide {i + 1}"></button>'
            for i in range(len(media))
        )
        dots = f'\n        <div class="carousel-dots">\n{dot_items}\n        </div>'

    return (
        '\n      <div class="carousel">\n'
        '        <div class="carousel-track">\n'
        + "\n".join(slides)
        + "\n        </div>"
        + nav
        + dots
        + "\n      </div>"
    )


def render(projects) -> str:
    if not projects:
        return (
            '\n      <p class="projects-empty" style="color:#666;font-size:.8rem;">'
            "no projects yet — add one to the projects/ folder and run "
            "build_portfolio.py</p>\n"
        )

    blocks = []
    for p in projects:
        carousel = render_carousel(p)
        meta = f'<span class="project-title">{escape(p["title"])}</span>'
        if p["date"]:
            meta += f'<span class="project-date">{escape(p["date"])}</span>'

        body = "\n".join(
            f"        <p>{escape(para)}</p>" for para in p["paragraphs"]
        )

        links_html = ""
        if p["links"]:
            link_items = "\n".join(
                f'          <a href="{escape(url)}" target="_blank" rel="noopener">{escape(label)}</a>'
                for label, url in p["links"]
            )
            links_html = f'\n      <div class="links">\n{link_items}\n      </div>'

        blocks.append(
            f'''
    <section class="project">{carousel}
      <div class="project-meta">{meta}</div>
{body}{links_html}
    </section>'''
        )
    return "\n" + "\n".join(blocks) + "\n\n    "


def build_page(category: str):
    index = PAGES[category]
    if not index.exists():
        sys.exit(f"error: {index} not found")
    html = index.read_text(encoding="utf-8")
    if START not in html or END not in html:
        sys.exit(f"error: markers {START} / {END} not found in {index}")

    projects = collect_projects(category)
    generated = render(projects)
    new_html = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        START + generated + END,
        html,
        flags=re.DOTALL,
    )
    index.write_text(new_html, encoding="utf-8")
    print(f"Built {len(projects)} project(s) into {index.name}:")
    for p in projects:
        print(f"  {p['sort_date'].date()}  {p['title']}  ({len(p['media'])} media)")


def main():
    for category in PAGES:
        build_page(category)


if __name__ == "__main__":
    main()
