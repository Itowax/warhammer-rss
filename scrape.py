import requests, re, datetime, os
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

SRC = "https://www.warhammer-community.com/en-gb/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; WarhammerRSS/1.0)"}

def fetch_articles():
    resp = requests.get(SRC, headers=UA, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Sélecteurs larges pour résister aux changements de mise en page
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
    now = datetime.datetime.utcnow()

    fg = FeedGenerator()
    fg.title("Warhammer Community – flux non officiel")
    fg.link(href=SRC, rel="alternate")
    fg.description("Flux RSS généré automatiquement depuis Warhammer Community (non officiel).")
    fg.language("en")
    fg.lastBuildDate(now)

    for it in items:
        fe = fg.add_entry()
        fe.title(it["title"])
        fe.link(href=it["link"])
        fe.description(it["desc"])
        fe.pubDate(now)  # pas de date source fiable → on met l'heure de build

    return fg.rss_str(pretty=True)

if __name__ == "__main__":
    items = fetch_articles()
    os.makedirs("docs", exist_ok=True)
    xml = build_rss(items)
    with open("docs/rss.xml", "wb") as f:
        f.write(xml)
