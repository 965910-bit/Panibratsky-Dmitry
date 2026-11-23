import importlib.util
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit, unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SiteTests(unittest.TestCase):
    def test_internal_reports_excluded_from_pages(self):
        config = (ROOT / '_config.yml').read_text(encoding='utf-8')
        self.assertIn('  - audit\n', config)
        for report in ROOT.glob('*.md'):
            if report.name != 'README.md':
                self.assertIn('  - "' + report.name + '"', config, report.name)

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

    def test_sitemap_pages_use_executive_navigation(self):
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for item in ET.parse(ROOT / 'sitemap.xml').findall('.//s:loc', ns):
            filename = urlsplit(item.text).path.lstrip('/') or 'index.html'
            html = (ROOT / filename).read_text(encoding='utf-8')
            if filename == 'index.html':
                css = (ROOT / 'css/executive.css').read_text(encoding='utf-8')
                self.assertIn('<!-- HOME_STYLES_START -->\n<style>\n' + css + '\n</style>\n<!-- HOME_STYLES_END -->', html)
                continue
            for required in ('css/executive-pages.css', 'js/executive-theme.js', 'js/executive-pages.js',
                             'class="executive-brand"', 'class="executive-menu"', 'class="executive-theme"',
                             'href="about.html"', 'href="career.html"'):
                self.assertIn(required, html, f'{filename}: {required}')
            self.assertIn('id="main"' if filename == 'scm-problems.html' else 'id="page-content"', html)

    def test_sitemap_heading_and_structured_data(self):
        import re
        import json
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for element in ET.parse(ROOT / 'sitemap.xml').findall('.//s:loc', ns):
            path = ROOT / (urlsplit(element.text).path.lstrip('/') or 'index.html')
            html = path.read_text(encoding='utf-8')
            self.assertEqual(len(re.findall(r'<h1\b', html, re.I)), 1, path.name)
            for match in re.findall(r'<script\s+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.I | re.S):
                json.loads(match)

    def test_sitemap_static_internal_links_and_anchor_ids(self):
        # Source-only check: no dynamic DOM, runtime URLs, HTTP status, or visibility checks.
        class Targets(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.ids, self.names, self.hrefs = [], [], []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if attrs.get('id'): self.ids.append(attrs['id'])
                if tag == 'a':
                    if attrs.get('name'): self.names.append(attrs['name'])
                    if attrs.get('href'): self.hrefs.append(attrs['href'])

        generator = load_script('generate_sitemap')
        parsed = {}
        def read_page(path):
            if path not in parsed:
                parser = Targets()
                parser.feed(path.read_text(encoding='utf-8'))
                parsed[path] = parser
            return parsed[path]

        for page in generator.PAGES:
            name = page or 'index.html'
            source = ROOT / name
            content = read_page(source)
            self.assertEqual(len(content.ids), len(set(content.ids)), f'{name}: duplicate id')
            for href in content.hrefs:
                link = urlsplit(urljoin(generator.BASE + page, href))
                if link.scheme not in ('http', 'https') or link.hostname != 'scm-news.ru':
                    continue
                path = (ROOT / (unquote(link.path).lstrip('/') or 'index.html')).resolve()
                self.assertTrue(path.is_relative_to(ROOT.resolve()), f'{name}: {href}')
                self.assertTrue(path.is_file(), f'{name}: missing target {href}')
                if link.fragment and path.suffix == '.html':
                    target = read_page(path)
                    self.assertIn(unquote(link.fragment), target.ids + target.names, f'{name}: missing anchor {href}')

    def test_corporate_training_offer_is_reachable_and_terms_are_discussed(self):
        home = (ROOT / 'index.html').read_text(encoding='utf-8')
        expertise = (ROOT / 'expertise.html').read_text(encoding='utf-8')
        self.assertIn('href="expertise.html#corporate-training"', home)
        self.assertIn('id="corporate-training"', expertise)
        for text in ('Корпоративное обучение команд', 'большой команды',
                     'Возможны разные форматы обучения', 'количество участников',
                     'стоимость согласовываются отдельно', 'Обсудить обучение команды',
                     'mailto:dmitry.gerasimov.2026@yandex.ru?subject='):
            self.assertIn(text, expertise)

    def test_book_concept_is_visible_and_uses_local_image(self):
        home = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertIn('id="book"', home)
        self.assertIn('Мост в цифровое будущее', home)
        self.assertIn('Маршрут от задачи к результату', home)
        self.assertIn('КОНЦЕПТ ОБЛОЖЕК', home)
        self.assertIn('src="images/book-concept-bridge.webp"', home)
        self.assertTrue((ROOT / 'images/book-concept-bridge.webp').is_file())

    def test_wiki_planned_material_is_not_claimed_as_published(self):
        text = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        self.assertGreater(text.count('class="wiki-article-card"'), 0)
        self.assertIn('не опубликованные статьи', text)
        self.assertIn('<details class="wiki-planned">', text)
        self.assertIn('href="scm-encyclopedia.html"', text)
        self.assertEqual(text.count('class="wiki-article-card"'), text.count('Материал готовится к публикации.'))
        self.assertNotIn('Статей и материалов</div>', text)
        self.assertNotIn('Практическая применимость</div>', text)
        self.assertNotIn('<span class="read-time">', text)
        self.assertNotIn('<span class="article-level ', text)
        for page in ('wiki.html', 'tools.html', 'projects.html', 'certificates.html', 'calculators.html'):
            html = (ROOT / page).read_text(encoding='utf-8')
            self.assertNotIn('успешная реализация</div>', html)
            self.assertNotIn('реализованных проектов</div>', html)
        self.assertNotIn('管理系统', (ROOT / 'tools.html').read_text(encoding='utf-8'))

    def test_answer_first_boundaries_are_visible_in_html(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        calculators = (ROOT / 'calculators.html').read_text(encoding='utf-8')
        career = (ROOT / 'career.html').read_text(encoding='utf-8')
        research = (ROOT / 'scm-problems.html').read_text(encoding='utf-8')
        news = (ROOT / 'trends.html').read_text(encoding='utf-8')
        self.assertIn('Что доступно в базе знаний?</h2>\n            <p>Откройте <a href="scm-encyclopedia.html">', wiki)
        self.assertIn('Для чего нужны эти калькуляторы?</h2>\n            <p>Расчётные модели', calculators)
        self.assertIn('Какие возможности рассматриваю</h2>\n<p>Рассматриваю постоянную руководящую работу', career)
        self.assertIn('Что стоит за операционными сбоями?</h2><p>', research)
        self.assertIn('<summary class="faq-question">Откуда берутся новости на сайте?</summary>', news)

    def test_person_profile_entity_is_consistent_and_visible(self):
        def structured(filename):
            text = (ROOT / filename).read_text(encoding='utf-8')
            return text, [json.loads(match) for match in re.findall(r'<script\s+type="application/ld\+json"[^>]*>(.*?)</script>', text, re.I | re.S)]
        homepage, home_data = structured('index.html')
        about, about_data = structured('about.html')
        person = next(item for item in home_data if item.get('@type') == 'Person')
        profile = next(item for item in about_data if item.get('@type') == 'ProfilePage')
        self.assertEqual(person['@id'], 'https://scm-news.ru/#person')
        self.assertEqual(profile['mainEntity']['@id'], person['@id'])
        self.assertEqual(profile['mainEntity']['name'], person['name'])
        self.assertIn(person['name'], about)
        self.assertEqual(person['sameAs'], ['https://set.ki/EYUBwz5'])
        self.assertIn(person['sameAs'][0], homepage)
        self.assertEqual(profile['url'], 'https://scm-news.ru/about.html')

    def test_trends_chart_is_versioned_local_with_license_and_audit(self):
        page = (ROOT / 'trends.html').read_text(encoding='utf-8')
        package = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
        self.assertEqual(package['dependencies']['chart.js'], '4.5.1')
        self.assertIn('src="js/vendor/chart.umd-4.5.1.js"', page)
        self.assertNotIn('cdn.jsdelivr.net/npm/chart.js', page)
        self.assertIn('Chart.js v4.5.1', (ROOT / 'js/vendor/chart.umd-4.5.1.js').read_text(encoding='utf-8')[:200])
        self.assertIn('MIT License', (ROOT / 'js/vendor/chartjs-LICENSE.md').read_text(encoding='utf-8'))
        workflow = (ROOT / '.github/workflows/site-tests.yml').read_text(encoding='utf-8')
        self.assertIn('npm ci --ignore-scripts', workflow)
        self.assertIn('npm audit --audit-level=high', workflow)
        self.assertIn('cmp node_modules/chart.js/dist/chart.umd.js js/vendor/chart.umd-4.5.1.js', workflow)
        dependabot = (ROOT / '.github/dependabot.yml').read_text(encoding='utf-8')
        self.assertIn('package-ecosystem: npm', dependabot)
        self.assertIn('package-ecosystem: github-actions', dependabot)

    def test_unpinned_chart_is_replaced_with_the_verified_local_build(self):
        for filename, expected in (
            ('admin.html', 'js/vendor/chart.umd-4.5.1.js'),
            ('scm-platform/dashboard.html', '../js/vendor/chart.umd-4.5.1.js'),
            ('scm-platform/kpi-center.html', '../js/vendor/chart.umd-4.5.1.js'),
        ):
            page = ROOT / filename
            text = page.read_text(encoding='utf-8')
            self.assertIn(f'<script src="{expected}"></script>', text, filename)
            self.assertEqual((page.parent / expected).resolve(), (ROOT / 'js/vendor/chart.umd-4.5.1.js').resolve())
            self.assertLess(text.index(expected), text.index('new Chart('), filename)
        root_kpi = (ROOT / 'kpi-center.html').read_text(encoding='utf-8')
        self.assertNotIn('chart.js', root_kpi.lower())
        self.assertNotIn('new Chart(', root_kpi)
        for page in list(ROOT.glob('*.html')) + list((ROOT / 'scm-platform').rglob('*.html')):
            self.assertNotIn('https://cdn.jsdelivr.net/npm/chart.js"', page.read_text(encoding='utf-8'), str(page))

    def test_news_paused_status_is_visible_and_matches_faq_markup(self):
        text = (ROOT / 'trends.html').read_text(encoding='utf-8')
        self.assertEqual(text.count('<details class="faq-item">'), 5)
        self.assertEqual(text.count('<summary class="faq-question">'), 5)
        self.assertNotIn("querySelectorAll('.faq-question')", text)
        self.assertIn('Добавление новых материалов приостановлено до проверки условий источников', text)
        self.assertIn('Новые материалы пока не собираются.', text)
        self.assertIn('Сохранённая лента загружена в', text)
        self.assertIn('Публикации из сохранённой ленты за последние 30 дней', text)
        self.assertNotIn('сбор новостей запускается примерно каждые 30 минут', text.lower())
        self.assertNotIn('сбор новых материалов запускается примерно каждые 30 минут', text.lower())
        blocks = [json.loads(x) for x in re.findall(r'<script\s+type="application/ld\+json"[^>]*>(.*?)</script>', text, re.I | re.S)]
        faq = next(block for block in blocks if block.get('@type') == 'FAQPage')
        for question in faq['mainEntity']:
            self.assertIn(question['acceptedAnswer']['text'], text)
        self.assertIn('приостановлено', faq['mainEntity'][0]['acceptedAnswer']['text'])
        self.assertIn('приостановлено', faq['mainEntity'][3]['acceptedAnswer']['text'])

    def test_unverified_forecasts_and_course_links_are_not_presented_as_facts(self):
        news = (ROOT / 'trends.html').read_text(encoding='utf-8')
        overview = (ROOT / 'trends-logistics.html').read_text(encoding='utf-8')
        plan = (ROOT / 'business-plan.html').read_text(encoding='utf-8')
        for text in ('Прогноз Gartner:', '$620 млрд', 'Записаться на курс →'):
            self.assertNotIn(text, news)
        self.assertIn('временно сняты до проверки источников', overview)
        self.assertNotIn('42% крупных компаний внедрили AI', overview)
        for section in ('logistics', 'personnel', 'academy', 'strategy'):
            self.assertIn('id="' + section + '"', overview)
            self.assertIn('id="' + section + '-2024"', overview)
        self.assertIn('Архивный проект, версия 2024 года', plan)
        self.assertIn('не являются гарантией результата', plan)
        self.assertNotIn('Текущий прогресс: 3,000 пользователей', plan)

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

    def test_rss_unchanged_content_preserves_timestamp_and_bytes(self):
        generator = load_script('generate_rss')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            news_file = root / 'data/news.json'
            news = [{'title': 'Old', 'link': 'https://example.com/old', 'pubDate': ''}]
            news_file.write_text(json.dumps(news), encoding='utf-8')
            generator.ROOT = root
            generator.generate_rss()
            feed = root / 'rss.xml'
            tree = ET.parse(feed)
            tree.find('./channel/lastBuildDate').text = 'Mon, 01 Jan 2024 00:00:00 +0000'
            tree.write(feed, encoding='utf-8', xml_declaration=True)
            previous = feed.read_bytes()
            generator.generate_rss()
            self.assertEqual(feed.read_bytes(), previous)
            news[0]['title'] = 'Updated'
            news_file.write_text(json.dumps(news), encoding='utf-8')
            generator.generate_rss()
            updated = ET.parse(feed)
            self.assertEqual(updated.findtext('./channel/item/title'), 'Updated')
            self.assertNotEqual(updated.findtext('./channel/lastBuildDate'), 'Mon, 01 Jan 2024 00:00:00 +0000')

    def test_rss_missing_or_malformed_previous_file_is_regenerated(self):
        generator = load_script('generate_rss')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            (root / 'data/news.json').write_text('[]', encoding='utf-8')
            generator.ROOT = root
            for previous in (None, '<not-xml'):
                feed = root / 'rss.xml'
                if previous is not None:
                    feed.write_text(previous, encoding='utf-8')
                generator.generate_rss()
                self.assertIsNotNone(ET.parse(feed).find('./channel/lastBuildDate'))

    def test_rss_omits_missing_dates_and_normalizes_iso(self):
        generator = load_script('generate_rss')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            news = [{'title': 'No date', 'link': 'https://example.com/undated', 'pubDate': ''},
                    {'title': 'ISO', 'link': 'https://example.com/iso', 'pubDate': '2026-11-15T12:00:00+03:00'}]
            (root / 'data/news.json').write_text(json.dumps(news), encoding='utf-8')
            generator.ROOT = root
            generator.generate_rss()
            items = ET.parse(root / 'rss.xml').findall('./channel/item')
            self.assertIsNone(items[0].find('pubDate'))
            self.assertEqual(items[1].findtext('pubDate'), 'Sun, 15 Nov 2026 09:00:00 +0000')

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

    def test_employer_page_clarifies_scope_results_and_direct_contact(self):
        home = (ROOT / 'index.html').read_text(encoding='utf-8')
        page = (ROOT / 'career.html').read_text(encoding='utf-8')
        self.assertIn('href="career.html">Для работодателя', home)
        for text in ('Масштаб и зоны ответственности', 'Примеры результатов',
                     'Это сумма дефекта, а не оценка экономии', 'Показатели приведены по данным резюме',
                     'Постоянная руководящая работа', 'href="tel:+79825810787"',
                     'mailto:dmitry.gerasimov.2026@yandex.ru?subject='):
            self.assertIn(text, page)
        self.assertNotIn('scm-news.ru/resume/', page)

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
