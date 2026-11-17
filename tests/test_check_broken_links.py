import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_checker():
    spec = importlib.util.spec_from_file_location('check_broken_links', ROOT / 'scripts/check_broken_links.py')
    checker = importlib.util.module_from_spec(spec)
    requests = types.ModuleType('requests')
    requests.RequestException = type('RequestException', (Exception,), {})
    with patch.dict(sys.modules, {'requests': requests}):
        spec.loader.exec_module(checker)
    return checker


class LinkCheckerTests(unittest.TestCase):
    def test_empty_allowlist_skips_all_and_preserves_feed(self):
        checker = load_checker()
        self.assertEqual(checker.APPROVED_HOSTS, frozenset())
        with tempfile.TemporaryDirectory() as directory:
            checker.NEWS_FILE = Path(directory) / 'news.json'
            data = [{'link': 'https://news.ati.su/a', 'dead': True},
                    {'link': 'https://logistics360.ru/b'},
                    {'link': 'https://example.org/c'}, None]
            raw = json.dumps(data, ensure_ascii=False)
            checker.NEWS_FILE.write_text(raw, encoding='utf-8')
            with patch.object(checker.requests, 'get', create=True) as get:
                checker.main()
                self.assertEqual(checker.check_url('https://news.ati.su/a'), 'unknown')
                get.assert_not_called()
            self.assertEqual(checker.NEWS_FILE.read_text(encoding='utf-8'), raw)

    def test_exact_https_host_no_credentials_and_redirects_not_followed(self):
        checker = load_checker()
        checker.APPROVED_HOSTS = frozenset({'example.org'})
        for url in ['http://example.org/a', 'https://sub.example.org/a', 'https://example.org.evil/a',
                    'https://user@example.org/a', 'https://example.org:444/a',
                    'https://news.ati.su/a', 'https://logistics360.ru/a']:
            self.assertFalse(checker.approved_url(url), url)
        self.assertTrue(checker.approved_url('https://EXAMPLE.ORG./a'))
        response = types.SimpleNamespace(status_code=302, close=lambda: None)
        with patch.object(checker.requests, 'get', create=True, return_value=response) as get:
            self.assertEqual(checker.check_url('https://example.org/a'), 'unknown')
            self.assertFalse(get.call_args.kwargs['allow_redirects'])
            self.assertEqual(get.call_count, 1)

    def test_only_definite_404_and_410_mark_missing(self):
        checker = load_checker()
        checker.APPROVED_HOSTS = frozenset({'example.org'})
        for code, status in [(200, 'alive'), (404, 'missing'), (410, 'missing'),
                             (301, 'unknown'), (403, 'unknown'), (429, 'unknown'), (500, 'unknown')]:
            response = types.SimpleNamespace(status_code=code, close=lambda: None)
            with patch.object(checker.requests, 'get', create=True, return_value=response):
                self.assertEqual(checker.check_url('https://example.org/a'), status)

    def test_unapproved_records_never_have_dead_flags_changed(self):
        checker = load_checker()
        checker.APPROVED_HOSTS = frozenset({'example.org'})
        with tempfile.TemporaryDirectory() as directory:
            checker.NEWS_FILE = Path(directory) / 'news.json'
            data = [{'link': 'https://example.org/a'},
                    {'link': 'https://news.ati.su/a', 'dead': True},
                    {'link': 'https://logistics360.ru/b'}]
            checker.NEWS_FILE.write_text(json.dumps(data), encoding='utf-8')
            response = types.SimpleNamespace(status_code=404, close=lambda: None)
            with patch.object(checker.requests, 'get', create=True, return_value=response) as get:
                checker.main()
                self.assertEqual(get.call_count, 1)
            result = json.loads(checker.NEWS_FILE.read_text(encoding='utf-8'))
            self.assertTrue(result[0]['dead'])
            self.assertEqual(result[1:], data[1:])


if __name__ == '__main__':
    unittest.main()
