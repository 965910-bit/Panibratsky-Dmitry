#!/usr/bin/env python3
"""Render a small, escaped news snapshot for users and crawlers without JS."""
import html
import json
from pathlib import Path
try:
    from news_link_validation import valid_news_link
except ModuleNotFoundError:
    from scripts.news_link_validation import valid_news_link

ROOT = Path(__file__).resolve().parent.parent
START = '<!-- NEWS_SNAPSHOT_START -->'
END = '<!-- NEWS_SNAPSHOT_END -->'


def generate():
    page = ROOT / 'trends.html'
    source = page.read_text(encoding='utf-8')
    if source.count(START) != 1 or source.count(END) != 1:
        raise ValueError('Expected exactly one pair of snapshot markers')
    items = json.loads((ROOT / 'data/news.json').read_text(encoding='utf-8'))
    articles = []
    seen = set()
    for item in items:
        if not isinstance(item, dict) or item.get('dead'):
            continue
        url = item.get('link')
        if not valid_news_link(url) or url in seen:
            continue
        seen.add(url)
        title = html.escape(str(item.get('title') or 'Новость'))
        description = html.escape(str(item.get('description') or ''))
        source_name = html.escape(str(item.get('source') or ''))
        articles.append(f'<article class="news-item"><h3 class="news-title"><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{title}</a></h3><p class="news-source">{source_name}</p><p class="news-description">{description}</p></article>')
        if len(articles) == 10:
            break
    snapshot = '\n' + '\n'.join(articles) + '\n' if articles else '\n<p>Новости временно недоступны.</p>\n'
    before, rest = source.split(START, 1)
    _, after = rest.split(END, 1)
    page.write_text(before + START + snapshot + END + after, encoding='utf-8')

if __name__ == '__main__':
    generate()
