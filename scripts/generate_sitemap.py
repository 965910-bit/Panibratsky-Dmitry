#!/usr/bin/env python3
"""Generate or check the sitemap of public, canonical pages on this site only."""
import argparse
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import stat
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://scm-news.ru/'
# Deliberately excludes local-only dashboards, verification files and noindex pages.
PAGES = ['','about.html','blog.html','scm-problems.html','career.html','contact.html','experience.html',
         'expertise.html','prompts.html','trends.html','calculators.html',
         'certificates.html','projects.html','business-plan.html','tools.html','wiki.html','trends-logistics.html',
         'inventory-turnover-calculator.html','safety-stock-calculator.html','reorder-point-calculator.html','scm-diagnostic.html','scm-knowledge.html','scm-encyclopedia.html','scm-practical-guides.html','scm-academy.html','scm-internal-academy.html','scm-navigator.html','scm-advanced-practice.html','scm-case-lab.html','scm-leader-map.html','scm-sector-cases.html']
# These directives are checked locally; HTTP X-Robots-Tag and other agents require live inspection.
ROBOTS_NAMES = {'robots', 'googlebot', 'googlebot-news', 'bingbot', 'yandex', 'yandexbot', 'slurp'}


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.canonicals = []
        self.canonical_has_variant_attributes = False
        self.robots = []

    def handle_starttag(self, tag, attributes):
        if tag == 'head':
            self.in_head = True
        attrs = dict(attributes)
        if self.in_head and tag == 'link' and 'canonical' in (attrs.get('rel') or '').lower().split():
            self.canonicals.append(attrs.get('href'))
            if any(attribute in attrs for attribute in ('hreflang', 'lang', 'media', 'type')):
                self.canonical_has_variant_attributes = True
        # Fail closed even if a robots directive has accidentally been placed in the body.
        if tag == 'meta' and (attrs.get('name') or '').strip().lower() in ROBOTS_NAMES:
            self.robots.append(attrs.get('content') or '')

    def handle_endtag(self, tag):
        if tag == 'head':
            self.in_head = False


def build_sitemap(root=ROOT, pages=None):
    """Validate all local pages before returning the complete XML document."""
    pages = PAGES if pages is None else pages
    if not pages or len(pages) != len(set(pages)):
        raise ValueError('Sitemap pages must be nonempty and unique')
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', namespace)
    document = ET.Element(f'{{{namespace}}}urlset')
    for page in pages:
        # Only the root and explicitly named top-level HTML files are supported.
        if not isinstance(page, str) or (page and not re.fullmatch(r'[a-z0-9-]+\.html', page)) or page == 'index.html':
            raise ValueError(f'Invalid sitemap page: {page!r}')
        path = root / (page or 'index.html')
        if not path.is_file():
            raise ValueError(f'Sitemap page missing: {page or "index.html"}')
        metadata = PageMetadata()
        metadata.feed(path.read_text(encoding='utf-8'))
        url = BASE + page
        if metadata.canonicals != [url] or metadata.canonical_has_variant_attributes:
            raise ValueError(f'{page or "index.html"}: expected exactly one matching canonical')
        for directive in metadata.robots:
            tokens = {token.lower() for token in re.split(r'[\s,]+', directive) if token}
            if tokens & {'noindex', 'none'}:
                raise ValueError(f'{page or "index.html"}: conflicting noindex directive')
        entry = ET.SubElement(document, f'{{{namespace}}}url')
        ET.SubElement(entry, f'{{{namespace}}}loc').text = url
    ET.indent(document, space='  ')
    return ET.tostring(document, encoding='utf-8', xml_declaration=True)


def generate_sitemap(root=ROOT, pages=None, check=False):
    content = build_sitemap(root, pages)
    target = root / 'sitemap.xml'
    if check:
        if not target.is_file() or target.read_bytes() != content:
            raise ValueError('sitemap.xml is missing or differs from the generated sitemap')
        return
    # Never replace the previous sitemap until validation and the complete write succeed.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=root, delete=False) as output:
            temporary = output.name
            output.write(content)
        os.chmod(temporary, stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644)
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='validate without writing files')
    args = parser.parse_args()
    try:
        generate_sitemap(check=args.check)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f'Sitemap validation failed: {error}\n')
    print('Sitemap validated; no files written.' if args.check else 'Sitemap generated.')


if __name__ == '__main__':
    main()
