#!/usr/bin/env python3
"""MCUAA static site generator — Material 3 redesign.

Source (legacy WordPress export) lives in source/, the generated website is
written to the repository root (deployable to GitHub Pages).

Generated structure (flat & concise):

    index.html  news.html  events.html  members.html  constitution.html
    contact.html  404.html
    articles/<slug>.html
    assets/css/site.css  assets/js/site.js
    assets/img/{logo-40.png, logo.png, hero-home.jpg, wechat-qr.png,
                acknowledgement.png}
    assets/img/posts/<slug>-cover.jpg  <slug>-cover-640.jpg  <slug>-<img>.*
    sitemap.xml  robots.txt  CNAME  .nojekyll  README.md

Set KEEP_LEGACY_REDIRECTS = True to also emit pages at the old WordPress URLs
(2025/05/24/<slug>/ ...) that redirect to the new structure.
"""
import glob
import os
import re
import shutil
import urllib.parse
from html import unescape
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
OUT = ROOT
SITE = "https://www.mcuaa.org.au"
KEEP_LEGACY_REDIRECTS = False

UPLOADS = os.path.join(SRC, "wp-content", "uploads")

# ---------------------------------------------------------------------------
# Image registry
# ---------------------------------------------------------------------------

# brand file in source/brand/ -> target under OUT/assets/img
FIXED_IMAGES = [
    ("logo-40.png", "assets/img/logo-40.png"),
    ("logo.png", "assets/img/logo.png"),
    ("wechat-qr.png", "assets/img/wechat-qr.png"),
    ("acknowledgement.png", "assets/img/acknowledgement.png"),
    ("hero-home.jpg", "assets/img/hero-home.jpg"),
]

IMG_TARGETS = {}  # local source src (within a post folder) -> target path


def clean_url(value):
    """Extract the first clean http(s) URL from a (possibly malformed) attribute."""
    m = re.search(r"https?://\S+", value or "")
    if m:
        return m.group(0).rstrip('"\'')
    return (value or "").strip()


def copy_file(src_abs, target):
    """Copy an absolute source file into OUT. Returns (target, src)."""
    if not src_abs or not os.path.exists(src_abs):
        print("  !! missing:", src_abs)
        return None, None
    dest = os.path.join(OUT, target)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        shutil.copy2(src_abs, dest)
    return target, src_abs


def make_thumb(src, target, width=640, quality=82):
    """Generate a width-capped JPEG thumbnail with PIL (falls back to a copy)."""
    dest = os.path.join(OUT, target)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        return target
    try:
        from PIL import Image
        im = Image.open(src)
        im.thumbnail((width, width))
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            im = im.convert("RGBA")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        im.save(dest, "JPEG", quality=quality, optimize=True)
    except Exception as e:
        print("  !! thumb fallback:", target, e)
        shutil.copy2(src, dest)
    return target


def build_image_registry(posts):
    """Assign every source image to its flat new location (per post)."""
    for brand_file, target in FIXED_IMAGES:
        src = os.path.join(SRC, "brand", brand_file)
        p_ = {"cover_src": src if os.path.exists(src) else None}
        globals().setdefault("_BRAND", {})[target] = p_["cover_src"]

    for p in posts:
        img_dir = os.path.join(SRC, "posts", p["folder"], "img")

        # cover: explicit cover.* file, else first body image
        cover = glob.glob(os.path.join(img_dir, "cover.*"))
        if not cover:
            cover = [os.path.join(img_dir, os.path.basename(src)) for src in p["body_imgs"]] or []
        if cover and os.path.exists(cover[0]):
            ext = os.path.splitext(cover[0])[1] or ".jpg"
            p["cover_src"] = cover[0]
            p["cover"] = os.path.join("assets", "img", "posts", p["slug"] + "-cover" + ext)
            p["thumb"] = os.path.join("assets", "img", "posts", p["slug"] + "-cover-640.jpg")
        else:
            p["cover"] = p["cover_src"] = p["thumb"] = None

        # inline images, flat with <slug>- prefix and collision suffixes
        used = set()
        for src in p["body_imgs"]:
            name = os.path.basename(src)
            target = os.path.join("assets", "img", "posts", p["slug"] + "-" + name)
            n = 2
            while target in used:
                target = os.path.join("assets", "img", "posts",
                                      "{}-{}-{}".format(p["slug"], n, name))
                n += 1
            used.add(target)
            p["img_map"][src] = target


def copy_registered_images(posts):
    for brand_file, target in FIXED_IMAGES:
        copy_file(os.path.join(SRC, "brand", brand_file), target)
    for p in posts:
        img_dir = os.path.join(SRC, "posts", p["folder"], "img")
        for src, target in p["img_map"].items():
            copy_file(os.path.join(img_dir, os.path.basename(src)), target)
        if p["cover_src"]:
            copy_file(p["cover_src"], p["cover"])
            make_thumb(p["cover_src"], p["thumb"])


# ---------------------------------------------------------------------------
# HTML sanitizer for post bodies
# ---------------------------------------------------------------------------

ALLOWED_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li",
    "a", "strong", "b", "em", "i", "img", "figure", "figcaption",
    "blockquote", "table", "thead", "tbody", "tr", "th", "td",
    "hr", "br", "sub", "sup", "pre", "code", "div", "span",
}
TRANS_BLOCK = {"div"}
INLINE = {"span", "sub", "sup", "code"}
P_CLOSERS = {"figure", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
             "blockquote", "table", "p", "hr", "div", "li", "pre"}


