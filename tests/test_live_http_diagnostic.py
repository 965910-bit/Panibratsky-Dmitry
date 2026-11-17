import sys
from pathlib import Path
import unittest
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import live_http_diagnostic as http


class LiveHTTPDiagnosticTests(unittest.TestCase):
    def test_fixed_urls_and_errors(self):
        seen = []
        def fetch(url):
            seen.append(url)
            if 'www.' in url: raise urllib.error.URLError('no connection')
            return 301, {'Location': 'https://scm-news.ru/', 'Strict-Transport-Security': 'max-age=300'}
        result = http.probe(fetch)
        self.assertEqual(seen, list(http.URLS.values()))
        self.assertEqual(result['http_apex']['location'], 'https://scm-news.ru/')
        self.assertEqual(result['https_apex']['hsts'], 'max-age=300')
        self.assertEqual(result['https_www'], {'error': 'request failed'})
        self.assertEqual(result['missing']['status'], 301)

    def test_does_not_expose_redirect_parameters(self):
        self.assertEqual(http.safe_location('https://scm-news.ru/?token=private'), 'redacted redirect with parameters or credentials')
        self.assertEqual(http.safe_location('https://external.example/path'), 'other origin')
        self.assertEqual(http.safe_location('/somewhere'), '/somewhere')


if __name__ == '__main__': unittest.main()
