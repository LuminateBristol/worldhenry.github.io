# worldhenry.github.io

Henry Hickson's portfolio site. Plain HTML/CSS/JS, no framework, no server —
just static pages plus two small Python build scripts that generate the
blog index and the two portfolio pages from folders of content.

```
index.html              home page (links to robots, art, BLog)

Portfolio/
  art.html               "art" page   — auto-generated, don't hand-edit
  copy.html               "robots" page — auto-generated, don't hand-edit
  build_portfolio.py      generates the two pages above from projects/
  carousel.js / style.css
  projects/
    art/     20200101-spacechanger/, 20240101-space-pride/, ...
    robots/  20150101-fortitude/, 20260115-the-hive/, ...

BLog/
  blog.html               post list — auto-generated, don't hand-edit
  about.html
  build_blog.py            generates blog.html from posts/
  posts/   20260718.html, ...
```

---

## Adding a blog post

1. Copy an existing file in `BLog/posts/` and rename it `YYYYMMDD.html`
   (the date it's sorted by — newest first on the blog page).
2. Edit its `<meta name="post-title" ...>`, `post-summary`, `post-tag`,
   and the `<article>` body.
3. Rebuild the index:
   ```
   cd BLog
   python3 build_blog.py
   ```
   (Or just commit — see "Auto-build on commit" below.)

## Adding a portfolio project

1. Create a folder under `Portfolio/projects/art/` or `.../projects/robots/`
   named `YYYYMMDD-slug`, e.g. `20240101-space-pride`. The date controls
   sort order (newest first); it doesn't need to be exact, just correct
   relative to the others.
2. Drop in media files, named **`1.<ext>`, `2.<ext>`, `3.<ext>`, ...** —
   any mix of images and videos, in the order you want them in the
   carousel. Extensions can differ per file (`1.png`, `2.mp4`, `3.mov`, ...).
   Leave the folder empty and the page shows a placeholder instead.
3. Add a `description.txt` in the folder:
   ```
   title: Space Pride
   date: 2024
   link: Press release | https://example.com/press

   Body text goes here, after a blank line. Multiple paragraphs are
   fine — just separate them with a blank line.
   ```
   `date:` is just a display label (free text — "2024", "Ongoing",
   whatever); actual sort order always comes from the `YYYYMMDD` folder
   prefix. `link:` is optional and repeatable, one per line.
4. Rebuild both pages:
   ```
   cd Portfolio
   python3 build_portfolio.py
   ```
   This also extracts a poster thumbnail from the first frame of each
   video (cached in a hidden `.posters/` folder) — requires `ffmpeg`
   (`brew install ffmpeg` if it's missing; the script still works
   without it, videos just show without a thumbnail).

## Adding a whole new page (e.g. a new nav section)

There's no automation for this — it's a one-off. Copy the structure of
`Portfolio/art.html` (header + `<main>`), link it from `index.html`'s
nav, and style it via `Portfolio/style.css` (or its own stylesheet, like
`BLog/blog.css` does).

## Auto-build on commit

A git pre-commit hook (`.git/hooks/pre-commit`) runs both build scripts
automatically before every commit and stages whatever they regenerate
(`blog.html`, `art.html`, `copy.html`, new poster thumbnails). In normal
use you never need to run the build scripts by hand — just add your
post/project folder and commit as usual.

Caveat: `.git/hooks/` isn't tracked by git, so this hook only exists on
this machine. If you ever set up the repo on another computer, recreate
it from this one (or just remember to run the two `build_*.py` scripts
manually before committing).

---

*Original (pre-restructure) site lives untouched in the sibling
`worldhenry.github.io/` folder. All active work is in this folder.*
