import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from csp_inventory import StaticInventory, inventory, PAGES


class CSPInventoryTests(unittest.TestCase):
    def test_static_counts_and_redaction(self):
        parser = StaticInventory('https://scm-news.ru/test.html')
        parser.feed('''<html><head>
          <script type="application/ld+json">{"name":"test"}</script>
          <script>console.log('x')</script><script src="https://user:pass@cdn.example/a.js?token=private#fragment"></script>
          <script type="application/json">{}</script><style>p {color:red}</style>
          <link rel="stylesheet" href="//fonts.example/test.css?private=1">
          </head><body><p style="color:red" onclick="x()">text</p>
          <img src="https://img.example/i.png?email=x"><iframe src="https://frame.example/path"></iframe>
          <script src="/js/site.js"></script></body></html>''')
        self.assertEqual(parser.counts, {'inline_scripts':1, 'inline_handlers':1, 'inline_style_attributes':1, 'inline_style_blocks':1})
        self.assertEqual(parser.origins['script'], {'https://cdn.example'})
        self.assertEqual(parser.origins['style'], {'https://fonts.example'})
        self.assertEqual(parser.origins['image'], {'https://img.example'})
        self.assertEqual(parser.origins['frame'], {'https://frame.example'})
        self.assertNotIn('private', str(parser.origins))
        self.assertNotIn('pass', str(parser.origins))

    def test_repository_scope_and_no_urls_or_payloads(self):
        report = inventory()
        self.assertEqual(report['pages'], len(PAGES))
        self.assertEqual(len(report['files']), len(PAGES))
        self.assertIn('no CSS URLs', report['scope'])
        for origins in report['external_origins'].values():
            for origin in origins:
                self.assertNotIn('?', origin)
                self.assertNotIn('#', origin)
                self.assertNotIn('@', origin)


if __name__ == '__main__':
    unittest.main()