class BodySanitizer(HTMLParser):
    def __init__(self, img_map):
        super().__init__(convert_charrefs=True)
        self.img_map = img_map
        self.out = []
        self.stack = []
        self.skip = 0

    def _close_to(self, tag):
        while self.stack:
            top = self.stack.pop()
            self.out.append("</{}>".format(top))
            if top == tag:
                return

    def _close_p(self):
        if self.stack and self.stack[-1] == "p":
            self.stack.pop()
            self.out.append("</p>")

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
            return
        if tag not in ALLOWED_TAGS:
            return
        if tag in TRANS_BLOCK or tag in INLINE:
            self.stack.append(tag)
            return
        if tag in P_CLOSERS:
            self._close_p()
        d = dict(attrs)
        if tag == "img":
            src = clean_url(d.get("src", ""))
            target = self.img_map.get(src)
            if not target:
                return
            extra = ""
            if d.get("width"):
                extra += ' width="{}"'.format(d["width"])
            if d.get("height"):
                extra += ' height="{}"'.format(d["height"])
            alt = d.get("alt", "")
            if alt:
                extra += ' alt="{}"'.format(alt.replace('"', "&quot;"))
            self.out.append('<img src="__ROOT__{}"{} loading="lazy">'.format(target, extra))
            return
        if tag == "a":
            href = d.get("href", "")
            if href.startswith(SITE):
                href = "_ROOTLINK_" + href[len(SITE):]
            self.out.append('<a href="{}">'.format(href))
            self.stack.append(tag)
            return
        if tag in ("th", "td"):
            extra = ""
            if d.get("colspan"):
                extra += ' colspan="{}"'.format(d["colspan"])
            if d.get("rowspan"):
                extra += ' rowspan="{}"'.format(d["rowspan"])
            self.out.append("<{}{}>".format(tag, extra))
            self.stack.append(tag)
            return
        if tag == "figure":
            cls = d.get("class", "").split()
            keep = [c for c in cls if c in ("alignleft", "alignright", "aligncenter")]
            self.out.append('<figure{}>'.format(
                ' class="{}"'.format(keep[0]) if keep else ""))
            self.stack.append(tag)
            return
        if tag == "p":
            st = d.get("style", "")
            m = re.search(r"text-align\s*:\s*(center|left|right)", st)
            self.out.append('<p class="ta-{}">'.format(m.group(1)) if m else "<p>")
            self.stack.append(tag)
            return
        self.out.append("<{}>".format(tag))
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
            return
        if tag not in ALLOWED_TAGS:
            return
        if tag in TRANS_BLOCK or tag in INLINE:
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
            return
        if self.stack and self.stack[-1] == tag:
            self.out.append("</{}>".format(tag))
            self.stack.pop()
        elif tag in self.stack:
            self._close_to(tag)

    def handle_data(self, data):
        if self.skip:
            return
        self.out.append(re.sub(r"[ \t\r\n]+", " ", data))


def sanitize_body(src_html, root, img_map):
    p = BodySanitizer(img_map)
    p.feed(src_html)
    p.close()
    html = "".join(p.out)
    html = html.replace("__ROOT__", root)
    html = html.replace("_ROOTLINK_", root)
    html = re.sub(r"<strong>\s*</strong>", "", html)
    html = re.sub(r"<em>\s*</em>", "", html)
    html = re.sub(r"<span>\s*</span>", "", html)
    html = re.sub(r"<p class=\"ta-\w+\">\s*</p>", "", html)
    html = re.sub(r"<p>\s*</p>", "", html)
    html = re.sub(r"\n\s*\n+", "\n", html)
    return html.strip()


# ---------------------------------------------------------------------------
# Source extraction
# ---------------------------------------------------------------------------

def extract_post(path):
    """Read source/posts/<date>-<slug>/index.html."""
    folder = os.path.basename(os.path.dirname(path))
    m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", folder)
    if not m:
        return None
    date_iso, slug = m.group(1), m.group(2)

    src = open(path, encoding="utf-8", errors="ignore").read()
    title_m = re.search(r"<title>(.*?)</title>", src)
    title = unescape(title_m.group(1)) if title_m else ""
    title = re.sub(r"\s*[–—|-]\s*MCUAA\s*$", "", title).strip()

    i = src.find('<div class="entry-content clear')
    j = src.find("</article>", i)
    if i < 0 or j < 0:
        return None
    body_src = src[i:j]

    # images are referenced locally as img/<file> within the post folder
    body_imgs = [u for u in re.findall(r'<img[^>]+src="(img/[^" ]+)"', body_src)]
    body_imgs = list(dict.fromkeys(body_imgs))

    return {"path": path, "title": title, "date": date_iso,
            "slug": slug, "folder": folder,
            "body_src": body_src, "body_imgs": body_imgs,
            "img_map": {}}  # local src -> generated target


def extract_listings():
    """Map old post URL -> (excerpt, card image src) from the news listing pages."""
    out = {}
    for page in ("pages/news/index.html", "pages/news/page-2.html"):
        src = open(os.path.join(SRC, page), encoding="utf-8", errors="ignore").read()
        for art in re.findall(r"<article[^>]*>(.*?)</article>", src, re.S):
            href_m = re.search(r'href="(https://www\.mcuaa\.org\.au/20\d\d/\d\d/\d\d/[^"]+)/"', art)
            if not href_m:
                continue
            url = href_m.group(1)
            ex = ""
            em = re.search(r'<p[^>]*>(.*?)</p>', art, re.S)
            if em:
                ex = re.sub(r"<[^>]+>", "", em.group(1))
                ex = unescape(ex).strip()
            img = ""
            im = re.search(r'<img[^>]+src="([^"]+)"', art)
            if im:
                img = clean_url(im.group(1))
            out[url] = (ex, img)
    return out


