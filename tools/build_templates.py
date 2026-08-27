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
    home = root if root else "./"
    links = []
    for name, href in NAV:
        cur = ' class="nav-item active"' if name == active else ' class="nav-item"'
        links.append('<a href="{root}{href}"{cur}>{name}</a>'.format(root=root, href=href, cur=cur))

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
  l.href = "https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap";
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
      <span class="brand-logo-wrap"><img class="brand-logo" src="{root}assets/img/logo-40.png" alt="MCUAA"></span>
      <span class="brand-text">
        <span class="brand-zh">墨尔本中国高校校友会联盟</span>
        <span class="brand-en">MCUAA · Melbourne CUAA Alliance</span>
      </span>
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
    home = root if root else "./"
    return """
</main>
<footer class="footer">
  <div class="footer-inner">
    <div>
      <span class="footer-logo-wrap"><img class="footer-logo" src="{root}assets/img/logo-40.png" alt="MCUAA"></span>
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
    <p class="footer-note">Melbourne CUAA Alliance Inc. &mdash; 非营利 &middot; 非政治 &middot; 非宗教</p>
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


def post_card(out_path, p):
    """Editorial post card (shared by home + news listing)."""
    url = href_to(out_path, p["file_rel"])
    return """<article class="post-card reveal">
  <a class="post-card-link" href="{url}">
    <div class="post-thumb-wrap"><img class="post-thumb" src="{root}{thumb}" alt="" loading="lazy"></div>
    <div class="post-card-body">
      <span class="post-date">{date}</span>
      <h3 class="post-card-title">{title}</h3>
      <p class="post-excerpt">{excerpt}</p>
      <span class="post-more">阅读全文 &rsaquo;</span>
    </div>
  </a>
</article>""".format(url=url, root=rel_prefix(out_path), thumb=p["thumb"],
                   date=fmt_date_cn(p["date"]), title=p["title"], excerpt=p["excerpt"])


def build_home(posts):
    out_path = os.path.join(OUT, "index.html")
    recent = [post_card(out_path, p) for p in posts[:6]]
    recent = "\n      ".join(recent)

    members = parse_members()
    member_count = sum(len(g["items"]) for g in members)
    governing = len(members[0]["items"]) if members else 0

    missions = [
        ("共享资源 · 联合活动", "在尊重每个成员校友会独立性与自主权的基础上，推动资源共享与联合举办活动，提升整体影响力。"),
        ("健康生活 · 职业成长", "倡导健康积极的生活方式，丰富校友的业余生活，并为校友的职业发展与专业成长提供支持。"),
        ("经验分享 · 共同成长", "分享各校友会运作的最佳实践经验，提升组织能力，同时协助不活跃或规模较小的校友会逐步成长。"),
        ("弘扬文化 · 促进融合", "弘扬中华文化，增强华人社区的凝聚力，促进跨文化理解与多元融合。"),
        ("中澳交流 · 合作共赢", "推动中澳两国在科技、教育、文化等领域的交流与合作。"),
    ]
    cards = []
    for i, (t, d) in enumerate(missions, 1):
        cards.append("""<article class="reason-card reveal">
          <span class="reason-icon">{i}</span>
          <h3 class="reason-title">{t}</h3>
          <p class="reason-text">{d}</p>
        </article>""".format(i=i, t=t, d=d))
    cards.append("""<article class="reason-card reveal">
          <span class="reason-icon">+</span>
          <h3 class="reason-title">加入我们 · 成为成员</h3>
          <p class="reason-text">联盟目前拥有 {gov} 个理事单位、{mem} 个成员校友会，覆盖四十余所中国高校。欢迎符合条件的校友会加入。</p>
          <a class="post-more" href="members.html">查看成员名单 &rsaquo;</a>
        </article>""".format(gov=governing, mem=member_count))
    cards = "\n      ".join(cards)

    body = """
<section class="hero">
  <div class="hero-inner">
    <p class="hero-kicker">MCUAA · Melbourne CUAA Alliance Inc.</p>
    <h1 class="hero-title">墨尔本中国高校校友会联盟</h1>
    <p class="hero-subtitle"><strong>Melbourne CUAA Alliance Inc</strong> &mdash; 交流联谊 · 合作共赢 · 共同进步</p>
    <div class="cta-row">
      <a class="btn btn-primary hero-cta" href="news.html">浏览最新动态 &rsaquo;</a>
      <a class="btn btn-secondary" href="constitution.html">了解联盟章程</a>
    </div>
  </div>
</section>

<section class="section section-home">
  <div class="section-inner narrow">
    <hr class="divider">
    <blockquote class="motto-text">交流联谊，合作共赢，共同进步</blockquote>
    <hr class="divider">
    <div class="home-spacer"></div>
    <p class="about-text">墨尔本中国高校校友会联盟（MCUAA）是一个非营利、非政治、非宗教组织，于 2025 年 4 月在澳大利亚正式注册成立。联盟的宗旨是：为墨尔本各中国高校校友会之间建立一个交流联谊、合作共赢、共同进步的平台。</p>
  </div>
</section>

<section class="section section-gray">
  <div class="section-inner-wide">
    <span class="kicker">About &middot; 关于我们</span>
    <h2 class="section-title">凝聚校友力量，共创发展平台</h2>
    <p class="section-desc">MCUAA is committed to &mdash; 联盟致力于：</p>
    <div class="mission-grid">
      {cards}
    </div>
  </div>
</section>

