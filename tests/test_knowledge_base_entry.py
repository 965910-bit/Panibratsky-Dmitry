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
        self.assertIn('<a href="wiki.html">База знаний</a>', home)
        self.assertIn('class="button button-secondary hero-knowledge-link" href="wiki.html"', home)
        self.assertIn('href="wiki.html" class="resource-card resource-card-knowledge"', home)
        self.assertIn('<details class="resource-directory">', home)
        self.assertLess(home.index('<details class="resource-directory">'), home.index('<section class="book-feature"'))
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

    def test_inventory_accuracy_example_and_wiki_navigation(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        self.assertIn('href="scm-practical-guides.html#inventory-accuracy"', wiki)
        self.assertEqual(html.count('id="inventory-accuracy"'), 1)
        for text in ('90 − 100 = −10', '60 − 50 = +10', '40 − 40 = 0',
                     '10 + 10 + 0', '1 / 3 × 100% ≈ 33,3%',
                     'не доказанные потери', 'не автоматически заменяет',
                     'При нуле проверенных записей доля не рассчитывается'):
            self.assertIn(text, html)
        self.assertEqual(sum((90 - 100, 60 - 50, 40 - 40)), 0)
        self.assertEqual(sum(abs(n) for n in (90 - 100, 60 - 50, 40 - 40)), 20)
        self.assertAlmostEqual(1 / 3 * 100, 33.333333, places=5)

    def test_receiving_time_example_and_navigation(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        self.assertIn('href="scm-practical-guides.html#receiving-to-availability"', wiki)
        self.assertEqual(html.count('id="receiving-to-availability"'), 1)
        for phrase in ('(3,5 + 5,5) / 2 = 4,5', '(4,5 + 5,5) / 2 = 5',
                       'незавершённые поставки', 'их длительности нельзя просто сложить',
                       'среднее не рассчитывается', 'не обходите проверки качества'):
            self.assertIn(phrase, html)
        self.assertEqual((3.5 + 5.5) / 2, 4.5)
        self.assertEqual((4.5 + 5.5) / 2, 5)

    def test_warehouse_slotting_example_and_navigation(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        self.assertIn('href="scm-practical-guides.html#warehouse-slotting"', wiki)
        self.assertEqual(html.count('id="warehouse-slotting"'), 1)
        for phrase in ('100 × 80 + 20 × 30 = 8 600', '100 × 30 + 20 × 80 = 4 600',
                       '4 000 м в день', 'не прогноз экономии времени',
                       'при нулевом времени показатель не определяется',
                       'Не уменьшайте перерывы', 'незавершённые заказы отдельно'):
            self.assertIn(phrase.casefold(), html.casefold())
        self.assertEqual(100 * 80 + 20 * 30, 8600)
        self.assertEqual(100 * 30 + 20 * 80, 4600)
        self.assertEqual(8600 - 4600, 4000)
        self.assertEqual(300 / 6, 50)

    def test_supplier_lead_time_examples_and_navigation(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        self.assertIn('href="scm-practical-guides.html#supplier-lead-time"', wiki)
        self.assertEqual(html.count('id="supplier-lead-time"'), 1)
        for phrase in ('(4 + 6 + 8) / 3 = 6', '(5 + 7 + 10) / 3 ≈ 7,33',
                       '20 × 7 + 30 = 170', '20 × 10 + 30 = 230',
                       'не расчёт страхового запаса', 'Открытые и просроченные заказы',
                       'средний срок не рассчитывается'):
            self.assertIn(phrase.casefold(), html.casefold())
        self.assertEqual((4 + 6 + 8) / 3, 6)
        self.assertAlmostEqual((5 + 7 + 10) / 3, 7.333333, places=5)
        self.assertEqual(20 * 7 + 30, 170)
        self.assertEqual(20 * 10 + 30, 230)

    def test_cross_functional_wiki_examples(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-advanced-practice.html').read_text(encoding='utf-8')
        for anchor in ('forecast-review', 'supply-allocation', 'cash-cycle-example'):
            self.assertIn(f'href="scm-advanced-practice.html#{anchor}"', wiki)
            self.assertEqual(html.count(f'id="{anchor}"'), 1)
        for phrase in ('(20 + 20) / (100 + 100) × 100% = 20%',
                       '90 / 120 = 75%', '45, 30 и 15',
                       '800 000 / (3 600 000 / 90) = 20',
                       '500 000 / (4 500 000 / 90) = 10',
                       '300 000 / (2 700 000 / 90) = 10',
                       'нулевой оборот делает соответствующий показатель дней неопределённым'):
            self.assertIn(phrase, html)
        self.assertEqual((20 + 20) / 200 * 100, 20)
        self.assertEqual(sum((45, 30, 15)), 90)
        self.assertEqual(800000 / (3600000 / 90), 20)
        self.assertEqual(500000 / (4500000 / 90), 10)
        self.assertEqual(300000 / (2700000 / 90), 10)

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
