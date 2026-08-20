# MCUAA · 墨尔本中国高校校友会联盟

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
