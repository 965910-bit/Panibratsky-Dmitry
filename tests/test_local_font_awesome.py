import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'css/vendor/font-awesome-6.4.0'
PACKAGE = ROOT / 'node_modules/@fortawesome/fontawesome-free'


class FontAwesomeTests(unittest.TestCase):
    @unittest.skipUnless(PACKAGE.is_dir(), "npm dependencies not installed; site CI verifies vendor bytes")
    def test_vendor_matches_locked_npm_distribution(self):
        files = ['css/all.min.css', 'LICENSE.txt']
        css = (VENDOR / files[0]).read_text(encoding='utf-8')
        fonts = sorted(set(re.findall(r'url\(\.\./webfonts/([a-z0-9.-]+)\)', css)))
        self.assertEqual(len(fonts), 8)
        files.extend('webfonts/' + name for name in fonts)
        for file in files:
            with self.subTest(file=file):
                self.assertEqual((VENDOR / file).read_bytes(), (PACKAGE / file).read_bytes())

    def test_all_replaced_page_paths_resolve_locally(self):
        pages = list(ROOT.glob('*.html')) + list((ROOT / 'scm-platform').glob('*.html')) + [ROOT / 'js/analytics.js']
        count = 0
        for page in pages:
            text = page.read_text(encoding='utf-8')
            self.assertNotIn('cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0', text, str(page))
            for href in re.findall(r'href="([^"]*font-awesome-6\.4\.0/css/all\.min\.css)"', text):
                count += 1
                self.assertEqual((page.parent / href).resolve(), (VENDOR / 'css/all.min.css').resolve(), str(page))
        self.assertGreaterEqual(count, 39)
        legacy = (ROOT / 'js/analytics.js').read_text(encoding='utf-8')
        self.assertNotIn('unpkg.com/leaflet', legacy)
        for href in ('vendor/leaflet-1.9.4/leaflet.js', 'vendor/leaflet-1.9.4/leaflet.css'):
            self.assertIn(href, legacy)
            self.assertTrue((ROOT / 'js' / href).is_file())


if __name__ == '__main__':
    unittest.main()
