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


if __name__ == '__main__':
    unittest.main()
