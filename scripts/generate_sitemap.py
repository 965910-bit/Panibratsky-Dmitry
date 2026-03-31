#!/usr/bin/env python
import json
import os
from datetime import datetime
from email.utils import parsedate_to_datetime

def generate_sitemap():
    static_pages = [
        "trends.html",
        "index.html",
        "about.html",
        "contact.html",
        "expertise.html",
        "experience.html"
    ]
    base_url = "https://965910-bit.github.io/Panibratsky-Dmitry/"

    news_path = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    news_items = []
    if os.path.exists(news_path):
        with open(news_path, "r", encoding="utf-8") as f:
            news_items = json.load(f)

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    today = datetime.now().strftime("%Y-%m-%d")
    for page in static_pages:
        xml += '  <url>\n'
        xml += f'    <loc>{base_url}{page}</loc>\n'
        xml += f'    <lastmod>{today}</lastmod>\n'
        xml += '    <changefreq>weekly</changefreq>\n'
        xml += '    <priority>0.8</priority>\n' if page != "trends.html" else '    <priority>1.0</priority>\n'
        xml += '  </url>\n'

    for item in news_items[:100]:
        link = item.get("link")
        if not link or not link.startswith("http"):
            continue
        pub_date = item.get("pubDate", "")
        lastmod = today
        if pub_date:
            try:
                dt = parsedate_to_datetime(pub_date)
                lastmod = dt.strftime("%Y-%m-%d")
            except:
                pass
        xml += '  <url>\n'
        xml += f'    <loc>{link}</loc>\n'
        xml += f'    <lastmod>{lastmod}</lastmod>\n'
        xml += '    <changefreq>never</changefreq>\n'
        xml += '    <priority>0.6</priority>\n'
        xml += '  </url>\n'

    xml += '</urlset>'

    output_path = os.path.join(os.path.dirname(__file__), "..", "sitemap.xml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"Sitemap generated: {output_path}")

if __name__ == "__main__":
    generate_sitemap()
