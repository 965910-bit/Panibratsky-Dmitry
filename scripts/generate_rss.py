#!/usr/bin/env python3
import json
import os
from datetime import datetime
from email.utils import format_datetime

def generate_rss():
    news_file = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    rss_file = os.path.join(os.path.dirname(__file__), "..", "rss.xml")

    if not os.path.exists(news_file):
        print("news.json not found, skipping RSS generation")
        return

    with open(news_file, "r", encoding="utf-8") as f:
        news = json.load(f)

    items = news[:50]

    rss = []
    rss.append('<?xml version="1.0" encoding="UTF-8"?>')
    rss.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    rss.append('<channel>')
    rss.append('  <title>Логистические новости</title>')
    rss.append('  <link>https://scm-news.ru/</link>')
    rss.append('  <description>Автоматический сбор новостей по логистике, цифровизации и управлению цепями поставок</description>')
    rss.append('  <language>ru</language>')
    rss.append(f'  <lastBuildDate>{format_datetime(datetime.now())}</lastBuildDate>')
    rss.append('  <atom:link href="https://scm-news.ru/rss.xml" rel="self" type="application/rss+xml"/>')

    for item in items:
        rss.append('  <item>')
        rss.append(f'    <title><![CDATA[{item["title"]}]]></title>')
        rss.append(f'    <link>{item["link"]}</link>')
        rss.append(f'    <description><![CDATA[{item["description"]}]]></description>')
        rss.append(f'    <pubDate>{item["pubDate"]}</pubDate>')
        if "tags" in item and item["tags"]:
            rss.append(f'    <category>{", ".join(item["tags"])}</category>')
        rss.append('  </item>')

    rss.append('</channel>')
    rss.append('</rss>')

    with open(rss_file, "w", encoding="utf-8") as f:
        f.write("\n".join(rss))

    print("RSS feed generated at rss.xml")

if __name__ == "__main__":
    generate_rss()
