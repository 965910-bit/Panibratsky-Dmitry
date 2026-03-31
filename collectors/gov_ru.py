import requests
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

class GovRuCollector:
    def __init__(self):
        self.sources = [
            {"name": "Росстат", "url": "http://www.gks.ru/rss/news.xml"},
            {"name": "Минтранс", "url": "https://mintrans.gov.ru/press-center/news/rss"}
        ]

    def fetch(self):
        results = []
        for src in self.sources:
            try:
                resp = requests.get(src["url"], timeout=10)
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                channel = root.find("channel")
                if channel is None:
                    continue
                items = channel.findall("item")
                for item in items[:10]:
                    title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    pubDate = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    description = item.find("description").text if item.find("description") is not None else ""
                    description = re.sub(r'<[^>]+>', '', description)[:250]
                    results.append({
                        "title": title,
                        "link": link,
                        "pubDate": pubDate,
                        "description": description,
                        "source": src["name"],
                        "lang": "ru",
                        "category": "government"
                    })
            except Exception as e:
                print(f"Error fetching {src['name']}: {e}")
        return results
