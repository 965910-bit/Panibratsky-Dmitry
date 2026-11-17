from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CardParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.current = None
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.current is None and tag == 'div' and 'kpi-card' in attrs.get('class', '').split():
            self.current = {'text': [], 'links': []}
            self.depth = 1
        elif self.current is not None:
            if tag == 'div': self.depth += 1
            if tag == 'a': self.current['links'].append(attrs.get('href'))

    def handle_endtag(self, tag):
        if self.current is not None and tag == 'div':
            self.depth -= 1
            if self.depth == 0:
                self.cards.append(self.current)
                self.current = None

    def handle_data(self, data):
        if self.current is not None: self.current['text'].append(data)


class LibraryFactcheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = (ROOT/'library.html').read_text(encoding='utf-8')
        parser = CardParser(); parser.feed(cls.library); cls.cards = parser.cards

    def card(self, name):
        matches = [card for card in self.cards if name in ' '.join(card['text'])]
        self.assertEqual(len(matches), 1, name)
        return matches[0], ' '.join(matches[0]['text'])

    def test_case_is_attributed_and_not_generalized(self):
        card, text = self.card('Экономический эффект RPA')
        self.assertIn('377 млн руб.', text)
        self.assertIn('1 июня 2023 года', text)
        self.assertIn('не независимый аудит', text)
        self.assertNotIn('превысил 377', text)
        self.assertNotIn('30%', text)
        self.assertIn('https://rpanext.ru/news/tstr-nekst-provel-iv-ezhegodnuyu-konferentsiyu-rpa-connect-formula-effekta/', card['links'])

    def test_fte_is_time_equivalent_not_automatically_money_or_headcount(self):
        _, text = self.card('FTE-эквивалент (Full-Time Equivalent)')
        self.assertIn('за тот же период', text)
        self.assertIn('не обязательно сокращение персонала или денежных расходов', text)

    def test_accuracy_is_clear_about_units_zero_and_negative_values(self):
        card, text = self.card('Точность прогнозов ML-моделей')
        self.assertIn('100% – MAPE', text)
        self.assertIn('если MAPE выражена в процентах', text)
        self.assertIn('нулевом факте', text)
        self.assertIn('отрицательной', text)
        self.assertNotIn('ПЭК', text)
        self.assertIn('https://otexts.com/fpp3/toolbox.html#sec-accuracy', card['links'])

    def test_sla_targets_are_contextual_and_penalty_ratio_is_not_compliance(self):
        for label in ('On-Time Delivery (OTD) по SLA', 'In-Full Delivery по SLA',
                      'Order Accuracy по SLA', 'Damage-Free Rate по SLA'):
            _, text = self.card(label)
            self.assertIn('договор', text)
            self.assertNotIn('Цель: ≥', text)
        _, text = self.card('Использование лимита штрафов по SLA')
        self.assertIn('не измеряет степень соблюдения SLA', text)
        self.assertIn('если он положителен', text)

    def test_removed_unverified_effects_are_not_repeated_on_related_pages(self):
        pages = ['library.html', 'scm-platform/library.html', 'scm-platform/inventory-methodology.html']
        for name in pages:
            text = (ROOT/name).read_text(encoding='utf-8')
            with self.subTest(page=name):
                self.assertNotIn('сокращать дефекты на 50-70%', text)
                self.assertNotIn('уменьшать время выполнения заказов на 30-40%', text)
                self.assertIn('проверен', text)
        for text in ('Лидеры достигают 95–98%', 'в России пока ~23%',
                     'В ПЭК внедрение машинного обучения', 'логистические компании достигали до 50%'):
            self.assertNotIn(text, self.library)
        self.assertNotIn('MAPE &lt;10%', (ROOT/'scm-platform/inventory-methodology.html').read_text(encoding='utf-8'))

if __name__ == '__main__': unittest.main()
