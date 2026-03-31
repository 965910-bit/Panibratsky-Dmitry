import requests
import xml.etree.ElementTree as ET
import json
import re
import os
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

SOURCES = [
    {
        "name": "Логистика 360",
        "url": "https://logistics360.ru/feed/",
        "cat": "logistics",
        "lang": "ru",
        "type": "rss"
    },
    {
        "name": "АТИ (новости)",
        "url": "https://news.ati.su/sitemap.xml",
        "cat": "logistics",
        "lang": "ru",
        "type": "sitemap"
    }
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
}

# ---------------------- RSS ----------------------
def fetch_rss(source):
    try:
        resp = requests.get(source["url"], timeout=15, headers=HEADERS)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            return []
        items = channel.findall("item")
        result = []
        for item in items:
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pubDate = item.find("pubDate").text if item.find("pubDate") is not None else ""
            description = item.find("description").text if item.find("description") is not None else ""
            description = re.sub(r'<[^>]+>', '', description)[:250]
            result.append({
                "title": title,
                "link": link,
                "pubDate": pubDate,
                "description": description,
                "source": source["name"],
                "lang": source["lang"],
                "category": source["cat"]
            })
        return result
    except Exception as e:
        print(f"Ошибка RSS {source['name']}: {e}")
        return []

# ---------------------- SITEMAP + ПАРСИНГ ----------------------
def fetch_from_sitemap(source):
    try:
        resp = requests.get(source["url"], timeout=15, headers=HEADERS)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        sitemap_urls = []
        for sitemap in root.findall('s:sitemap', ns):
            loc = sitemap.find('s:loc', ns).text
            match = re.search(r'sitemap-(\d{2})-(\d{4})\.xml', loc)
            if match:
                month, year = match.group(1), match.group(2)
                file_date = datetime(int(year), int(month), 1)
                if file_date >= datetime.now() - timedelta(days=90):
                    sitemap_urls.append(loc)

        sitemap_urls.sort(reverse=True)
        sitemap_urls = sitemap_urls[:3]

        all_urls = []
        for sitemap_url in sitemap_urls:
            try:
                resp2 = requests.get(sitemap_url, timeout=15, headers=HEADERS)
                resp2.raise_for_status()
                root2 = ET.fromstring(resp2.content)
                for url_elem in root2.findall('.//s:url', ns):
                    loc = url_elem.find('s:loc', ns).text
                    if any(pattern in loc for pattern in ['/news/', '/blog/', '/post/']):
                        all_urls.append(loc)
            except Exception as e:
                print(f"Ошибка загрузки {sitemap_url}: {e}")

        news_items = []
        for url in all_urls[:10]:
            try:
                page = requests.get(url, timeout=10, headers=HEADERS)
                page.raise_for_status()
                soup = BeautifulSoup(page.text, 'html.parser')

                title_tag = soup.find('h1')
                if not title_tag:
                    title_tag = soup.find('title')
                title = title_tag.text.strip() if title_tag else "Без заголовка"

                date_elem = soup.find('time')
                if not date_elem:
                    date_elem = soup.find('meta', {'name': 'date'})
                    if date_elem:
                        pubDate = date_elem.get('content', '')
                    else:
                        date_elem = soup.find(class_=re.compile(r'date|time|published'))
                        pubDate = date_elem.text.strip() if date_elem else ''
                else:
                    pubDate = date_elem.get('datetime') or date_elem.text.strip()
                if not pubDate:
                    pubDate = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

                desc_meta = soup.find('meta', {'name': 'description'})
                if desc_meta and desc_meta.get('content'):
                    description = desc_meta['content'][:250]
                else:
                    first_p = soup.find('p')
                    description = first_p.text.strip()[:250] if first_p else ""

                news_items.append({
                    "title": title,
                    "link": url,
                    "pubDate": pubDate,
                    "description": description,
                    "source": source["name"],
                    "lang": source["lang"],
                    "category": source["cat"]
                })
            except Exception as e:
                print(f"Ошибка парсинга {url}: {e}")

        return news_items
    except Exception as e:
        print(f"Ошибка обработки sitemap {source['name']}: {e}")
        return []

# ---------------------- GOOGLE ALERTS ----------------------
def load_google_alerts():
    """Загружает Google Alerts из data/google_alerts.json и преобразует в формат новостей."""
    alerts_path = os.path.join(os.path.dirname(__file__), "..", "data", "google_alerts.json")
    if not os.path.exists(alerts_path):
        return []
    try:
        with open(alerts_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        alerts = data.get("alerts", [])
        news_items = []
        for alert in alerts:
            # Преобразуем дату из ISO в RFC 822
            try:
                dt = datetime.fromisoformat(alert["date"])
                pubDate = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            except:
                pubDate = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            news_items.append({
                "title": alert["subject"],  # тема письма
                "link": alert["link"],
                "pubDate": pubDate,
                "description": f"Google Alert по теме: {alert['keyword']}",
                "source": "Google Alert",
                "lang": "ru",
                "category": alert["keyword"]  # используем ключевое слово как категорию
            })
        return news_items
    except Exception as e:
        print(f"Ошибка загрузки Google Alerts: {e}")
        return []

# ---------------------- ГЛАВНАЯ ----------------------
def main():
    all_news = []
    for src in SOURCES:
        if src["type"] == "rss":
            news = fetch_rss(src)
        else:
            news = fetch_from_sitemap(src)
        all_news.extend(news)
        print(f"Из {src['name']} получено {len(news)} новостей")
        time.sleep(1)

    # Добавляем Google Alerts
    google_news = load_google_alerts()
    if google_news:
        all_news.extend(google_news)
        print(f"Из Google Alerts получено {len(google_news)} новостей")
    else:
        print("Google Alerts не найдены или пусты")

    all_news.sort(key=lambda x: x['pubDate'], reverse=True)

    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    print(f"Всего сохранено {len(all_news)} новостей")

if __name__ == "__main__":
    main()