def parse_members():
    src = open(os.path.join(SRC, "pages", "members", "index.html"), encoding="utf-8", errors="ignore").read()
    i = src.find('<div class="entry-content clear')
    j = src.find("</article>", i)
    block = src[i:j]
    groups = []
    current = None
    for m in re.finditer(r"<h2[^>]*>(.*?)</h2>|<p[^>]*>(.*?)</p>", block, re.S):
        if m.group(1):
            current = {"title": unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip(), "items": []}
            groups.append(current)
        elif m.group(2):
            if current is None:
                continue
            text = unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
            text = re.sub(r"^\d+\.\s*", "", text).strip()
            if text:
                current["items"].append(text)
    return groups


def parse_constitution():
    src = open(os.path.join(SRC, "pages", "constitution", "index.html"), encoding="utf-8", errors="ignore").read()
    i = src.find('<div class="entry-content clear')
    j = src.find("</article>", i)
    block = src[i:j]
    sections = []
    num = 0
    title = ""
    blocks = []
    for m in re.finditer(r"<(h2|h3|p|ul)[^>]*>(.*?)</\1>", block, re.S):
        tag, inner = m.group(1), m.group(2)
        text = unescape(re.sub(r"<[^>]+>", " ", inner))
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        if tag == "h2" and "章程" in text:
            continue
        if tag == "p" and re.match(r"^<strong>", inner.strip()):
            strong_text = re.sub(r"<[^>]+>", "", inner).strip()
            m2 = re.match(r"^(\d+)\s*[\.、]?\s*(.*)$", strong_text)
            if m2 and m2.group(2):
                if num:
                    sections.append({"num": num, "title": title, "blocks": blocks})
                num = int(m2.group(1))
                title = m2.group(2).strip()
                blocks = []
                continue
        if tag == "ul":
            items = re.findall(r"<li[^>]*>(.*?)</li>", inner, re.S)
            blocks.append(("ul", [re.sub(r"<[^>]+>", " ", it).strip() for it in items]))
        elif tag == "p":
            if re.match(r"^<strong>", inner.strip()):
                blocks.append(("sub", re.sub(r"<[^>]+>", "", inner).strip()))
            else:
                blocks.append(("p", text))
    if num:
        sections.append({"num": num, "title": title, "blocks": blocks})
    return sections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_date_cn(iso):
    y, m, d = iso.split("-")
    return "{}年{}月{}日".format(int(y), int(m), int(d))


def rel_prefix(out_path):
    rel = os.path.relpath(out_path, OUT)
    depth = len(os.path.dirname(rel).split(os.sep)) if os.path.dirname(rel) else 0
    return "../" * depth


def href_to(out_path, target_rel):
    """Relative URL from a generated file to a file/dir (target_rel under OUT)."""
    rel = os.path.relpath(os.path.join(OUT, target_rel), os.path.dirname(out_path))
    if not os.path.splitext(target_rel)[1]:
        rel += "/"
    return rel


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", os.path.relpath(path, OUT))


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

NAV = [("News", "news.html"), ("Events", "events.html"), ("Members", "members.html"),
       ("Constitution", "constitution.html"), ("Contact", "contact.html")]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

ICONS = {
    "mail": '<svg viewBox="0 0 24 24"><path d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 4-8 5-8-5V6l8 5 8-5v2z"/></svg>',
    "wechat": '<svg viewBox="0 0 24 24"><path d="M8.7 4C5.5 4 3 6.2 3 8.9c0 1.6.9 3 2.3 3.9l-.6 1.8 2.1-1.1c.6.2 1.2.2 1.8.2h.4a4.7 4.7 0 0 1-.3-1.6c0-2.8 2.8-5 6.1-5h.4C14.7 5.4 12 4 8.7 4zM6.4 8a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8zm4.8 0a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8zM20.9 13.2c0-2.4-2.4-4.3-5.3-4.3s-5.3 1.9-5.3 4.3 2.4 4.3 5.3 4.3c.6 0 1.2-.1 1.8-.3l1.8 1-.5-1.6c1.4-.9 2.2-2 2.2-3.4zm-7.1-.9a.8.8 0 1 1 0-1.6.8.8 0 0 1 0 1.6zm3.6 0a.8.8 0 1 1 0-1.6.8.8 0 0 1 0 1.6z"/></svg>',
}


def page_header(root, title, desc, active, overlay=False, canonical=None):
    if canonical is None:
        canonical = SITE + ("/" if active in (None, "Home") else "/" + active.lower() + ".html")
    home = root + "index.html"
    links = []
    for name, href in NAV:
        cur = ' class="nav-item active"' if name == active else ' class="nav-item"'
        links.append('<a href="{root}{href}"{cur}>{name}</a>'.format(root=root, href=href, cur=cur, name=name))

    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="icon" href="{root}assets/img/logo-40.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<script>
/* Non-blocking web font loading: pages render instantly with system fonts
   even when offline; Noto Serif SC upgrades in when online. */
