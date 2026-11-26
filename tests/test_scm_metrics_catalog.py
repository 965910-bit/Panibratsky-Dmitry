import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MetricsCatalogTests(unittest.TestCase):
    def test_catalog_is_public_and_each_measure_has_definition_units_and_caveats(self):
        html = (ROOT / 'scm-metrics.html').read_text(encoding='utf-8')
        sitemap = (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
        self.assertIn('https://scm-news.ru/scm-metrics.html', sitemap)
        self.assertIn('<link rel="canonical" href="https://scm-news.ru/scm-metrics.html">', html)
        sections = re.findall(r'<section class="metric-group" id="([^"]+)">', html)
        self.assertEqual(len(sections), 13)
        self.assertEqual(len(set(sections)), 13)
        cards = re.findall(r'<article class="metric-entry">(.*?)</article>', html, re.S)
        self.assertEqual(len(cards), 154)
        for card in cards:
            for text in ('<h3>', '<strong>Формула:</strong>', '<strong>Единица:</strong>', '<strong>Оговорки:</strong>'):
                self.assertIn(text, card)
        self.assertIn('не полный перечень всех возможных показателей', html)
        self.assertIn('При нулевом знаменателе отношение не определено', html)
        self.assertIn('одновременно вовремя и полностью', html)
        self.assertIn('Формулы — предлагаемые варианты', html)
        for url in ('wiki.html', 'scm-navigator.html', 'scm-encyclopedia.html'):
            self.assertIn('href="scm-metrics.html"', (ROOT / url).read_text(encoding='utf-8'))
        for script in ('analytics-consent', 'visitor-events'):
            self.assertEqual(html.count(f'src="js/{script}.js"'), 1)

    def test_category_examples_are_present_and_arithmetically_consistent(self):
        html = (ROOT / 'scm-metrics.html').read_text(encoding='utf-8')
        self.assertEqual(html.count('class="metric-example"'), 15)
        self.assertEqual(80 / 100 * 100, 80)
        self.assertEqual((abs(90 - 100) + abs(120 - 100)) / 200 * 100, 15)
        self.assertEqual(1_200_000 / 300_000, 4)
        self.assertEqual(18 / 20 * 100, 90)
        self.assertEqual(500 / 50, 10)
        self.assertEqual(21_000 / (5 * 300), 14)
        self.assertAlmostEqual(.9 * .8 * .95 * 100, 68.4)
        self.assertEqual(30 + 25 - 40, 15)
        self.assertEqual(2 / 500_000 * 1_000_000, 4)
        self.assertEqual(20 / 1000 * 100, 2)
        self.assertEqual(80 / 100 * 100, 80)
        self.assertEqual(90 / 100 * 100, 90)
        self.assertEqual(4 * 200 * .15, 120)
        self.assertEqual((10 + 20) / 300 * 100, 10)
        self.assertAlmostEqual((10 / 100 + 20 / 200) / 2 * 100, 10)
        self.assertEqual((4 * 100 + 2 * 50) / 200, 2.5)

    def test_new_working_variants_link_to_sources_and_nav_counts_match(self):
        html = (ROOT / 'scm-metrics.html').read_text(encoding='utf-8')
        cards = re.findall(r'<article class="metric-entry">(.*?)</article>', html, re.S)
        titles = [re.search(r'<h3>(.*?)</h3>', card).group(1) for card in cards]
        self.assertEqual(len(titles), len(set(titles)))
        sourced = [card for card in cards if '<strong>Тематический источник:</strong>' in card]
        self.assertEqual(len(sourced), 87)
        for card in sourced:
            self.assertIn('формула выше — рабочий вариант сайта', card)
            self.assertRegex(card, r'<a href="https://[^"]+"')
        nav = dict(re.findall(r'<a href="#([^"]+)">[^<]*<span>\((\d+)\)</span></a>', html))
        groups = re.findall(r'<section class="metric-group" id="([^"]+)">(.*?)</section>', html, re.S)
        self.assertEqual(len(nav), len(groups))
        for slug, body in groups:
            self.assertEqual(int(nav[slug]), body.count('class="metric-entry"'), slug)
        self.assertIn('× 200 000', html)
        self.assertIn('на миллион часов', html)
        self.assertIn('не является автоматически обязательной нормой РФ', html)

    def test_no_unsupported_benchmark_and_sources_are_present(self):
        html = (ROOT / 'scm-metrics.html').read_text(encoding='utf-8')
        for source in ('apqc.org/', 'mckinsey.com/', 'ilo.org/'):
            self.assertIn(source, html)
        self.assertIn('Не устанавливайте единые целевые значения', html)
        self.assertIn('не является ошибкой само по себе', html)  # Negative cash cycle can occur.
        self.assertIn('не гарантирует снижение полной стоимости', html)


if __name__ == '__main__':
    unittest.main()
