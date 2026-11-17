import requests
import xml.etree.ElementTree as ET
import json
import re
import os
import time
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from news_utils import merge_news

# Direct primary sources are paused pending clarification of access rights.
# Keep the existing feed unchanged rather than treating a paused feed as fresh data.
SOURCES = []


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
}

# ========== ЧЁРНЫЙ СПИСОК УКРАИНСКИХ ДОМЕНОВ ==========
UKRAINIAN_DOMAINS = [
    'ukr.net',
    'unian.net',
    'pravda.com.ua',
    'censor.net',
    'liga.net',
    'kp.ua',
    'tsn.ua',
    'rbc.ua',
    'epravda.com.ua',
    'focus.ua',
    'apostrophe.ua',
    'obozrevatel.com',
    'segodnya.ua',
    'strana.ua',
    'fakty.ua',
    'gordonua.com',
    'glavcom.ua',
    'zaxid.net',
    'ukrinform.ua',
    'unn.com.ua',
    'zn.ua',
    'nv.ua',
    'lb.ua',
    'comments.ua',
    'ua.interfax.com.ua',
    'radio.ua',
    'ukr.media',
    'hromadske.ua',
    'censor.net.ua'
]

# ========== КЛЮЧЕВЫЕ СЛОВА ДЛЯ ТЕГОВ ==========
KEYWORDS = [
    "логистик", "перевозк", "грузоперевозк", "склад", "транспорт", "доставка", "логист",
    "цепь поставок", "управление цепями", "складск", "фулфилмент", "последняя миля",
    "робот", "автоматизац", "искусственный интеллект", "ии", "цифровизац", "беспилотник",
    "дрон", "wms", "tms", "yms", "iot", "блокчейн", "big data",
    "маркетплейс", "озон", "wildberries", "ozon", "wb", "электронная коммерция", "e-commerce",
    "розничн", "торговл",
    "экономик", "инфляц", "санкц", "кризис", "импорт", "экспорт", "таможн", "пошлин",
    "росси", "москв", "петербург", "спб", "сибир", "урал", "дальний восток"
]

def is_ukrainian_source(link: str) -> bool:
    try:
        domain = urlparse(link).netloc.lower()
        if not domain:
            return False
        if domain.startswith('www.'):
            domain = domain[4:]
        for banned in UKRAINIAN_DOMAINS:
            if domain == banned or domain.endswith('.' + banned):
                return True
        if domain.endswith('.ua'):
            return True
    except:
        pass
    return False

def extract_tags(text):
    text_lower = text.lower()
    found = set()
    for kw in KEYWORDS:
        if kw in text_lower:
            found.add(kw)
    return list(found)

def summarize_description(desc, max_len=200):
    if len(desc) <= max_len:
        return desc
    cut = max_len
    for sep in ['.', '!', '?']:
        last = desc.rfind(sep, 0, max_len)
        if last > max_len // 2:
            cut = last + 1
            break
    return desc[:cut].strip()

# ---------------------- RSS ----------------------
def fetch_rss(source):
    try:
        resp = requests.get(source["url"], timeout=15, headers=HEADERS)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            raise ValueError('RSS не содержит channel')
        items = channel.findall("item")
        result = []
        for item in items:
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pubDate = item.find("pubDate").text if item.find("pubDate") is not None else ""
            description = item.find("description").text if item.find("description") is not None else ""
            description = re.sub(r'<[^>]+>', '', description)[:250]
            description = summarize_description(description)
            tags = extract_tags(description + " " + title)
            result.append({
                "title": title,
                "link": link,
                "pubDate": pubDate,
                "collected_at": datetime.now(timezone.utc).isoformat() if not pubDate else None,
                "description": description,
                "source": source["name"],
                "lang": source["lang"],
                "category": source["cat"],
                "tags": tags
            })
        return result
    except Exception as e:
        print(f"Ошибка RSS {source['name']}: {e}")
        return None

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
        if not sitemap_urls:
            raise ValueError('Не найдены подходящие карты сайта')

        all_urls = []
        loaded_sitemaps = 0
        for sitemap_url in sitemap_urls:
            try:
                resp2 = requests.get(sitemap_url, timeout=15, headers=HEADERS)
                resp2.raise_for_status()
                root2 = ET.fromstring(resp2.content)
                loaded_sitemaps += 1
                for url_elem in root2.findall('.//s:url', ns):
                    loc = url_elem.find('s:loc', ns).text
                    if any(pattern in loc for pattern in ['/news/', '/blog/', '/post/']):
                        all_urls.append(loc)
            except Exception as e:
                print(f"Ошибка загрузки {sitemap_url}: {e}")

        if not loaded_sitemaps:
            raise RuntimeError('Не удалось загрузить ни одну карту сайта')
        news_items = []
        attempted_urls = all_urls[:10]
        for url in attempted_urls:
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
                # An unknown publication date must not be replaced with the collection time.
                if not pubDate:
                    pubDate = ''

                desc_meta = soup.find('meta', {'name': 'description'})
                if desc_meta and desc_meta.get('content'):
                    description = desc_meta['content'][:250]
                else:
                    first_p = soup.find('p')
                    description = first_p.text.strip()[:250] if first_p else ""

                description = summarize_description(description)
                tags = extract_tags(description + " " + title)

                news_items.append({
                    "title": title,
                    "link": url,
                    "pubDate": pubDate,
                    "collected_at": datetime.now(timezone.utc).isoformat() if not pubDate else None,
                    "description": description,
                    "source": source["name"],
                    "lang": source["lang"],
                    "category": source["cat"],
                    "tags": tags
                })
            except Exception as e:
                print(f"Ошибка парсинга {url}: {e}")

        if attempted_urls and not news_items:
            raise RuntimeError('Не удалось получить ни одной страницы новостей')
        return news_items
    except Exception as e:
        print(f"Ошибка обработки sitemap {source['name']}: {e}")
        return None