(function () {{
  var l = document.createElement("link");
  l.rel = "stylesheet";
  l.href = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap";
  l.media = "print";
  l.onload = function () {{ l.media = "all"; }};
  document.head.appendChild(l);
}})();
</script>
<link rel="stylesheet" href="{root}assets/css/site.css">
<link rel="canonical" href="{canonical}">
</head>
<body>
<header class="nav" id="nav">
  <div class="nav-inner">
    <a class="brand" href="{home}">
      <span class="brand-logo-wrap"><img class="brand-logo" src="{root}assets/img/logo.png" alt="MCUAA"></span>
    </a>
    <nav class="nav-links" id="navLinks">
      {links}
    </nav>
    <button class="nav-toggle" id="navToggle" aria-label="菜单" aria-expanded="false">&#9776;</button>
  </div>
</header>
<main>
""".format(title=title, desc=desc, root=root, home=home, canonical=canonical,
           links="\n      ".join(links))


def page_footer(root):
    home = root + "index.html"
    return """
</main>
<footer class="footer">
  <div class="footer-inner">
    <div>
      <span class="footer-logo-wrap"><img class="footer-logo" src="{root}assets/img/logo.png" alt="MCUAA"></span>
      <p class="footer-motto">交流联谊 · 合作共赢 · 共同进步</p>
    </div>
    <div class="footer-links">
      <a href="{root}news.html">新闻 | NEWS</a>
      <a href="{root}events.html">活动 | EVENTS</a>
      <a href="{root}members.html">成员 | MEMBERS</a>
      <a href="{root}constitution.html">规章 | Regulation</a>
      <a href="{root}contact.html">联系 | Contact</a>
    </div>
    <p class="footer-copy">Copyright &copy; 2025&ndash;2026 墨尔本中国高校校友会联盟 &middot; MCUAA</p>
    <p class="footer-note">Melbourne CUAA Alliance Inc.</p>
  </div>
</footer>
<script src="{root}assets/js/site.js"></script>
</body>
</html>
""".format(root=root, home=home)


def render_page(root, active, title, desc, body_html, overlay=False, canonical=None):
    return (page_header(root, title, desc, active, overlay, canonical)
            + body_html
            + page_footer(root))


def post_card(out_path, p, with_date=False):
    """Editorial post card (shared by home preview + news listing)."""
    url = href_to(out_path, p["file_rel"])
    date_html = '<span class="post-date">{}</span>'.format(fmt_date_cn(p["date"])) if with_date else ""
    return """<article class="post-card reveal">
  <a class="post-card-link" href="{url}">
    <div class="post-thumb-wrap"><img class="post-thumb" src="{root}{thumb}" alt="" loading="lazy"></div>
    <div class="post-card-body">
      {date}
      <h3 class="post-card-title">{title}</h3>
      <p class="post-excerpt">{excerpt}</p>
      <span class="post-more">阅读全文 &rsaquo;</span>
    </div>
  </a>
</article>""".format(url=url, root=rel_prefix(out_path), thumb=p["thumb"],
                   date=date_html, title=p["title"], excerpt=p["excerpt"])


def event_row(out_path, p):
    """Editorial event row (shared by home preview + events listing)."""
    y, m, d = p["date"].split("-")
    url = href_to(out_path, p["file_rel"])
    return """<a class="event-row reveal" href="{url}">
          <span class="event-date"><span class="day">{day}</span><span class="mon">{mon}</span></span>
          <span class="event-body">
            <span class="title">{title}</span>
            <span class="excerpt">{excerpt}</span>
          </span>
          <span class="event-arrow">&rsaquo;</span>
        </a>""".format(url=url, day=int(d), mon=MONTHS[int(m) - 1], title=p["title"],
                       excerpt=p["excerpt"])


def count_faces(image_path):
    """Detect faces with OpenCV Haar cascades; None if OpenCV unavailable."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    data = np.fromfile(image_path, dtype=np.uint8)
    if data.size == 0:
        return 0
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        return 0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    cc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cc.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(28, 28))
    return len(faces)


def select_gallery_photos(posts, target=20, per_post=3):
    """Scan all photos in the repo's post folders; several photos per post allowed."""
    exclude = re.compile(r"screen|poster|海报|banner|Picture|\b2\.png$|\b1_77868", re.I)
    lecture = re.compile(r"讲座|分享会|沙龙|论坛", re.I)
    picked = []
    events = [p for p in posts if p["category"] == "活动"]
    for p in events:
        if len(picked) >= target:
            break
        if lecture.search(p["title"]) or lecture.search(p["body_src"]):
            continue
        img_dir = os.path.join(SRC, "posts", p["folder"], "img")
        if not os.path.isdir(img_dir):
            continue
        cands = []
        for name in sorted(os.listdir(img_dir)):
            base = name.lower()
            if exclude.search(base) or not base.endswith((".jpg", ".jpeg")):
                continue
            abs_src = os.path.join(img_dir, name)
            target_rel = p["img_map"].get("img/" + name)
            if not target_rel:
                cand = os.path.join("assets", "img", "posts", p["slug"] + "-" + name)
                if os.path.exists(os.path.join(OUT, cand)):
                    target_rel = cand
                else:
                    continue
            cands.append((target_rel, abs_src, name))
        if not cands:
            continue
        scored = []
        for rel, abs_src, name in cands:
            n = count_faces(abs_src) or 0
            scored.append((n, rel, name))
        scored.sort(key=lambda c: c[0], reverse=True)
        for n, rel, name in scored[:per_post]:
            if len(picked) >= target:
                break
            picked.append({"img": rel, "title": p["title"], "faces": n})
    return picked[:target]


