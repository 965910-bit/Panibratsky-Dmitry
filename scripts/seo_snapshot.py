#!/usr/bin/env python3
"""Snapshot local sitemap pages and static HTML links; no network or JS execution."""
from collections import Counter, deque
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit, unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://scm-news.ru/'

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''; self.description = ''; self.h1 = []; self.json_ld = []; self.canonical = []; self.robots = []; self.links = []
        self.capture = None; self.buffer = ''
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'title' or tag == 'h1' or (tag == 'script' and a.get('type', '').lower() == 'application/ld+json'):
            self.capture, self.buffer = tag, ''
        if tag == 'meta' and a.get('name', '').lower() == 'description': self.description = a.get('content', '')
        if tag == 'meta' and a.get('name', '').lower() == 'robots': self.robots.append(a.get('content', ''))
        if tag == 'link' and 'canonical' in a.get('rel', '').lower().split(): self.canonical.append(a.get('href', ''))
        if tag == 'a' and 'href' in a: self.links.append(a['href'])
    def handle_data(self, data):
        if self.capture: self.buffer += data
    def handle_endtag(self, tag):
        if tag != self.capture: return
        if tag == 'title': self.title = self.buffer.strip()
        elif tag == 'h1': self.h1.append(self.buffer.strip())
        else:
            try: self.json_ld.append({'valid_json': True, 'data': json.loads(self.buffer)})
            except json.JSONDecodeError: self.json_ld.append({'valid_json': False})
        self.capture = None

def target(href, source):
    p = urlsplit(href)
    if p.scheme not in ('', 'https', 'http') or p.netloc not in ('', 'scm-news.ru'): return None
    if not p.path: return source
    path = unquote(p.path)
    if not path.startswith('/'): path = '/' + str(Path(source.lstrip('/')).parent / path)
    parts = []
    for part in path.split('/'):
        if part == '..':
            if parts: parts.pop()
        elif part not in ('', '.'): parts.append(part)
    path = '/' + '/'.join(parts)
    return '/' if path in ('/', '/index.html') else path

def main():
    paths = subprocess.check_output(['git', 'ls-files', '*.html'], cwd=ROOT, text=True).splitlines()
    paths = [p for p in paths if '/' not in p or p.startswith('scm-platform/')]
    pages = {}
    for filename in paths:
        path = ROOT / filename
        if not path.is_file(): continue
        key = '/' if filename == 'index.html' else '/' + filename
        parser = Page(); parser.feed(path.read_text(encoding='utf-8')); pages[key] = (filename, parser)
    incoming = {p: Counter() for p in pages}; graph = {}
    for source, (_, parser) in pages.items():
        destinations = [target(h, source) for h in parser.links]
        graph[source] = set()
        for dest in destinations:
            if dest in pages and dest != source:
                incoming[dest][source] += 1; graph[source].add(dest)
    distances = {'/': 0}; queue = deque(['/'])
    while queue:
        source = queue.popleft()
        for dest in graph.get(source, ()):
            if dest not in distances: distances[dest] = distances[source] + 1; queue.append(dest)
    root = ET.parse(ROOT / 'sitemap.xml').getroot(); results = []
    for element in root:
        url = element[0].text; key = target(url, '/')
        filename, p = pages[key]; counts = incoming[key]
        results.append({'url': url, 'file': filename, 'title': p.title, 'title_characters': len(p.title), 'description': p.description, 'description_characters': len(p.description), 'h1_count': len(p.h1), 'h1_text': p.h1, 'json_ld': p.json_ld, 'canonical': p.canonical, 'robots_meta': p.robots, 'incoming_internal_links': sum(counts.values()), 'incoming_unique_source_pages': len(counts), 'incoming_sources': sorted(counts), 'crawl_depth_from_home': distances.get(key), 'html_bytes': (ROOT / filename).stat().st_size})
    output = {'generated_utc_date': datetime.now(timezone.utc).date().isoformat(), 'scope': 'tracked top-level and scm-platform HTML; local source only; links in static a href, self-links excluded; /index.html normalized to /; no network or JS', 'html_files_scanned': len(pages), 'sitemap_urls': len(results), 'html_files_without_incoming_links': sum(not x for x in incoming.values()), 'pages': results}
    (ROOT / 'audit/after-snapshot.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__': main()
