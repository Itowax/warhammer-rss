import os, re, json, requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urljoin

UA = {"User-Agent": "Mozilla/5.0 (compatible; WarhammerRSS/2.0)"}
MAX_ITEMS = 15
NEW_ONLY  = False  # ne publier QUE les nouveaux liens (anti-spam)

FEEDS = [
    # title, base_url,           lang,      seen_json,            out_xml
    ("Warhammer Community FR", "https://www.warhammer-community.com/fr-fr/", "fr",
     "data/seen_fr.json", "docs/rss-fr.xml"),
    ("Warhammer Community EN", "https://www.warhammer-community.com/en-gb/", "en",
     "data/seen_en.json", "docs/rss-en.xml"),
]

def load_seen(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_seen(path, seen):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # garder un historique raisonnable
    if len(seen) > 800:
        seen = dict(list(sorted(seen.items(), key=lambda kv: kv[1], reverse=True))[:800])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)

def fetch_articles(src):
    r = requests.get(src, headers=UA, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select("article, div[class*=card], li[class*=post]")[:MAX_ITEMS]
    items = []
    for c in cards:
        a = c.find("a", href=True)
        h = c.find(["h2","h3","h4"])
        if not a or not h:
            continue
        href  = a["href"].strip()
        link  = urljoin(src, href)
        title = re.sub(r"\s+", " ", h.get_text(strip=True))
        p = c.find("p")
        desc  = (p.get_text(" ", strip=True) if p else title)
        items.append({"title": title, "link": link, "desc": desc})
    return items

def esc(s):  # échappement XML simple
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def build_rss(title, src, lang, items, seen):
    now_rfc = format_datetime(datetime.now(timezone.utc))

    # déterminer les nouveaux liens (et fixer la date à 1ère vue)
    new_items = []
    for it in items:
        link = it["link"]
        if link not in seen:
            seen[link] = now_rfc
            new_items.append(it)

    items_to_publish = new_items if NEW_ONLY else items

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        f'<title>{esc(title)}</title>',
        f'<link>{esc(src)}</link>',
        f'<description>{esc(title)} – flux RSS.</description>',
        f'<lastBuildDate>{now_rfc}</lastBuildDate>',
        f'<language>{lang}</language>',
    ]
    for it in items_to_publish:
        link = esc(it["link"])
        parts += [
            '<item>',
            f'  <title>{esc(it["title"])}</title>',
            f'  <link>{link}</link>',
            f'  <guid isPermaLink="true">{link}</guid>',
            f'  <description>{esc(it["desc"])}</description>',
            f'  <pubDate>{seen[it["link"]]}</pubDate>',
            '</item>',
        ]
    parts += ['</channel></rss>']
    return "\n".join(parts).encode("utf-8"), seen

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    for title, src, lang, seen_path, out_xml in FEEDS:
        items = fetch_articles(src)
        seen  = load_seen(seen_path)
        xml, seen = build_rss(title, src, lang, items, seen)
        save_seen(seen_path, seen)
        with open(out_xml, "wb") as f:
            f.write(xml)