def build_home(posts):
    out_path = os.path.join(OUT, "index.html")
    recent = [post_card(out_path, p) for p in posts[:8]]
    recent = "\n      ".join(recent)

    gallery = select_gallery_photos(posts, 20)
    gallery_items = []
    for g in gallery:
        gallery_items.append("""<figure class="gallery-item" data-caption="{title}">
          <img src="{root}{img}" alt="{title}" loading="lazy">
          <figcaption>{title}</figcaption>
        </figure>""".format(root="", img=g["img"], title=g["title"]))
    gallery_html = "\n      ".join(gallery_items)

    missions = [
        ("在尊重每一个成员校友会独立性与自主权的基础上，推动资源共享与联合举办活动，提升整体影响力；",
         "Promoting resource sharing and joint activities to enhance overall influence, while respecting the independence and autonomy of each member alumni association;"),
        ("倡导健康积极的生活方式，丰富校友的业余生活，并为校友的职业发展与专业成长提供支持；",
         "Advocating for healthy and active lifestyles, enriching the social life of alumni, and providing support for alumni\u2019s career development and professional growth;"),
        ("分享各校友会运作的最佳实践经验，提升组织能力，同时协助不活跃或规模较小的校友会逐步成长；",
         "Sharing best practices in the operation of various alumni associations to improve organisational capabilities, while also assisting inactive or smaller alumni associations to gradually grow;"),
        ("弘扬中华文化，增强华人社区的凝聚力，促进跨文化理解与多元融合；",
         "Promoting Chinese culture, strengthening the cohesion of the Chinese community, and fostering cross-cultural understanding and multi-diversity integration;"),
        ("推动中澳两国在科技、教育、文化等领域的交流与合作。",
         "Promoting exchange and cooperation between China and Australia in fields such as science, technology, education, and culture."),
    ]
    commits = []
    for i, (cn, en) in enumerate(missions, 1):
        commits.append("""<article class="commit-card" tabindex="0">
          <div class="commit-card-inner">
            <div class="commit-card-face commit-card-front">
              <span class="commit-card-num">{i:02d}</span>
              <p class="commit-card-cn">{cn}</p>
            </div>
            <div class="commit-card-face commit-card-back">
              <span class="commit-card-num">{i:02d}</span>
              <p class="commit-card-en">{en}</p>
            </div>
          </div>
        </article>""".format(i=i, cn=cn, en=en))
    commits = "\n      ".join(commits)

    body = """
<section class="hero">
  <div class="hero-inner">
    <h1 class="hero-title">墨尔本中国高校校友会联盟</h1>
    <p class="hero-subtitle">Melbourne CUAA Alliance Inc &ndash; MCUAA</p>
  </div>
</section>

<section class="section section-home">
  <div class="section-inner-wide">
    <div class="intro-side">
      <div class="org-block">
        <p class="org-name">MCUAA</p>
        <p class="org-en">Melbourne CUAA Alliance Inc.</p>
        <p class="org-note">CUAA stands for Chinese University Alumni Associations</p>
        <img class="org-logo" src="assets/img/logo.png" alt="MCUAA 墨尔本中国高校校友会联盟">
      </div>
      <div>
        <p class="about-text">墨尔本中国高校校友会联盟（MCUAA）是一个非营利、非政治、非宗教组织，于 2025 年 4 月在澳大利亚正式注册成立。联盟的宗旨是：为墨尔本各中国高校校友会之间建立一个交流联谊、合作共赢、共同进步的平台。</p>
        <p class="about-text">Melbourne CUAA Alliance Inc. (MCUAA) is a non-profit, non-political, and non-religious organization. Its mission is to establish a platform for exchange, fellowship, win-win cooperation, and mutual progress among the Chinese university alumni associations in Melbourne.</p>
      </div>
    </div>
    <div class="home-spacer"></div>
    <div class="motto-band">
      <span class="motto-line"></span>
      <blockquote class="motto-text">交流联谊，合作共赢，共同进步</blockquote>
      <span class="motto-line motto-line--r"></span>
    </div>
    <div class="home-spacer"></div>
    <div class="commit-wrap">
      <h2 class="commit-title">
        <span class="commit-title-lines">
          <span>联盟致力于：</span>
          <span class="commit-title-en">MCUAA is committed to:</span>
        </span>
      </h2>
      <div class="commit-cards">
        {commits}
      </div>
    </div>
  </div>
</section>

<section class="section section-gray">
  <div class="section-inner-wide">
    <span class="kicker">Gallery &middot; 精彩瞬间</span>
    <h2 class="section-title">活动精彩瞬间</h2>
    <p class="section-desc">来自各成员校友会的活动留影 &mdash; 点击照片查看大图</p>
    <div class="gallery-carousel" id="galleryCarousel">
      <div class="gallery-track" id="galleryTrack">
        {gallery}
      </div>
      <button class="gallery-arrow gallery-prev" id="galleryPrev" aria-label="上一张">&lsaquo;</button>
      <button class="gallery-arrow gallery-next" id="galleryNext" aria-label="下一张">&rsaquo;</button>
    </div>
    <div class="gallery-dots" id="galleryDots"></div>
  </div>
</section>

<section class="section section-gray">
  <div class="section-inner-wide">
    <span class="kicker">News &middot; 新闻动态</span>
    <h2 class="section-title">Recent News</h2>
    <p class="section-desc">来自各成员校友会的最新动态与活动报道</p>
    <div class="post-list">
      {recent}
    </div>
    <div class="cta-row">
      <a class="btn btn-primary" href="news.html">查看全部新闻 &rsaquo;</a>
    </div>
  </div>
</section>

<section class="ack">
  <img src="assets/img/acknowledgement.png" alt="Acknowledgement of Country">
  <p>MCUAA acknowledges the Wurundjeri People of the Kulin Nations as the Traditional Owners of the Country on which we live. We pay respect to their Elders past and present.</p>
</section>
""".format(commits=commits, recent=recent, gallery=gallery_html)
    html = render_page(rel_prefix(out_path), "Home", "首页 | Home - 墨尔本中国高校校友会联盟 MCUAA",
                       "墨尔本中国高校校友会联盟（MCUAA）官方主页：新闻动态、活动回顾、成员与章程。",
                       body)
    write(out_path, html)


