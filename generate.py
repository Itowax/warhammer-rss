import os, re, json, requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import format_datetime

SRC = "https://www.warhammer-community.com/en-gb/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; WarhammerRSS/1.0)"}
SEEN_PATH = "data/seen.json"
MAX_ITEMS = 15  # limite d'items dans le flux

def load_seen():
    if os.path.exists(SEEN_PATH):
        with open(SEEN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_seen(seen):
    os.makedirs(os.path.dirname(SEEN_PATH), exist_ok=True)
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)

def fetch_articles():
    r = requests.get(SRC, headers=UA, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select("article, div[class*=card], li[class*=post]")[:MAX_ITEMS]
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

def esc(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def build_rss(items, seen):
    now_rfc = format_datetime(datetime.now(timezone.utc))
    # Assigne une pubDate stable pour chaque lien (si nouveau -> maintenant)
    out_dates = {}
    for it in items:
        link = it["link"]
        out_dates[link] = seen.get(link) or now_rfc

    # Ne garde en mémoire que les items présents (évite que le JSON grossisse)
    save_seen({link: out_dates[link] for link in out_dates})

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
        pub = out_dates[it["link"]]
        parts += [
            '<item>',
            f'  <title>{title}</title>',
            f'  <link>{link}</link>',
            f'  <guid isPermaLink="true">{link}</guid>',
            f'  <description>{desc}</description>',
            f'  <pubDate>{pub}</pubDate>',
            '</item>',
        ]
    parts += ['</channel></rss>']
    return "\n".join(parts).encode("utf-8")

if __name__ == "__main__":
    items = fetch_articles()
    seen = load_seen()
    os.makedirs("docs", exist_ok=True)
    xml = build_rss(items, seen)
    with open("docs/rss.xml", "wb") as f:
        f.write(xml)
