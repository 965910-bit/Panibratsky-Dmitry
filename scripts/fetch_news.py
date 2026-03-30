import requests
import xml.etree.ElementTree as ET
import json
import re
import os

# Рабочие источники (добавлен AXELOT)
SOURCES = [
    {"name": "Логистика 360", "url": "https://logistics360.ru/feed/", "cat": "logistics", "lang": "ru"},
    {"name": "AXELOT", "url": "https://www.axelot.ru/feed/", "cat": "scm", "lang": "ru"}
]

def fetch_rss(source):
    try:
        resp = requests.get(source["url"], timeout=10)
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
        print(f"Ошибка загрузки {source['name']}: {e}")
        return []

def main():
    all_news = []
    for src in SOURCES:
        news = fetch_rss(src)
        all_news.extend(news)
    all_news.sort(key=lambda x: x['pubDate'], reverse=True)
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)
    print(f"Сохранено {len(all_news)} новостей")

if __name__ == "__main__":
    main()