def build_news(posts):
    out_path = os.path.join(OUT, "news.html")
    root = rel_prefix(out_path)
    cards = "\n      ".join(post_card(out_path, p, True) for p in posts)

    body = """
<section class="hero hero-small">
  <div class="hero-inner">
    <p class="hero-kicker">News &middot; 新闻动态</p>
    <h1 class="hero-title">新闻动态</h1>
    <p class="hero-subtitle">共 {n} 篇报道</p>
  </div>
</section>

<section class="section">
  <div class="section-inner-wide">
    <div class="post-list">
      {cards}
    </div>
  </div>
</section>
""".format(cards=cards, n=len(posts))
    html = render_page(root, "News", "新闻 | NEWS - 墨尔本中国高校校友会联盟 MCUAA",
                       "MCUAA 墨尔本中国高校校友会联盟新闻动态与活动报道。", body)
    write(out_path, html)


def build_events(posts):
    out_path = os.path.join(OUT, "events.html")
    root = rel_prefix(out_path)

    years = {}
    for p in posts:
        years.setdefault(p["date"][:4], []).append(p)

    groups = []
    for year in sorted(years, reverse=True):
        cards = "\n      ".join(post_card(out_path, p, True) for p in years[year])
        groups.append("""<h3 class="sub-title">{year} 年</h3>
    <div class="post-list">
      {cards}
    </div>""".format(year=year, cards=cards))
    groups_html = "\n\n    ".join(groups)

    body = """
<section class="hero hero-small">
  <div class="hero-inner">
    <p class="hero-kicker">Events &middot; 活动回顾</p>
    <h1 class="hero-title">活动回顾</h1>
    <p class="hero-subtitle">共 {n} 场活动</p>
  </div>
</section>

<section class="section">
  <div class="section-inner-wide">
    {groups}
  </div>
</section>
""".format(groups=groups_html, n=len(posts))
    html = render_page(root, "Events", "活动 | EVENTS - 墨尔本中国高校校友会联盟 MCUAA",
                       "MCUAA 墨尔本中国高校校友会联盟活动回顾：讲座、体育联谊、春节庆典等。", body)
    write(out_path, html)


def build_members():
    out_path = os.path.join(OUT, "members.html")
    root = rel_prefix(out_path)
    members = parse_members()
    groups = []
    for g in members:
        items = "\n          ".join("<li>{}</li>".format(name) for name in g["items"])
        groups.append("""<section class="member-group reveal">
        <h3 class="sub-title">{title} <span style="font-size:13px;color:var(--text-tertiary);letter-spacing:1px;font-family:var(--font-sans)">（{n} 个）</span></h3>
        <ol class="criteria-list">
          {items}
        </ol>
      </section>""".format(title=g["title"], n=len(g["items"]), items=items))
    groups = "\n    ".join(groups)

    body = """
<section class="hero hero-small">
  <div class="hero-inner">
    <p class="hero-kicker">Members &middot; 成员</p>
    <h1 class="hero-title">成员校友会</h1>
    <p class="hero-subtitle">理事单位 · 正式会员 · 观察会员</p>
  </div>
</section>

<section class="section">
  <div class="section-inner">
    <div class="member-groups">
      {groups}
    </div>
  </div>
</section>
""".format(groups=groups)
    html = render_page(root, "Members", "成员 | MEMBERS - 墨尔本中国高校校友会联盟 MCUAA",
                       "MCUAA 成员校友会名单：理事单位、正式会员与观察会员。", body)
    write(out_path, html)


def build_constitution():
    out_path = os.path.join(OUT, "constitution.html")
    root = rel_prefix(out_path)
    sections = parse_constitution()
    blocks_html = []
    for s in sections:
        blocks = []
        for kind, val in s["blocks"]:
            if kind == "p":
                blocks.append("<p class=\"doc-note\">{}</p>".format(val))
            elif kind == "sub":
                blocks.append("<p class=\"doc-sub\">{}</p>".format(val))
            elif kind == "ul":
                items = "".join("<li>{}</li>".format(it) for it in val)
                blocks.append("<ul class=\"doc-list-ul\">{}</ul>".format(items))
        blocks_html.append("""<p class="doc-head"><span class="doc-head-num">{num}</span>{title}</p>
      {blocks}""".format(num=s["num"], title=s["title"], blocks="\n      ".join(blocks)))
    doc = "\n\n    ".join(blocks_html)

    body = """
<section class="hero hero-small">
  <div class="hero-inner">
    <p class="hero-kicker">Constitution &middot; 章程</p>
    <h1 class="hero-title">Constitution</h1>
  </div>
</section>

<section class="section">
  <div class="section-inner-wide">
    <div class="constitution-doc">
      <h2 class="doc-main-title">墨尔本中国高校校友会联盟章程</h2>
      <p class="doc-main-sub">根据维多利亚州《2012年社团成立改革法案》制定</p>
      {doc}
    </div>
  </div>
</section>
""".format(doc=doc)
    html = render_page(root, "Constitution", "规章 | Regulation - 墨尔本中国高校校友会联盟 MCUAA",
                       "墨尔本中国高校校友会联盟章程，根据维多利亚州《2012年社团成立改革法案》制定。", body)
    write(out_path, html)


