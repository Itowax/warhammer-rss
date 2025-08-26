import requests, re, os
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import format_datetime

SRC = "https://www.warhammer-community.com/en-gb/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; WarhammerRSS/1.0)"}

def fetch_articles():
    r = requests.get(SRC, headers=UA, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    cards = soup.select("article, div[class*=card], li[class*=post]")[:15]
    items = []
    for c in cards:
        a = c.find("a", href=True)
        h = c.find(["h2","h3","h4"])
        if not a or not h:
            continue
        link = a["href"].strip()
        if link.startswith("/"):
            link = "https://www.warhammer-community.com" + link
        title = re.sub(r"\s+", " ", h.get_text(strip=True))
        p = c.find("p")
        desc = (p.get_text(" ", strip=True) if p else title)
        items.append({"title": title, "link": link, "desc": desc})
    return items

def build_rss(items):
    now_rfc = format_datetime(datetime.now(timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        '<title>Warhammer Community – flux non officiel</title>',
        f'<link>{SRC}</link>',
        '<description>Flux RSS généré automatiquement depuis Warhammer Community (non officiel).</description>',
        f'<lastBuildDate>{now_rfc}</lastBuildDate>',
        '<language>en</language>',
    ]
    for it in items:
        title = esc(it["title"]); link = esc(it["link"]); desc = esc(it["desc"])
        parts += [
            '<item>',
            f'  <title>{title}</title>',
            f'  <link>{link}</link>',
            f'  <description>{desc}</description>',
            f'  <pubDate>{now_rfc}</pubDate>',
            '</item>',
        ]
    parts += ['</channel></rss>']
    return "\n".join(parts).encode("utf-8")

def esc(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

if __name__ == "__main__":
    items = fetch_articles()
    os.makedirs("docs", exist_ok=True)
    xml = build_rss(items)
    with open("docs/rss.xml", "wb") as f:
        f.write(xml)