# ---------------------- GOOGLE ALERTS ----------------------
def fetch_page_description(url):
    try:
        resp = requests.get(url, timeout=8, headers=HEADERS)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, 'html.parser')
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'][:250]
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 30:
                return text[:250]
        return ""
    except Exception:
        return ""

def load_google_alerts(existing_links):
    alerts_path = os.path.join(os.path.dirname(__file__), "..", "data", "google_alerts.json")
    if not os.path.exists(alerts_path):
        return []
    try:
        with open(alerts_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        alerts = data.get("alerts", [])
        news_items = []
        skipped_duplicate = 0
        skipped_ua = 0
        for alert in alerts:
            link = alert.get("link", "")
            if is_ukrainian_source(link):
                skipped_ua += 1
                continue
            if link in existing_links:
                skipped_duplicate += 1
                continue

            # Alert links come from email; never fetch arbitrary URLs from the runner.
            description = f"Google Alert по теме: {alert.get('keyword', '')}"
            description = summarize_description(description)
            tags = extract_tags(description + " " + alert["subject"])

            # The email date is an alert timestamp, not a verified publication date.
            pubDate = ''

            news_items.append({
                "title": alert["subject"],
                "link": link,
                "pubDate": pubDate,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "description": description,
                "source": "Google Alert",
                "lang": "ru",
                "category": alert["keyword"],
                "tags": tags
            })
        if skipped_ua:
            print(f"Из Google Alerts отфильтровано украинских источников: {skipped_ua}")
        if skipped_duplicate:
            print(f"Из Google Alerts отфильтровано дубликатов: {skipped_duplicate}")
        return news_items
    except Exception as e:
        print(f"Ошибка загрузки Google Alerts: {e}")
        return []

# ---------------------- ОБЩАЯ ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ СУЩЕСТВУЮЩИХ ССЫЛОК ----------------------
def load_existing_links(news_file):
    if not os.path.exists(news_file):
        return set()
    try:
        with open(news_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {item['link'] for item in data}
    except:
        return set()

# ---------------------- ГЛАВНАЯ ----------------------
def main(news_file=None):
    if not SOURCES:
        print('::warning::Основные источники приостановлены; лента не обновлялась')
        return
    news_file = news_file or os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    if os.path.exists(news_file):
        with open(news_file, "r", encoding="utf-8") as f:
            previous = json.load(f)
        if not isinstance(previous, list):
            raise ValueError("news.json must contain a list")
    else:
        previous = []
    existing_links = {item.get('link') for item in previous if isinstance(item, dict)}
    incoming = []
    successful_sources = 0
    for src in SOURCES:
        news = fetch_rss(src) if src["type"] == "rss" else fetch_from_sitemap(src)
        if news is None:
            print(f"::warning::Не удалось получить данные источника {src['name']}")
            continue
        successful_sources += 1
        for item in news:
            if item.get('link') not in existing_links:
                incoming.append(item)
                existing_links.add(item.get('link'))
        print(f"Из {src['name']} получено {len(news)} новостей")

    if not successful_sources:
        raise RuntimeError('Все основные источники недоступны; существующая лента сохранена')

    for item in load_google_alerts(existing_links):
        if item.get('link') not in existing_links:
            incoming.append(item)
            existing_links.add(item.get('link'))
    # A temporary outage should never replace the existing feed with an empty file.
    if not incoming and previous:
        print("Нет новых новостей; существующая лента сохранена без изменений")
        return
    all_news = merge_news(previous, incoming)
    if not all_news and previous:
        raise RuntimeError("Refusing to replace existing feed with an empty result")
    os.makedirs(os.path.dirname(news_file), exist_ok=True)
    temp = news_file + '.tmp'
    try:
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(all_news, f, ensure_ascii=False, indent=2)
        os.replace(temp, news_file)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print(f"Всего сохранено {len(all_news)} новостей")

if __name__ == "__main__":
    main()
