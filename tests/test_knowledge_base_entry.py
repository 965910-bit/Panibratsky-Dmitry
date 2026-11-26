import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class KnowledgeBaseEntryTests(unittest.TestCase):
    def test_entry_connects_public_materials_to_real_anchors(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        home = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<h1>База знаний по логистике и цепям поставок</h1>', wiki)
        self.assertIn('не опубликованные статьи', wiki)
        self.assertIn('href="wiki.html">База знаний по логистике и SCM', home)
        for href in re.findall(r'href="([^"#?]+\.html)(?:#[^"]*)?"', wiki):
            if not href.startswith(('http:', 'https:')):
                self.assertTrue((ROOT / href).is_file(), href)
        for page, anchor in [('scm-practical-guides.html', 'inventory-balance'),
                             ('scm-practical-guides.html', 'working-hours'),
                             ('scm-practical-guides.html', 'supply-chain-roles')]:
            self.assertIn(f'href="{page}#{anchor}"', wiki)
            self.assertIn(f'id="{anchor}"', (ROOT / page).read_text(encoding='utf-8'))

    def test_examples_distinguish_stock_types_and_hours(self):
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        for text in ('100 + 40 − 30 − 5 = 105', '80 + 50 = 130', 'поступление в пути',
                     '7,5 часа', '150 плановых часов', '30 человеко-часов', '8 человеко-часов',
                     '50 строк на человеко-час', 'специальные перерывы включаются',
                     'не является юридической консультацией', 'не должностные инструкции'):
            self.assertIn(text.casefold(), html.casefold(), text)
        self.assertEqual(100 + 40 - 30 - 5, 105)
        self.assertEqual((100 - 20) + 50, 130)
        self.assertEqual((8 - .5) * 20, 150)
        self.assertEqual(2 * 3 + 2, 8)
        self.assertEqual(400 / 8, 50)


    def test_kpi_application_examples_and_navigation(self):
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        self.assertIn('id="kpi-application"', html)
        for text in ('80 / 100', '76,5%', '25%', '4,55%', '22,5 дня', '300 ₽', '200 счетов'):
            self.assertIn(text, html)
        self.assertIn('href="scm-practical-guides.html#kpi-application"', (ROOT / 'scm-metrics.html').read_text(encoding='utf-8'))
        self.assertEqual(80 / 100 * 100, 80)
        self.assertAlmostEqual(.90 * .85 * 100, 76.5)
        self.assertEqual((5 / 10 + 0 / 100) / 2 * 100, 25)
        self.assertAlmostEqual(5 / 110 * 100, 4.5454545, places=5)
        self.assertEqual(90 / (400000 / 100000), 22.5)
        self.assertEqual(120000 / 400, 300)
        self.assertEqual(400 / 2, 200)

    def test_service_stockout_guide_is_linked_and_distinguishes_bases(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        self.assertIn('href="scm-practical-guides.html#service-and-stockouts"', wiki)
        self.assertEqual(html.count('id="service-and-stockouts"'), 1)
        for text in ('(80 + 10) / (80 + 20)', '1 / 2 × 100% = 50%',
                     '3 / 4 × 100% = 75%', 'данных о границах',
                     'показатель не рассчитывается', 'может отличаться от выбранного временного окна'):
            self.assertIn(text, html)
        self.assertEqual((80 + 10) / (80 + 20) * 100, 90)
        self.assertEqual(1 / 2 * 100, 50)
        self.assertEqual(3 / 4 * 100, 75)

    def test_abc_capacity_and_diagnostic_examples(self):
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        for term in ('id="abc-xyz"', 'id="warehouse-review"', 'id="capacity"',
                     'при нулевом среднем коэффициент не определён',
                     'универсальных границ X, Y и Z нет',
                     '300 строк', '6 человеко-часов', '10 человеко-часов',
                     '12 человеко-часов', 'не норматив для другого склада'):
            self.assertIn(term.casefold(), html.casefold(), term)
        self.assertEqual(300 * 1.2 / 60, 6)
        self.assertEqual(6 + 4, 10)
        self.assertEqual(2 * 6, 12)
        self.assertEqual(12 - 10, 2)
        self.assertEqual(sum([600, 300, 100]), 1000)
        self.assertEqual(600 / 1000 * 100, 60)


if __name__ == '__main__':
    unittest.main()
