#!/usr/bin/env python3
"""Offline checks for sitemap page JSON-LD and local HTML hreflang clusters.

This does not validate Schema.org semantics, crawlability, rendered visibility or indexing.
Localized pages in this repository must be in the sitemap and use self-canonical URLs.
"""
import json
from html.parser import HTMLParser
from pathlib import Path
import re

from generate_sitemap import BASE, PAGES, ROOT, build_sitemap

LANG = re.compile(r'^(?:[a-z]{2,3}(?:-[a-z]{2}|-[0-9]{3})?|x-default)$', re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.in_json = False
        self.buffer = []
        self.json_blocks = []
        self.alternates = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'head':
            self.in_head = True
        if tag == 'link' and 'alternate' in (attrs.get('rel') or '').lower().split() and 'hreflang' in attrs:
            if not self.in_head:
                raise ValueError('hreflang link must be in head')
            self.alternates.append(((attrs.get('hreflang') or '').lower(), attrs.get('href') or ''))
        if tag == 'script' and (attrs.get('type') or '').split(';')[0].strip().lower() == 'application/ld+json':
            self.in_json = True
            self.buffer = []

    def handle_data(self, data):
        if self.in_json:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == 'head':
            self.in_head = False
        if tag == 'script' and self.in_json:
            self.json_blocks.append(''.join(self.buffer))
            self.in_json = False


def reject_constant(value):
    raise ValueError('Invalid JSON constant: ' + value)


def validate(root=ROOT, pages=None):
    pages = PAGES if pages is None else pages
    # Reuse the sitemap's canonical, robots and page existence checks.
    build_sitemap(root, pages)
    parsed = {}
    blocks = 0
    for name in pages:
        url = BASE + name
        page = Page()
        page.feed((Path(root) / (name or 'index.html')).read_text(encoding='utf-8'))
        if page.in_json:
            raise ValueError(f'{url}: unclosed JSON-LD')
        for block in page.json_blocks:
            try:
                data = json.loads(block, parse_constant=reject_constant)
            except ValueError as error:
                raise ValueError(f'{url}: invalid JSON-LD: {error}') from error
            if not isinstance(data, (dict, list)) or not data:
                raise ValueError(f'{url}: JSON-LD must be a nonempty object or array')
            blocks += 1
        mapping = {}
        for lang, href in page.alternates:
            if not LANG.fullmatch(lang) or lang in mapping:
                raise ValueError(f'{url}: invalid or duplicate hreflang {lang!r}')
            if href not in {BASE + p for p in pages}:
                raise ValueError(f'{url}: hreflang target is not a local sitemap canonical: {href!r}')
            mapping[lang] = href
        if mapping and url not in mapping.values():
            raise ValueError(f'{url}: hreflang cluster lacks self-reference')
        parsed[url] = mapping
    for url, mapping in parsed.items():
        for target in mapping.values():
            if parsed[target] != mapping:
                raise ValueError(f'{url}: hreflang cluster not reciprocal with {target}')
    return {'pages': len(pages), 'json_ld_blocks': blocks,
            'pages_with_hreflang': sum(bool(item) for item in parsed.values())}


def main():
    try:
        print(json.dumps(validate(), ensure_ascii=False, sort_keys=True))
    except (OSError, UnicodeError, ValueError) as error:
        raise SystemExit(f'SEO guard failed: {error}')


if __name__ == '__main__':
    main()
