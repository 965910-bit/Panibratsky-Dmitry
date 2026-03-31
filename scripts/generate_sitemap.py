#!/usr/bin/env python
import json
import os
from datetime import datetime

def generate_sitemap():
    # Статичные страницы
    static_pages = [
        "trends.html",
        "index.html",
        "about.html",
        "contact.html",
        "expertise.html",
        "experience.html"
    ]
    base_url = "https://965910-bit.github.io/Panibratsky-Dmitry/"

    # Загружаем новости
    news_path = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    news_items = []
    if os.path.exists(news_path):
        with open(news_path, "r", encoding="utf-8") as f:
            news_items = json.load(f)

    # Начинаем XML
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    # Добавляем статичные страницы
    today = datetime.now().strftime("%Y-%m-%d")
    for page in static_pages:
        xml += '  <url>\n'
        xml += f'    <loc>{base_url}{page}</loc>\n'
        xml += f'    <lastmod>{today}</lastmod>\n'
        if page == "trends.html":
            xml += '    <changefreq>daily</changefreq>\n'
            xml += '    <priority>1.0</priority>\n'
        else:
            xml += '    <changefreq>weekly</changefreq>\n'
            xml += '    <priority>0.8</priority>\n'
        xml += '  </url>\n'

    # Добавляем новости (каждую новость как отдельный URL)
    for item in news_items[:100]:  # не более 100 новостей
        link = item.get("link")
        if link and link.startswith("http"):
            xml += '  <url>\n'
            xml += f'    <loc>{link}</loc>\n'
            # Пытаемся извлечь дату новости
            pub_date = item.get("pubDate", "")
            if pub_date:
                # Преобразуем RFC 822 в ISO
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub_date)
                    lastmod = dt.strftime("%Y-%m-%d")
                except:
                    lastmod = today
            else:
                lastmod = today
            xml += f'    <lastmod>{lastmod}</lastmod>\n'
            xml += '    <changefreq>never</changefreq>\n'
            xml += '    <priority>0.6</priority>\n'
            xml += '  </url>\n'

    xml += '</urlset>'

    # Записываем в корень репозитория (рядом с data/)
    output_path = os.path.join(os.path.dirname(__file__), "..", "sitemap.xml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"Sitemap generated: {output_path}")

if __name__ == "__main__":
    generate_sitemap()