<section class="section">
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
""".format(cards=cards, recent=recent, gov=governing, mem=member_count)
    html = render_page(rel_prefix(out_path), "Home", "首页 | Home - 墨尔本中国高校校友会联盟 MCUAA",
                       "墨尔本中国高校校友会联盟（MCUAA）官方主页：新闻动态、活动回顾、成员与章程。",
                       body)
    write(out_path, html)


def build_news(posts):
    out_path = os.path.join(OUT, "news.html")
    root = rel_prefix(out_path)
    cards = "\n      ".join(post_card(out_path, p) for p in posts)

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
    rows = []
    for p in posts:
        y, m, d = p["date"].split("-")
        url = href_to(out_path, p["file_rel"])
        rows.append("""<a class="event-row reveal" href="{url}">
          <span class="event-date"><span class="day">{day}</span><span class="mon">{mon}</span></span>
          <span class="event-body">
            <span class="title">{title}</span>
            <span class="excerpt">{excerpt}</span>
          </span>
          <span class="event-arrow">&rsaquo;</span>
        </a>""".format(url=url, day=int(d), mon=MONTHS[int(m) - 1], title=p["title"],
                       excerpt=p["excerpt"]))
    rows = "\n    ".join(rows)

    body = """
<section class="hero hero-small">
  <div class="hero-inner">
    <p class="hero-kicker">Events &middot; 活动回顾</p>
    <h1 class="hero-title">活动回顾</h1>
    <p class="hero-subtitle">共 {n} 场活动</p>
  </div>
</section>

<section class="section">
  <div class="section-inner">
    <div class="event-list">
      {rows}
    </div>
  </div>
</section>
""".format(rows=rows, n=len(posts))
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
    cards = []
    for s in sections:
        blocks = []
        for kind, val in s["blocks"]:
            if kind == "p":
                blocks.append("<p class=\"rule-note\">{}</p>".format(val))
            elif kind == "sub":
                blocks.append("<p class=\"rule-note\" style=\"font-weight:700;color:var(--text)\">{}</p>".format(val))
            elif kind == "ul":
                items = "".join("<li>{}</li>".format(it) for it in val)
                blocks.append("<ul class=\"rules-list\">{}</ul>".format(items))
        cards.append("""<section class="rule-card reveal">
        <h2 class="rule-card-title"><span class="rule-num">{num}</span>{title}</h2>
        {blocks}
      </section>""".format(num=s["num"], title=s["title"], blocks="".join(blocks)))
    cards = "\n    ".join(cards)

    body = """
<section class="hero hero-small">
  <div class="hero-inner">
    <p class="hero-kicker">Constitution &middot; 章程</p>
    <h1 class="hero-title">墨尔本中国高校校友会联盟章程</h1>
    <p class="hero-subtitle">根据维多利亚州《2012年社团成立改革法案》制定</p>
  </div>
</section>

<section class="section">
  <div class="section-inner">
    <div class="constitution-wrap">
      {cards}
    </div>
  </div>
</section>
""".format(cards=cards)
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
  <div class="section-inner narrow">
    <div class="qr-wrap">
      <div class="qr-card">
        <img class="qr-img" src="{root}assets/img/wechat-qr.png" alt="MCUAA 微信公众号二维码">
      </div>
      <p class="qr-caption">微信公众平台公众号 · 扫码关注</p>
    </div>
    <div class="contact-list">
      <div class="contact-row reveal">
        <span class="contact-ico">{mail}</span>
        <div>
          <p class="contact-row-label">电子邮件 Email</p>
          <p class="contact-row-value"><a href="mailto:mcuaa2025@gmail.com">mcuaa2025@gmail.com</a></p>
        </div>
      </div>
      <div class="contact-row reveal">
        <span class="contact-ico">{wechat}</span>
        <div>
          <p class="contact-row-label">微信公众平台</p>
          <p class="contact-row-value">关注公众号，获取最新活动与动态</p>
        </div>
      </div>
    </div>
  </div>
</section>
""".format(root=root, mail=ICONS["mail"], wechat=ICONS["wechat"])
    html = render_page(root, "Contact", "联系 | Contact - 墨尔本中国高校校友会联盟 MCUAA",
                       "联系 MCUAA：mcuaa2025@gmail.com，微信公众平台。", body)
    write(out_path, html)


def build_article(p, prev_p, next_p):
    out_path = os.path.join(OUT, p["file_rel"])
    root = rel_prefix(out_path)
    body_html = sanitize_body(p["body_src"], root, p["img_map"])

    # Drop a leading figure that only repeats the cover photo
    if p["cover"]:
        m = re.search(r"<figure[^>]*>\s*<img src=\"([^\"]+)\"[^>]*>\s*</figure>", body_html)
        if m and os.path.basename(m.group(1)) == os.path.basename(p["cover"]):
            body_html = body_html[:m.start()] + body_html[m.end():]

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
<article class="post-page">
  {cover}
  <header class="post-meta">
    <span class="post-date">{date_cn} &middot; {category}</span>
    <h1>{title}</h1>
    <p class="post-byline">墨尔本中国高校校友会联盟 &middot; MCUAA</p>
  </header>
  <div class="post-content">
    {body}
  </div>
  {nav}
  <div class="post-back">
    <a class="btn btn-secondary" href="{back}">← {back_label}</a>
  </div>
</article>
""".format(cover=cover, date_cn=fmt_date_cn(p["date"]), category=p["category"],
           title=p["title"], body=body_html, nav=nav_html,
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

