import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import seo_guard


def page(canonical, extra='', body=''):
    return f'<html><head><link rel="canonical" href="{seo_guard.BASE}{canonical}">{extra}</head><body>{body}</body></html>'


def alternates(ru='', en='about.html'):
    return (f'<link rel="alternate" hreflang="ru" href="{seo_guard.BASE}{ru}">'
            f'<link rel="alternate" hreflang="en" href="{seo_guard.BASE}{en}">')


class SEOValidationTests(unittest.TestCase):
    def test_current_site(self):
        result = seo_guard.validate()
        self.assertEqual(result['pages'], len(seo_guard.PAGES))
        self.assertGreater(result['json_ld_blocks'], 0)

    def test_valid_and_invalid_jsonld_and_noindex(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'index.html'
            target.write_text(page('', '<script type="application/ld+json">{"@type":"Person"}</script>'))
            self.assertEqual(seo_guard.validate(root, [''])['json_ld_blocks'], 1)
            for bad in ('{oops}', '{"v": NaN}', 'null', '[]'):
                target.write_text(page('', f'<script type="application/ld+json">{bad}</script>'))
                with self.subTest(bad=bad), self.assertRaises(ValueError): seo_guard.validate(root, [''])
            target.write_text(page('', '<meta name="robots" content="noindex">'))
            with self.assertRaises(ValueError): seo_guard.validate(root, [''])
            target.write_text(page('', '<link rel="canonical" href="https://wrong.example/">'))
            with self.assertRaises(ValueError): seo_guard.validate(root, [''])

    def test_hreflang_self_reference_reciprocity_and_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home, other = root / 'index.html', root / 'about.html'
            home.write_text(page('', alternates()), encoding='utf-8')
            other.write_text(page('about.html', alternates()), encoding='utf-8')
            self.assertEqual(seo_guard.validate(root, ['', 'about.html'])['pages_with_hreflang'], 2)
            for bad in ('', alternates(en='missing.html'), alternates() + alternates(),
                        '<link rel="alternate" hreflang="ru" href="https://scm-news.ru/">'):
                other.write_text(page('about.html', bad), encoding='utf-8')
                with self.subTest(bad=bad), self.assertRaises(ValueError): seo_guard.validate(root, ['', 'about.html'])
            other.write_text(page('', alternates()), encoding='utf-8')
            with self.assertRaises(ValueError): seo_guard.validate(root, ['', 'about.html'])

    def test_hreflang_outside_head_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text(page('', body=alternates()), encoding='utf-8')
            with self.assertRaises(ValueError): seo_guard.validate(root, [''])


if __name__ == '__main__': unittest.main()
