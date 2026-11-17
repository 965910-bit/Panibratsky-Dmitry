import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_sitemap as sitemap


class SitemapValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.pages = ['', 'about.html']
        self.page('index.html', '<link rel="canonical" href="https://scm-news.ru/">')
        self.page('about.html', '<link href="https://scm-news.ru/about.html" rel="alternate canonical">')

    def page(self, name, head, body=''):
        (self.root / name).write_text(f'<html><head>{head}</head><body>{body}</body></html>', encoding='utf-8')

    def test_generate_and_check_are_deterministic_and_check_does_not_write(self):
        sitemap.generate_sitemap(self.root, self.pages)
        target = self.root / 'sitemap.xml'
        before = target.read_bytes()
        with patch.object(sitemap.os, 'replace', side_effect=AssertionError('check wrote a file')):
            sitemap.generate_sitemap(self.root, self.pages, check=True)
        self.assertEqual(target.read_bytes(), before)
        target.write_text('<urlset/>', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'differs'):
            sitemap.generate_sitemap(self.root, self.pages, check=True)
        self.assertEqual(target.read_text(), '<urlset/>')

    def test_invalid_or_duplicate_pages_do_not_replace_previous_sitemap(self):
        target = self.root / 'sitemap.xml'
        target.write_bytes(b'previous')
        for pages in (['', ''], ['', 'index.html'], ['', '../about.html'], ['', 'about.html?x=1'], ['', 'missing.html']):
            with self.subTest(pages=pages), self.assertRaises(ValueError):
                sitemap.generate_sitemap(self.root, pages)
            self.assertEqual(target.read_bytes(), b'previous')

    def test_missing_wrong_duplicate_and_body_canonical_rejected(self):
        cases = [('', ''), ('<link rel="canonical" href="https://example.com/">', ''),
                 ('<link rel="canonical" href="https://scm-news.ru/about.html">' * 2, ''),
                 ('', '<link rel="canonical" href="https://scm-news.ru/about.html">')]
        for head, body in cases:
            self.page('about.html', head, body)
            with self.subTest(head=head, body=body), self.assertRaisesRegex(ValueError, 'canonical'):
                sitemap.build_sitemap(self.root, self.pages)

    def test_canonical_with_variant_attributes_is_rejected(self):
        for attribute in ('hreflang="en"', 'lang="ru"', 'media="all"', 'type="text/html"'):
            self.page('about.html', f'<link rel="canonical" href="https://scm-news.ru/about.html" {attribute}>')
            with self.subTest(attribute=attribute), self.assertRaisesRegex(ValueError, 'canonical'):
                sitemap.build_sitemap(self.root, self.pages)

    def test_meta_noindex_for_relevant_agents_and_none_are_rejected(self):
        canonical = '<link rel="canonical" href="https://scm-news.ru/about.html">'
        for directive in ('<meta name="robots" content="follow, NOINDEX">',
                          '<meta name="googlebot-news" content="none">',
                          '<meta name="BINGBOT" content="noindex">'):
            self.page('about.html', canonical + directive)
            with self.subTest(directive=directive), self.assertRaisesRegex(ValueError, 'noindex'):
                sitemap.build_sitemap(self.root, self.pages)
        self.page('about.html', canonical, '<meta name="robots" content="noindex">')
        with self.assertRaisesRegex(ValueError, 'noindex'):
            sitemap.build_sitemap(self.root, self.pages)
        self.page('about.html', canonical + '<meta name="robots" content="index,follow">')
        sitemap.build_sitemap(self.root, self.pages)

    def test_replace_failure_preserves_existing_file_and_cleans_temp(self):
        target = self.root / 'sitemap.xml'
        target.write_bytes(b'previous')
        original_files = set(self.root.iterdir())
        with patch.object(sitemap.os, 'replace', side_effect=OSError('failure')):
            with self.assertRaises(OSError):
                sitemap.generate_sitemap(self.root, self.pages)
        self.assertEqual(target.read_bytes(), b'previous')
        self.assertEqual(set(self.root.iterdir()), original_files)


if __name__ == '__main__':
    unittest.main()
