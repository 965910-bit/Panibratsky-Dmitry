import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime
import os

# RSS-источники (те же, что и в trends.html)
SOURCES = [
    {"name": "Logirus", "url": "https://logirus.ru/rss", "cat": "logistics", "lang": "ru"},
    {"name": "Логистика 360", "url": "https://logistics360.ru/feed/", "cat": "logistics", "lang": "ru"},
    {"name": "Zakupki.gov.ru", "url": "https://zakupki.gov.ru/epz/main/public/rss", "cat": "tenders", "lang": "ru"},
    {"name": "Retail & Logistics", "url": "https://retail-loyalty.org/rss/", "cat": "logistics", "lang": "ru"},
    {"name": "Склад & Логистика", "url": "https://logistics.ru/rss", "cat": "warehouse", "lang": "ru"},
    {"name": "MarketInfo", "url": "https://marketinfo.pro/rss", "cat": "marketplace", "lang": "ru"},
    {"name": "Supply Chain Digital", "url": "https://supplychaindigital.com/feeds/rss", "cat": "tech", "lang": "en"},
    {"name": "CIO SCM", "url": "https://www.cio.com/rss", "cat": "tech", "lang": "en"}
]

def fetch_rss(source):
    try:
        resp = requests.get(source["url"], timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        # RSS обычно в корне <rss>, а items – внутри <channel>
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
            # Очищаем описание от HTML
            import re
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
        print(f"Ошибка загрузки {source['name']}: {e}")
        return []

def main():
    all_news = []
    for src in SOURCES:
        news = fetch_rss(src)
        all_news.extend(news)
    # Сортировка по дате (новые сверху)
    all_news.sort(key=lambda x: x["pubDate"], reverse=True)
    # Сохраняем в JSON
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)
    print(f"Сохранено {len(all_news)} новостей в {output_path}")

if __name__ == "__main__":
    main()
