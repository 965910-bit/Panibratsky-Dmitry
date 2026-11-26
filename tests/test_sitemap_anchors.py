import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_sitemap_anchors import check


class AnchorTests(unittest.TestCase):
    def test_local_anchors_and_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('<div id="book"></div><a href="/index.html#book">OK</a><a href="/other.html#bad">bad</a><a href="https://outside.test/#missing">external</a>', encoding='utf-8')
            (root / 'other.html').write_text('<a name="here"></a><a href="/#book">OK</a>', encoding='utf-8')
            self.assertEqual(check(root, ['', 'other.html']), [('index.html', '/other.html#bad')])
            (root / 'other.html').write_text('<div id="bad"></div>', encoding='utf-8')
            self.assertEqual(check(root, ['', 'other.html']), [])


if __name__ == '__main__':
    unittest.main()
