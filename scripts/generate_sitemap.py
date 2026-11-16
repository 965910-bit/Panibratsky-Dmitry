#!/usr/bin/env python3
"""Generate a sitemap of public, canonical pages on this site only."""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://scm-news.ru/'
# Deliberately excludes local-only dashboards, verification files and noindex pages.
PAGES = ['','about.html','blog.html','scm-problems.html','career.html','contact.html','experience.html',
         'expertise.html','prompts.html','trends.html','calculators.html',
         'certificates.html','projects.html','tools.html','wiki.html','trends-logistics.html']

def generate_sitemap():
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', namespace)
    root = ET.Element(f'{{{namespace}}}urlset')
    for page in PAGES:
        if not (ROOT / (page or 'index.html')).is_file():
            raise FileNotFoundError(page)
        url = ET.SubElement(root, f'{{{namespace}}}url')
        ET.SubElement(url, f'{{{namespace}}}loc').text = BASE + page
    ET.indent(root, space='  ')
    ET.ElementTree(root).write(ROOT / 'sitemap.xml', encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    generate_sitemap()
