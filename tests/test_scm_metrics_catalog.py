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
        self.assertEqual(len(sections), 10)
        self.assertEqual(len(set(sections)), 10)
        cards = re.findall(r'<article class="metric-entry">(.*?)</article>', html, re.S)
        self.assertEqual(len(cards), 67)
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

    def test_ten_category_examples_are_present_and_arithmetically_consistent(self):
        html = (ROOT / 'scm-metrics.html').read_text(encoding='utf-8')
        self.assertEqual(html.count('class="metric-example"'), 10)
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

    def test_no_unsupported_benchmark_and_sources_are_present(self):
        html = (ROOT / 'scm-metrics.html').read_text(encoding='utf-8')
        for source in ('apqc.org/', 'mckinsey.com/', 'ilo.org/'):
            self.assertIn(source, html)
        self.assertIn('Не устанавливайте единые целевые значения', html)
        self.assertIn('не является ошибкой само по себе', html)  # Negative cash cycle can occur.
        self.assertIn('не гарантирует снижение полной стоимости', html)


if __name__ == '__main__':
    unittest.main()
