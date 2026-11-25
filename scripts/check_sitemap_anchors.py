#!/usr/bin/env python3
"""Check explicit local fragment links between sitemap pages (not rendered DOM or HTTP)."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from generate_sitemap import BASE, PAGES, ROOT


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a':
            if attrs.get('name'):
                self.ids.add(attrs['name'])
            if attrs.get('href'):
                self.links.append(attrs['href'])


def check(root=ROOT, pages=PAGES):
    parsed = {}
    for name in pages:
        page = Page()
        page.feed((Path(root) / (name or 'index.html')).read_text(encoding='utf-8'))
        parsed['/' + name] = page
    if '/' in parsed:
        parsed['/index.html'] = parsed['/']
    failures = []
    for name in pages:
        for href in parsed['/' + name].links:
            target = urlsplit(urljoin(BASE + name, href))
            if (target.scheme == 'https' and target.netloc == urlsplit(BASE).netloc and target.fragment
                    and target.path in parsed and unquote(target.fragment) not in parsed[target.path].ids):
                failures.append((name or 'index.html', href))
    return failures


if __name__ == '__main__':
    problems = check()
    if problems:
        for source, href in problems:
            print(f'{source}: missing static anchor: {href}')
        raise SystemExit(1)
    print(f'Explicit local fragment links between {len(PAGES)} sitemap pages: OK')
