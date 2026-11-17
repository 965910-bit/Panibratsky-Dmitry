from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = set(), []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs: self.ids.add(attrs['id'])
        if tag == 'a': self.links.append(attrs.get('href', ''))

class StandardsFactcheckTests(unittest.TestCase):
    def test_standards_remove_unsupported_values_and_link_sources(self):
        page = (ROOT / 'scm-platform/standards.html').read_text(encoding='utf8')
        parser = Elements(); parser.feed(page)
        for anchor in ('quality', 'transport', 'sla', 'esg', 'safety'):
            self.assertIn(anchor, parser.ids)
        for source in ('https://www.fedex.com/en-gb/how-to/calculate-costs/dimensional-weight.html',
                       'https://otexts.com/fpp3/toolbox.html#sec-accuracy',
                       'https://www.mckinsey.com/capabilities/operations/our-insights/defining-on-time-in-full-in-the-consumer-sector',
                       'https://publication.pravo.gov.ru/document/0001202112290004',
                       'https://publication.pravo.gov.ru/document/0001202606300022'):
            self.assertIn(source, parser.links)
        for claim in ('Все значения являются среднерыночными', '1,5 – 1,7', '≈ 59 600',
                      'Управление без удостоверения категории С запрещено', '35 000 – 45 000',
                      'индексация 2025–2026', 'Для авто: /6000', 'Штраф (типовой)'):
            self.assertNotIn(claim, page)
        self.assertIn('не является отраслевым бенчмарком', page)
        self.assertIn('действующую редакцию и специальные нормы', page)

    def test_methodology_no_unsupported_inventory_or_sla_targets(self):
        page = (ROOT / 'scm-platform/inventory-methodology.html').read_text(encoding='utf8')
        for claim in ('GMROI &lt; 2', '>180 дней', 'норматива (60 дней)', 'КСХ = (Р + АД',
                      'своевременность доставки (≥98%)', 'полнота отгрузки (≥99%)',
                      'время реакции на претензию (&lt;4 часа)'):
            self.assertNotIn(claim, page)
        self.assertIn('универсальные пороги дней и GMROI не подтверждены', page)
        self.assertIn('не доказывает неликвидность', page)
        self.assertIn('определяются договором', page)

if __name__ == '__main__': unittest.main()
