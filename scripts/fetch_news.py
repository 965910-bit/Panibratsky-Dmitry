import requests
import xml.etree.ElementTree as ET
import json
import re
import os
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime

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
def fetch_page_description(url):
    """Извлекает описание со страницы (meta description или первый абзац)."""
    try:
        resp = requests.get(url, timeout=8, headers=HEADERS)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, 'html.parser')
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'][:250]
        # Ищем первый абзац текста
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 30:
                return text[:250]
        return ""
    except Exception:
        return ""

def load_google_alerts(existing_links):
    """Загружает Google Alerts, фильтрует по домену и дубликатам, извлекает описание."""
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

            # Извлекаем описание со страницы
            description = fetch_page_description(link)
            if not description:
                description = f"Google Alert по теме: {alert['keyword']}"

            try:
                dt = datetime.fromisoformat(alert["date"])
                pubDate = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            except:
                pubDate = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

            news_items.append({
                "title": alert["subject"],
                "link": link,
                "pubDate": pubDate,
                "description": description,
                "source": "Google Alert",
                "lang": "ru",
                "category": alert["keyword"]
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
    """Возвращает множество ссылок из уже существующего news.json."""
    if not os.path.exists(news_file):
        return set()
    try:
        with open(news_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {item['link'] for item in data}
    except:
        return set()

# ---------------------- ЧИСТКА СТАРЫХ НОВОСТЕЙ ----------------------
def clean_old_news(news_items, days=30):
    """Удаляет новости старше указанного количества дней."""
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    cleaned = []
    removed = 0
    for item in news_items:
        try:
            # Парсим дату в формате RFC 822
            pub_date = parsedate_to_datetime(item['pubDate'])
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=None)  # для сравнения с наивным now
            if pub_date >= cutoff:
                cleaned.append(item)
            else:
                removed += 1
        except Exception:
            # Если дата не распарсилась, сохраняем (лучше оставить, чем потерять)
            cleaned.append(item)
    if removed:
        print(f"Удалено старых новостей (старше {days} дней): {removed}")
    return cleaned

# ---------------------- ГЛАВНАЯ ----------------------
def main():
    news_file = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    existing_links = load_existing_links(news_file)

    all_news = []
    for src in SOURCES:
        if src["type"] == "rss":
            news = fetch_rss(src)
        else:
            news = fetch_from_sitemap(src)
        # Для RSS/sitemap тоже можно фильтровать дубликаты
        for item in news:
            if item['link'] not in existing_links:
                all_news.append(item)
                existing_links.add(item['link'])  # чтобы не дублировать внутри одного запуска
        print(f"Из {src['name']} получено {len(news)} новостей")

    google_news = load_google_alerts(existing_links)
    if google_news:
        all_news.extend(google_news)
        print(f"Из Google Alerts получено {len(google_news)} новостей")
    else:
        print("Google Alerts не найдены или пусты")

    # Чистка старых новостей перед записью
    all_news = clean_old_news(all_news, days=30)

    all_news.sort(key=lambda x: x['pubDate'], reverse=True)

    os.makedirs(os.path.dirname(news_file), exist_ok=True)
    with open(news_file, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    print(f"Всего сохранено {len(all_news)} новостей")

if __name__ == "__main__":
    main()