def build_contact():
    out_path = os.path.join(OUT, "contact.html")
    root = rel_prefix(out_path)
    body = """
<section class="hero hero-small">
  <div class="hero-inner">
    <p class="hero-kicker">Contact &middot; 联系</p>
    <h1 class="hero-title">联系我们</h1>
    <p class="hero-subtitle">欢迎通过邮件或微信公众平台与我们联系</p>
  </div>
</section>

<section class="section">
  <div class="section-inner-wide">
    <div class="contact-layout">
      <div class="contact-panel">
        <img src="{root}assets/img/logo.png" alt="MCUAA">
      </div>
      <div class="contact-info">
        <p class="contact-label"><strong>Email</strong> &nbsp;📧</p>
        <p class="contact-value"><a href="mailto:mcuaa2025@gmail.com">mcuaa2025@gmail.com</a></p>
        <a class="btn btn-primary contact-mail-btn" href="mailto:mcuaa2025@gmail.com">发送邮件 &rsaquo;</a>
        <hr class="contact-divider">
        <p class="contact-label"><strong>公众号</strong> &nbsp;💬</p>
        <img class="contact-qr" src="{root}assets/img/wechat-qr.png" alt="MCUAA 微信公众号二维码">
        <p class="contact-caption">扫码关注，获取最新活动与动态</p>
      </div>
    </div>
  </div>
</section>
""".format(root=root)
    html = render_page(root, "Contact", "联系 | Contact - 墨尔本中国高校校友会联盟 MCUAA",
                       "联系 MCUAA：mcuaa2025@gmail.com，微信公众平台。", body)
    write(out_path, html)


def build_article(p, prev_p, next_p):
    out_path = os.path.join(OUT, p["file_rel"])
    root = rel_prefix(out_path)
    body_html = sanitize_body(p["body_src"], root, p["img_map"])
    cover = ""
    if p["cover"]:
        cover = """<div class="post-cover">
        <img src="{root}{cover}" alt="{title}">
      </div>""".format(root=root, cover=p["cover"], title=p["title"])

    nav_html = ""
    if prev_p or next_p:
        cells = []
        if prev_p:
            url = href_to(out_path, prev_p["file_rel"])
            cells.append('<a href="{}"><div class="label">← 上一篇</div><div class="title">{}</div></a>'.format(url, prev_p["title"]))
        else:
            cells.append('<a style="visibility:hidden" aria-hidden="true"></a>')
        if next_p:
            url = href_to(out_path, next_p["file_rel"])
            cells.append('<a href="{}"><div class="label">下一篇 →</div><div class="title">{}</div></a>'.format(url, next_p["title"]))
        nav_html = '<nav class="post-nav">{}</nav>'.format("".join(cells))

    back = href_to(out_path, "news.html" if p["category"] == "新闻" else "events.html")
    back_label = "返回新闻列表" if p["category"] == "新闻" else "返回活动列表"

    body = """
<section class="hero hero-small">
  <div class="hero-inner">
    <p class="hero-kicker">{category} &middot; {date_cn}</p>
    <h1 class="hero-title">{title}</h1>
  </div>
</section>

<article class="post-page">
  {cover}
  <div class="post-content">
    {body}
  </div>
  {nav}
  <div class="post-back">
    <a class="btn btn-secondary" href="{back}">← {back_label}</a>
  </div>
</article>
""".format(category=p["category"], date_cn=fmt_date_cn(p["date"]),
           title=p["title"], cover=cover, body=body_html, nav=nav_html,
           back=back, back_label=back_label)
    html = render_page(root, "News" if p["category"] == "新闻" else "Events",
                       "{} - 墨尔本中国高校校友会联盟 MCUAA".format(p["title"]),
                       "{} — MCUAA 墨尔本中国高校校友会联盟。".format(p["excerpt"][:80]),
                       body, canonical=SITE + "/" + p["file_rel"].replace("\\", "/"))
    write(out_path, html)


def build_404():
    body = """
<section class="hero hero-small">
  <div class="hero-inner">
    <p class="hero-kicker">404 &middot; Not Found</p>
    <h1 class="hero-title">页面不存在</h1>
    <p class="hero-subtitle">您访问的页面可能已被移动或删除</p>
  </div>
</section>

<section class="section">
  <div class="section-inner narrow" style="text-align:center">
    <p class="about-text" style="margin-bottom:32px">请返回首页，或浏览最新新闻与活动。</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="index.html">返回首页 &rsaquo;</a>
      <a class="btn btn-secondary" href="news.html">浏览新闻</a>
    </div>
  </div>
</section>
"""
    html = render_page("", None, "页面不存在 - 墨尔本中国高校校友会联盟 MCUAA",
                       "404 — 页面不存在。", body)
    write(os.path.join(OUT, "404.html"), html)

def redirect_page(path, target):
    rel = os.path.relpath(os.path.join(OUT, target), os.path.dirname(path))
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0; url={}">
<title>Redirecting…</title>
</head>
<body><p>Moved to <a href="{}">{}</a>.</p></body>
</html>
""".format(rel, rel, rel)
    write(path, html)


def build_sitemap(posts):
    pages = [("", "2026-07-13"), ("news.html", "2026-07-13"), ("events.html", "2026-07-13"),
             ("members.html", "2026-07-13"), ("constitution.html", "2026-07-13"),
             ("contact.html", "2026-07-13")]
    urls = ["  <url>\n    <loc>{}/{}</loc>\n    <lastmod>{}</lastmod>\n  </url>".format(SITE, u, d)
            for u, d in pages]
    for p in posts:
        urls.append("  <url>\n    <loc>{}/{}</loc>\n    <lastmod>{}</lastmod>\n  </url>".format(
            SITE, p["file_rel"].replace("\\", "/"), p["date"]))
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{}
</urlset>
""".format("\n".join(urls))
    write(os.path.join(OUT, "sitemap.xml"), xml)


