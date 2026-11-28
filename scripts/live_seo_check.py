#!/usr/bin/env python3
"""Read-only smoke check of fixed production URLs; not an indexing or crawler audit."""
import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from generate_sitemap import BASE, PAGES, PageMetadata
from seo_guard import Page, reject_constant

MAX_BYTES = 1024 * 1024
SITEMAP_NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'


class Descriptions(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_head = False
        self.values = []

    def handle_starttag(self, tag, attrs):
        if tag == 'head':
            self.in_head = True
        attributes = dict(attrs)
        if self.in_head and tag == 'meta' and (attributes.get('name') or '').lower() == 'description':
            self.values.append((attributes.get('content') or '').strip())

    def handle_endtag(self, tag):
        if tag == 'head':
            self.in_head = False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url):
    # Fixed allowlisted URLs only. Retry one transient read, never a redirect or rate-limit.
    req = urllib.request.Request(url, headers={'User-Agent': 'SCM-News-SEO-Monitor/1.0', 'Accept': 'text/html,application/xml,text/plain'})
    for attempt in range(2):
        try:
            with urllib.request.build_opener(NoRedirect).open(req, timeout=20) as response:
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise ValueError('response too large')
                return response.status, response.headers, body
        except urllib.error.HTTPError as exc:
            # Do not retry if the server specifies any delay; never follow redirects.
            if attempt or exc.code not in (500, 502, 503, 504) or (exc.headers and exc.headers.get('Retry-After') is not None):
                raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt:
                raise
        time.sleep(2)


def generic_root_disallow(lines):
    """Detect only a clear wildcard group with Disallow: / and no Allow rule.

    Does not attempt full robots matching or determine what specific bots see.
    """
    groups = []
    agents, rules = [], []
    for line in lines:
        line = line.split('#',1)[0].strip()
        if ':' not in line:
            continue
        key, value = (part.strip() for part in line.split(':',1))
        key = key.lower()
        if key == 'user-agent':
            if rules:
                groups.append((agents,rules));agents,rules = [],[]
            agents.append(value.lower())
        elif key in ('allow','disallow') and agents:
            rules.append((key,value))
    if agents:
        groups.append((agents,rules))
    return any('*' in group and ('disallow','/') in rules and
               not any(key == 'allow' and value for key,value in rules)
               for group,rules in groups)


def has_noindex(value):
    return bool(re.search(r'(?i)(?:^|[\s,:;])(?:noindex|none)(?:$|[\s,:;])', value))


def check(fetcher=fetch, pages=None):
    pages = PAGES if pages is None else pages
    expected = {BASE + page for page in pages}
    findings = []
    def get(url):
        try:
            status, headers, body = fetcher(url)
            if status != 200:
                findings.append(f'{url}: HTTP {status}; redirect not followed')
                return None
            if len(body) > MAX_BYTES:
                findings.append(f'{url}: response too large')
                return None
            return headers, body
        except (urllib.error.URLError, OSError, ValueError, UnicodeError):
            findings.append(f'{url}: request failed or redirected')
            return None

    result = get(BASE + 'sitemap.xml')
    if result:
        try:
            body = result[1]
            if b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
                raise ValueError('DTD not supported')
            root = ET.fromstring(body)
            urls = [item.text for item in root.findall(f'{SITEMAP_NS}url/{SITEMAP_NS}loc')]
            if root.tag != SITEMAP_NS + 'urlset' or len(urls) != len(set(urls)) or set(urls) != expected:
                findings.append('sitemap.xml: URL set differs from repository or contains duplicates')
        except (ET.ParseError, ValueError):
            findings.append('sitemap.xml: invalid or unsupported XML')
    result = get(BASE + 'robots.txt')
    if result:
        try:
            lines = result[1].decode('utf-8-sig').splitlines()
            sitemap = [line.split(':', 1)[1].strip() for line in lines if re.match(r'^\s*sitemap\s*:', line, re.I)]
            if BASE + 'sitemap.xml' not in sitemap:
                findings.append('robots.txt: expected sitemap directive missing')
            if generic_root_disallow(lines):
                findings.append('robots.txt: wildcard user-agent group disallows / without an allow rule; review crawler access')
        except UnicodeError:
            findings.append('robots.txt: invalid UTF-8')

    descriptions = {}
    for url in sorted(expected):
        result = get(url)
        if not result:
            continue
        headers, body = result
        try:
            html = body.decode('utf-8-sig')
            meta, page = PageMetadata(), Page()
            meta.feed(html); page.feed(html)
            description = Descriptions()
            description.feed(html)
            if len(description.values) != 1 or not description.values[0]:
                findings.append(f'{url}: missing or duplicate meta description')
            elif description.values[0] in descriptions:
                findings.append(f'{url}: meta description duplicates {descriptions[description.values[0]]}')
            else:
                descriptions[description.values[0]] = url
            if meta.canonicals != [url] or meta.canonical_has_variant_attributes:
                findings.append(f'{url}: canonical mismatch')
            if any(has_noindex(value) for value in meta.robots):
                findings.append(f'{url}: meta robots noindex')
            # Conservative: any X-Robots-Tag noindex flags review, even if agent-specific.
            values = headers.get_all('X-Robots-Tag', []) if hasattr(headers, 'get_all') else [headers.get('X-Robots-Tag', '')]
            if any(has_noindex(value) for value in values):
                findings.append(f'{url}: X-Robots-Tag contains noindex')
            if page.in_json:
                raise ValueError('unclosed JSON-LD')
            for block in page.json_blocks:
                data = json.loads(block, parse_constant=reject_constant)
                if not isinstance(data, (dict, list)) or not data:
                    raise ValueError('invalid JSON-LD')
        except (UnicodeError, ValueError):
            findings.append(f'{url}: invalid HTML encoding or JSON-LD')
    return {'pages_expected': len(expected), 'requests_expected': len(expected) + 2, 'findings': findings}


def main():
    report = check()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['findings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
