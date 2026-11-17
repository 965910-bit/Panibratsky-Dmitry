#!/usr/bin/env python3
"""Inventory static HTML only; not a CSP policy, runtime trace, or security guarantee."""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from generate_sitemap import BASE, PAGES, ROOT


class StaticInventory(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.origins = {k: set() for k in ('script', 'style', 'image', 'frame')}
        self.counts = {'inline_scripts': 0, 'inline_handlers': 0,
                       'inline_style_attributes': 0, 'inline_style_blocks': 0}
        self.inline_script = False
        self.script_has_content = False

    def resource(self, kind, raw):
        if not raw:
            return
        try:
            target = urlsplit(urljoin(self.base, raw))
            home = urlsplit(self.base)
            if target.scheme not in ('http', 'https') or not target.hostname:
                return
            # Never print paths, query strings, credentials, or fragments.
            port = target.port
            origin = f'{target.scheme}://{target.hostname}' + (f':{port}' if port else '')
            local = (target.scheme, target.hostname, port) == (home.scheme, home.hostname, home.port)
            if not local:
                self.origins[kind].add(origin)
        except ValueError:
            return

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.counts['inline_handlers'] += sum(1 for key, value in attrs.items() if key.startswith('on') and value)
        if attrs.get('style'):
            self.counts['inline_style_attributes'] += 1
        if tag == 'style':
            self.counts['inline_style_blocks'] += 1
        if tag == 'script':
            self.resource('script', attrs.get('src'))
            script_type = (attrs.get('type') or '').strip().lower()
            self.inline_script = 'src' not in attrs and script_type in ('', 'text/javascript', 'application/javascript', 'module')
            self.script_has_content = False
        elif tag == 'link' and 'stylesheet' in (attrs.get('rel') or '').lower().split():
            self.resource('style', attrs.get('href'))
        elif tag == 'img':
            self.resource('image', attrs.get('src'))
        elif tag in ('iframe', 'frame'):
            self.resource('frame', attrs.get('src'))

    def handle_data(self, data):
        if self.inline_script and data.strip():
            self.script_has_content = True

    def handle_endtag(self, tag):
        if tag == 'script':
            if self.inline_script and self.script_has_content:
                self.counts['inline_scripts'] += 1
            self.inline_script = False
            self.script_has_content = False


def inventory(root=ROOT, pages=PAGES):
    total = {k: 0 for k in ('inline_scripts', 'inline_handlers', 'inline_style_attributes', 'inline_style_blocks')}
    origins = {k: set() for k in ('script', 'style', 'image', 'frame')}
    results = []
    for page in pages:
        filename = page or 'index.html'
        parsed = StaticInventory(BASE + page)
        parsed.feed((Path(root) / filename).read_text(encoding='utf-8'))
        for key in total:
            total[key] += parsed.counts[key]
        for key in origins:
            origins[key].update(parsed.origins[key])
        results.append({'file': filename, **parsed.counts,
                        'external_origins': {k: sorted(v) for k, v in parsed.origins.items()}})
    return {'scope': 'sitemap HTML only; no CSS URLs, srcset, JS-created resources, network requests, worker, connect-src or runtime DOM',
            'pages': len(results), 'totals': total,
            'external_origins': {k: sorted(v) for k, v in origins.items()}, 'files': results}


if __name__ == '__main__':
    print(json.dumps(inventory(), ensure_ascii=False, indent=2))
