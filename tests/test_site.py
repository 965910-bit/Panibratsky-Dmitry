import importlib.util
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import urlsplit, unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SiteTests(unittest.TestCase):
    def test_sitemap_is_valid_local_and_canonical(self):
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = [e.text for e in ET.parse(ROOT / 'sitemap.xml').findall('.//s:loc', ns)]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertIn('https://scm-news.ru/', urls)
        for url in urls:
            parsed = urlsplit(url)
            self.assertEqual((parsed.scheme, parsed.netloc), ('https', 'scm-news.ru'))
            path = ROOT / (parsed.path.lstrip('/') or 'index.html')
            self.assertTrue(path.is_file(), url)
            html = path.read_text(encoding='utf-8')
            self.assertNotRegex(html.lower(), r'content=["\'][^"\']*noindex')
            self.assertIn('href="' + url + '"', html)

    def test_public_business_plan_discovery(self):
        page = (ROOT / 'business-plan.html').read_text(encoding='utf-8')
        self.assertIn('href="https://scm-news.ru/business-plan.html"', page)
        for field in ('name="description"', 'property="og:title"', 'property="og:description"', 'property="og:url"'):
            self.assertIn(field, page)
        for source in ('projects.html', 'tools.html'):
            self.assertIn('href="business-plan.html"', (ROOT / source).read_text(encoding='utf-8'))
        self.assertIn('business-plan.html', load_script('generate_sitemap').PAGES)
        self.assertIn('https://scm-news.ru/business-plan.html', (ROOT / 'sitemap.xml').read_text(encoding='utf-8'))

    def test_rss_is_xml_and_urls_are_valid(self):
        items = ET.parse(ROOT / 'rss.xml').findall('./channel/item')
        self.assertTrue(items)
        links = [item.findtext('link') for item in items]
        self.assertEqual(len(links), len(set(links)))
        for link in links:
            self.assertIn(urlsplit(link).scheme, ('http', 'https'))

    def test_generator_escapes_untrusted_xml_and_deduplicates(self):
        generator = load_script('generate_rss')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            item = {'title': 'a & <b> ]]> "', 'link': 'https://example.com/?a=1&b=2',
                    'description': 'Text & more', 'pubDate': 'Mon, 16 Nov 2026 00:00:00 +0000', 'tags': ['A & B']}
            (root / 'data/news.json').write_text(json.dumps([item, item]), encoding='utf-8')
            generator.ROOT = root
            generator.generate_rss()
            items = ET.parse(root / 'rss.xml').findall('./channel/item')
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].findtext('title'), item['title'])
            self.assertEqual(items[0].findtext('link'), item['link'])
            self.assertEqual(items[0].findtext('category'), 'A & B')

    def test_mobile_navigation_and_news_content(self):
        news = (ROOT / 'trends.html').read_text(encoding='utf-8')
        self.assertIn('.fade-up { opacity: 1; transform: none; }', news)
        self.assertIn('aria-controls="nav-menu"', news)
        for name in ('auditor', 'inventory-methodology', 'kpi-center', 'library'):
            html = (ROOT / (name + '.html')).read_text(encoding='utf-8')
            self.assertIn('class="mobile-app-menu"', html, name)
            self.assertIn('css/mobile-app.css', html, name)
        common = (ROOT / 'scm-platform/scm-common.js').read_text(encoding='utf-8')
        self.assertIn("toggleBtn.setAttribute('aria-expanded'", common)
        self.assertIn("toggleBtn.textContent = '☰ Разделы'", common)

    def test_required_assets_exist(self):
        for path in ('css/portfolio-menu.css', 'js/portfolio-menu.js',
                     'icons/android/launchericon-192x192.png', 'icons/android/launchericon-512x512.png'):
            self.assertTrue((ROOT / path).is_file(), path)
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        self.assertEqual(manifest['start_url'], '/')
        for icon in manifest['icons']:
            self.assertTrue((ROOT / icon['src']).is_file(), icon['src'])

    def test_static_internal_links_resolve(self):
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.urls = []
            def handle_starttag(self, tag, attrs):
                self.urls.extend(value for key, value in attrs if key in ('href', 'src') and value)
        files = list(ROOT.glob('*.html')) + list((ROOT / 'scm-platform').glob('*.html'))
        for file in files:
            parser = Links()
            parser.feed(file.read_text(encoding='utf-8'))
            for url in parser.urls:
                parts = urlsplit(url)
                if parts.scheme or parts.netloc or not parts.path or '${' in parts.path:
                    continue
                target = ((ROOT if parts.path.startswith('/') else file.parent) /
                          unquote(parts.path.lstrip('/')))
                self.assertTrue(target.exists(), f'{file.name}: {url}')

    def test_portfolio_navigation_and_resume_privacy(self):
        home = (ROOT / 'index.html').read_text(encoding='utf-8')
        for link in ('about.html', 'career.html', 'blog.html', 'experience.html'):
            self.assertIn('href="' + link + '"', home)
        self.assertRegex(home, r'<h1>Герасимов<br>Дмитрий')
        about = (ROOT / 'about.html').read_text(encoding='utf-8')
        self.assertNotRegex(about, r'\b41\s+год\b')
        self.assertNotIn('ТВОЯ_СТРАНИЦА', about)
        experience = (ROOT / 'experience.html').read_text(encoding='utf-8')
        self.assertIn('Март 2024 — Июль 2025</div><h3 class="exp-company">Лемана ПРО', experience)
        self.assertIn('Март 2020 — Март 2024</div><h3 class="exp-company">Леруа Мерлен', experience)
        self.assertIn('/resume/', (ROOT / '.gitignore').read_text(encoding='utf-8'))

    def test_research_page_navigation_sources_and_sitemap(self):
        class Document(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = set()
                self.links = []
                self.h1_count = 0
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if attrs.get('id'):
                    self.ids.add(attrs['id'])
                if tag == 'a' and attrs.get('href'):
                    self.links.append(attrs['href'])
                if tag == 'h1':
                    self.h1_count += 1
        page = ROOT / 'scm-problems.html'
        document = Document()
        document.feed(page.read_text(encoding='utf-8'))
        self.assertEqual(document.h1_count, 1)
        for href in document.links:
            if href.startswith('#'):
                self.assertIn(href[1:], document.ids, href)
        self.assertGreaterEqual(sum(url.startswith('https://') for url in document.links), 8)
        for name in ('index.html', 'blog.html'):
            self.assertIn('href="scm-problems.html"', (ROOT / name).read_text(encoding='utf-8'))
        generator = load_script('generate_sitemap')
        self.assertIn('scm-problems.html', generator.PAGES)
        self.assertIn('https://scm-news.ru/scm-problems.html', (ROOT / 'sitemap.xml').read_text())

    def test_no_previous_surname_in_public_text_or_paths(self):
        # Exclude the local, ignored private archive and Git history; neither is a site asset.
        names = ('\u043f\u0430\u043d\u0438\u0431\u0440\u0430\u0442', 'pani' + 'brat')
        extensions = {'.html', '.htm', '.js', '.css', '.json', '.xml', '.txt', '.md', '.py', '.yml', '.yaml'}
        for file in ROOT.rglob('*'):
            rel = file.relative_to(ROOT)
            if any(part in {'.git', 'resume', 'node_modules', '__pycache__'} for part in rel.parts):
                continue
            self.assertFalse(any(name in str(rel).lower() for name in names), str(rel))
            if file.is_file() and file.suffix.lower() in extensions:
                text = file.read_text(encoding='utf-8').lower()
                self.assertFalse(any(name in text for name in names), str(rel))

    def test_no_prefilled_password(self):
        html = (ROOT / 'login.html').read_text()
        password = re.search(r'<input\b[^>]*type="password"[^>]*>', html).group()
        self.assertNotRegex(password, r'\bvalue\s*=')


if __name__ == '__main__':
    unittest.main()
