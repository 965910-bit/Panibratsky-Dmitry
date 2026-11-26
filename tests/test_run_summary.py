import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_summary
try:
    import fetch_news
except ImportError:
    fetch_news = None


class SummaryTests(unittest.TestCase):
    def test_appends_and_prints_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'summary'
            path.write_text('Earlier\n')
            with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(path)}), contextlib.redirect_stdout(io.StringIO()) as out:
                run_summary.report('Test status')
            self.assertEqual(path.read_text(), 'Earlier\nTest status\n\n')
            self.assertIn('Test status', out.getvalue())

    def test_missing_summary_is_nonfatal_and_printed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'missing' / 'summary'
            with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(path)}), contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                run_summary.report('Test status')
            self.assertIn('Test status', out.getvalue())
            self.assertIn('warning', err.getvalue())

    @unittest.skipIf(fetch_news is None, "news dependencies unavailable")
    def test_paused_news_explicitly_reports_no_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'summary'
            with patch.object(fetch_news, 'SOURCES', []), patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(path)}), contextlib.redirect_stdout(io.StringIO()):
                fetch_news.main()
            self.assertIn('новые новости не собирались', path.read_text())


if __name__ == '__main__':
    unittest.main()