def main():
    # --- ensure page-based source layout (convert once from WP layout) -----
    if os.path.exists(os.path.join(SRC, "wp-content")):
        print("Converting source/ to page-based layout ...")
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "reorg_source", os.path.join(ROOT, "tools", "reorg_source.py"))
        reorg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reorg)
        reorg.main()

    # --- clean generated site (keep .git, source/, tools/, .gitignore) -----
    keep = {".git", "source", "tools", ".gitignore"}
    for entry in sorted(os.listdir(OUT)):
        if entry in keep:
            continue
        p = os.path.join(OUT, entry)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            os.remove(p)

    # static css/js
    os.makedirs(os.path.join(OUT, "assets", "css"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "assets", "js"), exist_ok=True)
    shutil.copy2(os.path.join(ROOT, "tools", "static", "css", "site.css"),
                 os.path.join(OUT, "assets", "css", "site.css"))
    shutil.copy2(os.path.join(ROOT, "tools", "static", "js", "site.js"),
                 os.path.join(OUT, "assets", "js", "site.js"))

    # --- extract posts -----------------------------------------------------
    post_files = glob.glob(os.path.join(SRC, "posts", "*", "index.html"))
    posts = []
    for f in sorted(post_files):
        p = extract_post(f)
        if p:
            posts.append(p)

    events_src = open(os.path.join(SRC, "pages", "events", "index.html"), encoding="utf-8", errors="ignore").read()
    event_urls = set()
    for href in re.findall(r'href="(https://www\.mcuaa\.org\.au/20\d\d/\d\d/\d\d/[^"]+)/"', events_src):
        event_urls.add(href)

    listings = extract_listings()

    for p in posts:
        encoded = urllib.parse.quote("/{}/{}/{}/{}".format(
            *p["date"].split("-"), p["slug"]), safe="/")
        p["category"] = "活动" if (SITE + encoded) in event_urls else "新闻"

        ex, feat = listings.get(SITE + encoded, ("", ""))
        p["excerpt"] = ex
        if not p["excerpt"]:
            t = re.search(r"<p[^>]*>(.*?)</p>", p["body_src"], re.S)
            if t:
                p["excerpt"] = unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip()[:160]

        p["file_rel"] = os.path.join("articles", p["slug"] + ".html")

    posts.sort(key=lambda p: p["date"], reverse=True)

    # --- images ------------------------------------------------------------
    build_image_registry(posts)
    copy_registered_images(posts)

    # --- pages -------------------------------------------------------------
    build_home(posts)
    build_news(posts)
    build_events([p for p in posts if p["category"] == "活动"])
    build_members()
    build_constitution()
    build_contact()
    build_404()

    # --- articles ----------------------------------------------------------
    n = len(posts)
    for i, p in enumerate(posts):
        prev_p = posts[i + 1] if i + 1 < n else None
        next_p = posts[i - 1] if i > 0 else None
        build_article(p, prev_p, next_p)

    # --- legacy redirects (optional) --------------------------------------
    if KEEP_LEGACY_REDIRECTS:
        for p in posts:
            y, m, d = p["date"].split("-")
            old = os.path.join(OUT, y, m, d, p["slug"], "index.html")
            redirect_page(old, p["file_rel"])
        redirect_page(os.path.join(OUT, "members-live", "index.html"), "members.html")
        redirect_page(os.path.join(OUT, "category", "news", "index.html"), "news.html")
        redirect_page(os.path.join(OUT, "category", "events", "index.html"), "events.html")
        redirect_page(os.path.join(OUT, "category", "uncategorized", "index.html"), "news.html")
        redirect_page(os.path.join(OUT, "author", "mcuaa", "index.html"), "news.html")

    # --- meta files --------------------------------------------------------
    build_sitemap(posts)
    with open(os.path.join(OUT, "robots.txt"), "w") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: {}/sitemap.xml\n".format(SITE))
    with open(os.path.join(OUT, "CNAME"), "w") as f:
        f.write("mcuaa.org.au\n")
    with open(os.path.join(OUT, ".nojekyll"), "w") as f:
        f.write("")
    with open(os.path.join(OUT, "README.md"), "w") as f:
        f.write("""# MCUAA · 墨尔本中国高校校友会联盟

Material Design 3 website (seed color #4460A5). Deployable to GitHub Pages.

## Structure

    index.html  news.html  events.html  members.html  constitution.html
    contact.html  404.html
    articles/<slug>.html          Article pages
    assets/css/site.css           Design system
    assets/js/site.js             Drawer / scroll behaviour
    assets/img/                   Global images (logo, hero, QR, …)
    assets/img/posts/             Flat per-article images (<slug>-cover.jpg, …)
    sitemap.xml  robots.txt  CNAME  .nojekyll

## Rebuild

    python3 tools/build.py        # regenerates the site from source/
""")

    print("\nDone. Posts: {} ({} events, {} news)".format(
        n, len([p for p in posts if p["category"] == "活动"]),
        len([p for p in posts if p["category"] == "新闻"])))


if __name__ == "__main__":
    main()
