#!/usr/bin/env python3
"""Generate a well-formed RSS feed from the collected news."""
import json
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    from news_link_validation import valid_news_link
except ModuleNotFoundError:
    from scripts.news_link_validation import valid_news_link

ROOT = Path(__file__).resolve().parent.parent

def rss_date(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        date = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (TypeError, ValueError, OverflowError):
            return None
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return format_datetime(date.astimezone(timezone.utc))


def generate_rss():
    news = json.loads((ROOT / 'data/news.json').read_text(encoding='utf-8'))
    destination = ROOT / 'rss.xml'
    previous = None
    try:
        previous = ET.parse(destination).getroot()
    except (OSError, ET.ParseError):
        pass
    previous_date = previous.findtext('./channel/lastBuildDate') if previous is not None else None
    atom = 'http://www.w3.org/2005/Atom'
    ET.register_namespace('atom', atom)
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', 'Логистические новости'), ('link', 'https://scm-news.ru/'),
                       ('description', 'Новости логистики и управления цепями поставок'), ('language', 'ru'),
                       ('lastBuildDate', previous_date or '')]:
        ET.SubElement(channel, key).text = value
    ET.SubElement(channel, f'{{{atom}}}link', href='https://scm-news.ru/rss.xml', rel='self', type='application/rss+xml')
    seen = set()
    for item in news:
        if not isinstance(item, dict) or item.get('dead'):
            continue
        link = item.get('link', '')
        if not valid_news_link(link) or link in seen:
            continue
        seen.add(link)
        entry = ET.SubElement(channel, 'item')
        for key in ('title', 'link', 'description'):
            # XML 1.0 disallows most C0 control characters.
            value = str(item.get(key) or '')
            ET.SubElement(entry, key).text = ''.join(c for c in value if ord(c) >= 32 or c in '\t\n\r')
        date = rss_date(item.get('pubDate'))
        if date:
            ET.SubElement(entry, 'pubDate').text = date
        for tag in item.get('tags') or []:
            ET.SubElement(entry, 'category').text = ''.join(c for c in str(tag) if ord(c) >= 32 or c in '\t\n\r')
        if len(seen) == 50:
            break
    ET.indent(rss, space='  ')
    # A scheduled rebuild with identical entries is not a new publication.
    # Preserve the old bytes and timestamp, avoiding misleading freshness and noisy commits.
    if previous is not None:
        ET.indent(previous, space='  ')
        if previous_date and ET.tostring(previous, encoding='utf-8') == ET.tostring(rss, encoding='utf-8'):
            return
    channel.find('lastBuildDate').text = format_datetime(datetime.now(timezone.utc))
    ET.ElementTree(rss).write(destination, encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    generate_rss()
