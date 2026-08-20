#!/usr/bin/env python3
"""Reorganise source/ from the WordPress layout into a page-based layout.

Each page and each post becomes a folder containing its own HTML and the
resources (images) that page actually uses:

    source/
      brand/                         shared brand assets (logo, QR, hero, ack)
      pages/
        news/index.html  page-2.html
        news/img/                    featured images shown on the listing
        events/index.html
        events/img/
        members/index.html
        constitution/index.html
        contact/index.html
        contact/img/
      posts/<YYYY-MM-DD>-<slug>/
        index.html
        img/                         every image the article uses (+ cover.*)
      resources.md                   which page/post includes which resources
"""
import glob
import os
import re
import shutil
import sys
import urllib.parse
from html import unescape

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(SRC, "source")
SITE = "https://www.mcuaa.org.au"

BRAND = {
    "https://www.mcuaa.org.au/wp-content/uploads/2025/09/mcuaaLogo-scaled-40x40.png": "logo-40.png",
    "https://www.mcuaa.org.au/wp-content/uploads/2025/09/mcuaaLogo-1.png": "logo.png",
    "https://www.mcuaa.org.au/wp-content/uploads/2025/09/mcuaaQR_hori.png": "wechat-qr.png",
    "https://www.mcuaa.org.au/wp-content/uploads/2025/12/MCUAA-Acknowledgement.png": "acknowledgement.png",
    "https://www.mcuaa.org.au/wp-content/uploads/2026/04/homePic-2048x852.jpg": "hero-home.jpg",
}


def clean_url(value):
    m = re.search(r"https?://\S+", value or "")
    if m:
        return m.group(0).rstrip('"\'')
    return (value or "").strip()


def uploads_rel(url):
    rel = url.replace(SITE + "/", "").replace("https://www.mcuaa.org.au/", "")
    if not rel.startswith("wp-content/uploads/"):
        return None
    return rel


def wp_src(url):
    rel = uploads_rel(url)
    return os.path.join(SRC, rel) if rel else None


def base_name(url):
    return url.rsplit("/", 1)[-1]


def copy_file(url, dest_dir, dest_name=None):
    src = wp_src(url)
    if not src or not os.path.exists(src):
        print("  !! missing:", url)
        return False
    dest = os.path.join(dest_dir, dest_name or base_name(url))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        shutil.copy2(src, dest)
    return True


def find_card_images(html, img_map):
    """Return {remote url: local src} for every uploads image in the page."""
    out = {}
    for m in re.finditer(r"<img[^>]*>", html):
        tag = m.group(0)
        sm = re.search(r'\bsrc="([^"]+)"', tag)
        if not sm:
            continue
        url = clean_url(sm.group(1))
        if not uploads_rel(url):
            continue
        local = img_map(url)
        if local:
            out[url] = local
    return out


def rewrite_img_tags(html, mapper):
    """Rewrite every <img> whose src is an uploads URL via mapper(url)->local."""

    def sub(m):
        tag = m.group(0)
        sm = re.search(r'\bsrc="([^"]+)"', tag)
        if not sm:
            return tag
        url = clean_url(sm.group(1))
        if not uploads_rel(url):
            return tag
        local = mapper(url)
        if not local:
            return tag
        am = re.search(r'\balt="([^"]*)"', tag)
        alt = ' alt="{}"'.format(am.group(1)) if am else ""
        return '<img src="{}"{}>'.format(local, alt)

    return re.sub(r"<img[^>]*>", sub, html)


def extract_excerpts():
    out = {}
    for page in ("news/index.html", "news/page/2/index.html"):
        src = open(os.path.join(SRC, page), encoding="utf-8", errors="ignore").read()
        for art in re.findall(r"<article[^>]*>(.*?)</article>", src, re.S):
            href_m = re.search(r'href="(https://www\.mcuaa\.org\.au/20\d\d/\d\d/\d\d/[^"]+)/"', art)
            if not href_m:
                continue
            img_m = re.search(r'<img[^>]+src="([^"]+)"', art)
            out[href_m.group(1)] = (art, img_m.group(1) if img_m else "")
    return out


def entry_imgs(src):
    """Uploads image URLs inside the article content (not the WP chrome)."""
    i = src.find('<div class="entry-content clear')
    j = src.find("</article>", i)
    body = src[i:j] if 0 <= i < j else src
    urls = [clean_url(u) for u in re.findall(r'<img[^>]+src="([^"]+)"', body)]
    return [u for u in urls if "wp-content/uploads" in u]


