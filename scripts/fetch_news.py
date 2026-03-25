import requests
import xml.etree.ElementTree as ET
import json
import re
import os

# Русские источники (приоритетные)
ru_sources = [
    {"name": "Логистика 360", "url": "https://logistics360.ru/feed/", "cat": "logistics", "lang": "ru"},
    {"name": "Logirus", "url": "https://logirus.ru/rss", "cat": "logistics", "lang": "ru"},
    {"name": "Retail & Logistics", "url": "https://retail-loyalty.org/rss/", "cat": "logistics", "lang": "ru"},
    {"name": "Склад & Логистика", "url": "https://logistics.ru/rss", "cat": "warehouse", "lang": "ru"},
    {"name": "Zakupki.gov.ru", "url": "https://zakupki.gov.ru/epz/main/public/rss", "cat": "tenders", "lang": "ru"},
    {"name": "TenderGuru", "url": "https://www.tenderguru.ru/rss", "cat": "tenders", "lang": "ru"},
    {"name": "MarketInfo", "url": "https://marketinfo.pro/rss", "cat": "marketplace", "lang": "ru"},
    {"name": "E-Pepper", "url": "https://e-pepper.ru/news/rss/", "cat": "marketplace", "lang": "ru"},
    {"name": "РЖД-Партнёр", "url": "https://www.rzd-partner.ru/rss/", "cat": "logistics", "lang": "ru"},
    {"name": "Минтранс РФ", "url": "https://mintrans.gov.ru/rss", "cat": "regulation", "lang": "ru"},
    {"name": "ФТС России", "url": "https://customs.gov.ru/rss", "cat": "regulation", "lang": "ru"},
    {"name": "Коммерсантъ (Логистика)", "url": "https://www.kommersant.ru/RSS/section/logistics", "cat": "logistics", "lang": "ru"},
]

# Английские и международные источники (резерв)
en_sources = [
    {"name": "Supply Chain Digital", "url": "https://supplychaindigital.com/feeds/rss", "cat": "tech", "lang": "en"},
    {"name": "CIO SCM", "url": "https://www.cio.com/rss", "cat": "tech", "lang": "en"},
    {"name": "Logistics Management", "url": "https://www.logisticsmgmt.com/rss", "cat": "logistics", "lang": "en"},
    {"name": "The Loadstar", "url": "https://theloadstar.com/feed/", "cat": "logistics", "lang": "en"},
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
    # 1. Загружаем русские источники
    for src in ru_sources:
        news = fetch_rss(src)
        all_news.extend(news)
    # 2. Если русских новостей меньше 20, догружаем английские
    if len([n for n in all_news if n['lang'] == 'ru']) < 20:
        for src in en_sources:
            news = fetch_rss(src)
            all_news.extend(news)
    # 3. Сортировка: сначала русские, потом английские, внутри по дате
    all_news.sort(key=lambda x: (0 if x['lang'] == 'ru' else 1, x['pubDate']), reverse=False)
    all_news.sort(key=lambda x: x['pubDate'], reverse=True)  # дополнительная сортировка по дате, сохраняя язык
    # 4. Сохраняем в JSON
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)
    print(f"Сохранено {len(all_news)} новостей, из них русских: {len([n for n in all_news if n['lang'] == 'ru'])}")

if __name__ == "__main__":
    main()
