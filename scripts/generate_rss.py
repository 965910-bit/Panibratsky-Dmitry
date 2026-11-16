#!/usr/bin/env python3
"""Generate a well-formed RSS feed from the collected news."""
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent

def generate_rss():
    news = json.loads((ROOT / 'data/news.json').read_text(encoding='utf-8'))
    atom = 'http://www.w3.org/2005/Atom'
    ET.register_namespace('atom', atom)
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', 'Логистические новости'), ('link', 'https://scm-news.ru/'),
                       ('description', 'Новости логистики и управления цепями поставок'), ('language', 'ru'),
                       ('lastBuildDate', format_datetime(datetime.now(timezone.utc)))]:
        ET.SubElement(channel, key).text = value
    ET.SubElement(channel, f'{{{atom}}}link', href='https://scm-news.ru/rss.xml', rel='self', type='application/rss+xml')
    seen = set()
    for item in news:
        link = item.get('link', '')
        try:
            url = urlsplit(link)
            if url.scheme not in ('http', 'https') or not url.hostname or link in seen or item.get('dead'):
                continue
        except ValueError:
            continue
        seen.add(link)
        entry = ET.SubElement(channel, 'item')
        for key in ('title', 'link', 'description', 'pubDate'):
            # XML 1.0 disallows most C0 control characters.
            value = str(item.get(key) or '')
            ET.SubElement(entry, key).text = ''.join(c for c in value if ord(c) >= 32 or c in '\t\n\r')
        for tag in item.get('tags') or []:
            ET.SubElement(entry, 'category').text = ''.join(c for c in str(tag) if ord(c) >= 32 or c in '\t\n\r')
        if len(seen) == 50:
            break
    ET.indent(rss, space='  ')
    ET.ElementTree(rss).write(ROOT / 'rss.xml', encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    generate_rss()
