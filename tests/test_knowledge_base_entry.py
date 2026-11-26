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

    def test_transport_risk_and_safety_examples(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        pages = {'scm-encyclopedia.html': 'freight-utilisation', 'scm-practical-guides.html': 'supply-recovery',
                 'scm-internal-academy.html': 'shift-safety-dialogue'}
        for page, anchor in pages.items():
            self.assertIn(f'href="{page}#{anchor}"', wiki)
            self.assertEqual((ROOT / page).read_text(encoding='utf-8').count(f'id="{anchor}"'), 1)
        transport = (ROOT / 'scm-encyclopedia.html').read_text(encoding='utf-8')
        for phrase in ('10 × 100 + 0 × 80 = 1 000', '80 / (100 + 80) × 100% ≈ 44,4%',
                       '1 000 / 180 ≈ 5,56', 'не процент загрузки грузоподъёмности'):
            self.assertIn(phrase, transport)
        risk = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        self.assertIn('1 200 / 100 = 12 дней', risk)
        self.assertIn('15 − 12 = 3 дня', risk)
        safety = (ROOT / 'scm-internal-academy.html').read_text(encoding='utf-8')
        self.assertIn('Ноль зарегистрированных случаев не доказывает отсутствия опасности', safety)
        self.assertEqual(10 * 100 + 0 * 80, 1000)
        self.assertAlmostEqual(80 / 180 * 100, 44.4444444, places=4)
        self.assertEqual(1200 / 100, 12)
        self.assertEqual(15 - 12, 3)

    def test_production_oee_and_flow(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-advanced-practice.html').read_text(encoding='utf-8')
        for anchor in ('production-oee', 'production-bottleneck'):
            self.assertIn(f'href="scm-advanced-practice.html#{anchor}"', wiki)
            self.assertEqual(html.count(f'id="{anchor}"'), 1)
        for phrase in ('420 / 480 = 87,5%', '760 / 800 = 95%', '79,17%',
                       'при нулевом плановом времени OEE не определена',
                       '90 изделий за смену', 'ограничением станет третья операция'):
            self.assertIn(phrase.casefold(), html.casefold())
        self.assertAlmostEqual((420 / 480) * (400 / 420) * (760 / 800) * 100, 79.1666667)
        self.assertEqual(min(120, 90, 110), 90)
        self.assertEqual(min(120, 105, 110), 105)
        self.assertEqual(min(120, 115, 110), 110)

    def test_procurement_category_and_supplier_correction(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        for anchor in ('category-strategy', 'supplier-corrective-action'):
            self.assertIn(f'href="scm-practical-guides.html#{anchor}"', wiki)
            self.assertEqual(html.count(f'id="{anchor}"'), 1)
        for phrase in ('60%, 30% и 10%', 'при нулевой сумме',
                       '300 уже отгружены, 700 физически находятся на складе',
                       '2 / 100 × 100% = 2%', 'не доказывают долю дефектов во всей партии',
                       'отсутствие дефектов в небольшой проверке не доказывает полного отсутствия риска'):
            self.assertIn(phrase, html)
        self.assertEqual([n / 10 * 100 for n in (6, 3, 1)], [60, 30, 10])
        self.assertEqual(300 + 700, 1000)
        self.assertEqual(2 / 100 * 100, 2)

    def test_order_promising_cash_and_master_data(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        for anchor in ('available-to-promise', 'order-to-cash', 'product-master-data'):
            self.assertIn(f'href="scm-practical-guides.html#{anchor}"', wiki)
            self.assertEqual(html.count(f'id="{anchor}"'), 1)
        for phrase in ('100 − 30 = 70', '70 + 40 = 110', 'ещё 110',
                       'от счёта до оплаты = 96 часов', 'от заказа до оплаты = 168 часов',
                       'не 168 часов трудозатрат', '10 × 12 = 120', 'расхождение составляет 20'):
            self.assertIn(phrase, html)
        self.assertEqual(100 - 30, 70)
        self.assertEqual(70 + 40 - 90, 20)
        self.assertEqual(48 + 24 + 96, 168)
        self.assertEqual(10 * 12 - 10 * 10, 20)

    def test_cross_dock_and_carrier_performance(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        for anchor in ('cross-docking', 'carrier-performance'):
            self.assertIn(f'href="scm-practical-guides.html#{anchor}"', wiki)
            self.assertEqual(html.count(f'id="{anchor}"'), 1)
        for phrase in ('180 минут', 'готова в 12:30', 'точное время следующей отправки',
                       '18 / 20 × 100% = 90%', '100 000 / 20 = 5 000',
                       'не относите причину к перевозчику без доказательств'):
            self.assertIn(phrase.casefold(), html.casefold())
        self.assertEqual(90 + 90, 180)
        self.assertEqual(18 / 20 * 100, 90)
        self.assertEqual(100000 / 20, 5000)

    def test_expiry_rotation_and_little_law(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        for anchor in ('fifo-fefo', 'little-law'):
            self.assertIn(f'href="scm-practical-guides.html#{anchor}"', wiki)
            self.assertEqual(html.count(f'id="{anchor}"'), 1)
        for phrase in ('40 из B и 30 из A', 'A — 18 дней, B — 8 дней',
                       'B не подходит', '30 / 5 =', '6 часов на заказ',
                       'не трудозатраты сотрудника', 'при нулевой интенсивности деление не определено'):
            self.assertIn(phrase.casefold(), html.casefold())
        self.assertEqual(40 + 30, 70)
        self.assertEqual(30 - 12, 18)
        self.assertEqual(20 - 12, 8)
        self.assertEqual(30 / 5, 6)

    def test_supplier_selection_and_three_way_match(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        for anchor in ('supplier-selection', 'three-way-match'):
            self.assertIn(f'href="scm-practical-guides.html#{anchor}"', wiki)
            self.assertEqual(html.count(f'id="{anchor}"'), 1)
        for phrase in ('4 × 0,4 + 3 × 0,3 + 5 × 0,3', '3 × 0,4 + 5 × 0,3 + 4 × 0,3',
                       '20 + 60 =', 'расхождение =', 'не путая физическое получение',
                       'не является инструкцией для конкретной процедуры'):
            self.assertIn(phrase.casefold(), html.casefold())
        self.assertAlmostEqual(4 * .4 + 3 * .3 + 5 * .3, 4.0)
        self.assertAlmostEqual(3 * .4 + 5 * .3 + 4 * .3, 3.9)
        self.assertEqual(20 + 60 - 70, 10)

    def test_intermittent_demand_and_inventory_transfer(self):
        wiki = (ROOT / 'wiki.html').read_text(encoding='utf-8')
        html = (ROOT / 'scm-practical-guides.html').read_text(encoding='utf-8')
        for anchor in ('intermittent-demand', 'inventory-transfer'):
            self.assertIn(f'href="scm-practical-guides.html#{anchor}"', wiki)
            self.assertEqual(html.count(f'id="{anchor}"'), 1)
        for phrase in ('6 / 6 =', '6 / 2 =', 'не является расчётом Кростона',
                       '100 − 40 − 40 =', '45 − 15 =', '80 + 15 + 20 в пути',
                       'не равен доступному остатку получателя'):
            self.assertIn(phrase.casefold(), html.casefold())
        self.assertEqual(6 / 6, 1)
        self.assertEqual(6 / 2, 3)
        self.assertEqual(100 - 40 - 40, 20)
        self.assertEqual(45 - (15 + 20), 10)
        self.assertEqual(80 + 15 + 20, 80 + 35)

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