def main():
    if not os.path.exists(os.path.join(SRC, "wp-content", "uploads")):
        print("source/ is already page-based; nothing to do")
        return

    listings = extract_excerpts()
    os.makedirs(SRC, exist_ok=True)

    # ------------------------------------------------------------------ brand
    brand_dir = os.path.join(SRC, "brand")
    for url, name in BRAND.items():
        copy_file(url, brand_dir, name)

    # ------------------------------------------------------------------ posts
    post_files = (glob.glob(os.path.join(SRC, "2025", "**", "index.html"), recursive=True)
                  + glob.glob(os.path.join(SRC, "2026", "**", "index.html"), recursive=True))
    post_display = {}  # old post URL -> relative path of its display image
    for path in sorted(post_files):
        src = open(path, encoding="utf-8", errors="ignore").read()
        y, m, d = os.path.relpath(path, SRC).split(os.sep)[:3]
        slug = os.path.basename(os.path.dirname(path))
        date = "{}-{:02d}-{:02d}".format(y, int(m), int(d))

        # old URL of this post (for the listing map)
        encoded = urllib.parse.quote("/{}/{}/{}/{}".format(y, m, d, slug), safe="/")
        card_img = listings.get(SITE + encoded, (None, ""))[1] or ""

        body_imgs = entry_imgs(src)
        body_imgs = list(dict.fromkeys(body_imgs))  # drop duplicate references

        folder = os.path.join(SRC, "posts", "{}-{}".format(date, slug))
        img_dir = os.path.join(folder, "img")
        os.makedirs(img_dir, exist_ok=True)

        def mapper(url):
            if url in BRAND:
                return "../../brand/" + BRAND[url]
            return "img/" + base_name(url)

        # copy every image the article uses (deduped)
        for url in body_imgs:
            if url not in BRAND:
                copy_file(url, img_dir)

        # cover.* only when the article has no inline image (featured from the
        # listing card); otherwise the first body image serves as the cover
        display = ""
        if body_imgs:
            display = "img/" + base_name(body_imgs[0])
        elif card_img and uploads_rel(card_img):
            ext = os.path.splitext(base_name(card_img))[1] or ".jpg"
            copy_file(card_img, img_dir, "cover" + ext)
            display = "img/cover" + ext
        post_display[SITE + encoded] = display

        html = rewrite_img_tags(src, mapper)
        dest = os.path.join(folder, "index.html")
        with open(dest, "w", encoding="utf-8") as f:
            f.write(html)
        print("post:", os.path.relpath(folder, SRC))

    # ------------------------------------------------------------------ pages
    # card image URL -> relative path to that post's display image (no copies)
    card_to_display = {}
    for post_url, display in post_display.items():
        if not display:
            continue
        folder = "-".join(post_url.replace(SITE + "/", "").split("/"))
        card_img = listings.get(post_url, (None, ""))[1] or ""
        if card_img:
            card_to_display[card_img] = "../../posts/{}/{}".format(folder, display)

    page_specs = [
        ("news/index.html", "pages/news/index.html"),
        ("news/page/2/index.html", "pages/news/page-2.html"),
        ("events/index.html", "pages/events/index.html"),
        ("members/index.html", "pages/members/index.html"),
        ("constitution/index.html", "pages/constitution/index.html"),
        ("contact/index.html", "pages/contact/index.html"),
    ]
    for old, new in page_specs:
        old_path = os.path.join(SRC, old)
        if not os.path.exists(old_path):
            continue
        src = open(old_path, encoding="utf-8", errors="ignore").read()

        def mapper(url):
            if url in BRAND:
                return "../../brand/" + BRAND[url]
            return card_to_display.get(url)

        html = rewrite_img_tags(src, mapper)
        dest = os.path.join(SRC, new)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(html)
        print("page:", new)

    # ---------------------------------------------------------------- cleanup
    for entry in ("2025", "2026", "news", "events", "members", "constitution",
                  "contact", "wp-content"):
        p = os.path.join(SRC, entry)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
    for f in ("CNAME",):
        p = os.path.join(SRC, f)
        if os.path.exists(p):
            os.remove(p)

    write_resources_md()
    print("\nDone. source/ is now page-based.")


def write_resources_md():
    lines = ["# source/ — resources by page", ""]
    lines.append("Each page and article folder is self-contained: its HTML plus the")
    lines.append("images it uses. `brand/` holds shared assets referenced by every")
    lines.append("page template (logo, QR code, hero, acknowledgement).")
    lines.append("")

    lines.append("## brand/ (shared)")
    for name in sorted(os.listdir(os.path.join(SRC, "brand"))):
        lines.append("- {0}  (used by the site templates on every page)".format(name))
    lines.append("")

    pages_dir = os.path.join(SRC, "pages")
    for page in sorted(os.listdir(pages_dir)):
        pdir = os.path.join(pages_dir, page)
        if not os.path.isdir(pdir):
            continue
        files = [f for f in os.listdir(pdir) if f.endswith(".html")]
        lines.append("## pages/{0}".format(page))
        for f in files:
            lines.append("- {0}".format(f))
        lines.append("")
    lines.append("Listing pages (news/events) reference post images directly via")
    lines.append("`../../posts/<date>-<slug>/img/...` — no duplicate copies.")
    lines.append("")

    lines.append("## posts/ (one folder per article)")
    posts_dir = os.path.join(SRC, "posts")
    for folder in sorted(os.listdir(posts_dir)):
        fdir = os.path.join(posts_dir, folder)
        if not os.path.isdir(fdir):
            continue
        imgs = sorted(os.listdir(os.path.join(fdir, "img"))) if os.path.isdir(os.path.join(fdir, "img")) else []
        lines.append("- **{0}** — index.html".format(folder))
        for i in imgs:
            lines.append("    - img/{0}".format(i))

    with open(os.path.join(SRC, "resources.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
