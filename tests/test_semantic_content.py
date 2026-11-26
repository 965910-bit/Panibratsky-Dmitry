import csv
import re
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SemanticContentTests(unittest.TestCase):
    def test_unified_queries_are_unique_and_statistics_are_not_invented(self):
        with (ROOT / 'audit/СЕМАНТИКА-ЯНДЕКС-GOOGLE-РОССИЯ.csv').open(encoding='utf-8-sig', newline='') as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 196)
        normalize = lambda q: re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', q).casefold()).strip()
        queries = [normalize(row['Фраза для проверки']) for row in rows]
        self.assertEqual(len(queries), len(set(queries)))
        for row in rows:
            self.assertEqual(row['Яндекс частотность'], '')
            self.assertEqual(row['Google среднемесячные'], '')
            for destination in row['Страница для оценки'].split('; '):
                filename, _, fragment = destination.partition('#')
                html = (ROOT / filename).read_text(encoding='utf-8')
                if fragment:
                    self.assertRegex(html, r'(?:id|name)=["\']' + re.escape(fragment) + r'["\']')

    def test_search_answer_pages_keep_formulas_limits_and_internal_links(self):
        expectations = {
            'inventory-turnover-calculator.html': ('среднюю стоимость запаса', 'нулевой себестоимости', 'регулярным наблюдениям'),
            'safety-stock-calculator.html': ('фиксированном сроке', 'не гарантирует', 'вероятность дефицита'),
            'reorder-point-calculator.html': ('520', '550', 'не «сколько заказать»'),
            'scm-problems.html': ('Как повысить точность складских остатков?', 'не то же самое', 'не подтверждённая сумма предотвращённых потерь'),
            'career.html': ('Как оценить руководителя логистики и цепей поставок', 'головной офис находится в другом городе'),
        }
        for filename, texts in expectations.items():
            html = (ROOT / filename).read_text(encoding='utf-8')
            for text in texts:
                self.assertIn(text, html, filename)
            self.assertEqual(html.count('src="js/analytics-consent.js"'), 1, filename)
            self.assertEqual(html.count('src="js/visitor-events.js"'), 1, filename)


if __name__ == '__main__':
    unittest.main()
