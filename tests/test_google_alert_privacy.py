import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_collector():
    bs4 = types.ModuleType('bs4')
    bs4.BeautifulSoup = lambda *_args: types.SimpleNamespace(find_all=lambda *a, **k: [])
    spec = importlib.util.spec_from_file_location('test_google_collector', ROOT / 'collectors/google_alerts.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'bs4': bs4}):
        spec.loader.exec_module(module)
    return module


def load_script(collector):
    spec = importlib.util.spec_from_file_location('test_collect_alerts', ROOT / 'scripts/collect_google_alerts.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'collectors.google_alerts': types.SimpleNamespace(GoogleAlertsCollector=collector)}):
        spec.loader.exec_module(module)
    return module


class GoogleAlertPrivacyTests(unittest.TestCase):
    def test_collector_uses_readonly_mailbox_and_does_not_log_message_content(self):
        module = load_collector()
        message = (b'Subject: Google Alert \xe2\x80\x93 private-secret-keyword\r\n'
                   b'Content-Type: text/plain; charset=utf-8\r\n\r\n'
                   b'https://example.com/private-secret-url')
        class Mail:
            selected = None
            fetch_mode = None
            def login(self, *_): return 'OK', []
            def select(self, folder, readonly=False): self.selected = (folder, readonly); return 'OK', []
            def search(self, *_): return 'OK', [b'1']
            def fetch(self, number, mode): self.fetch_mode = mode; return 'OK', [(b'body', message)]
            def logout(self): return 'BYE', []
        mail = Mail()
        output = io.StringIO()
        with patch.object(module.imaplib, 'IMAP4_SSL', return_value=mail), contextlib.redirect_stdout(output):
            result = module.GoogleAlertsCollector('user', 'password').fetch()
        self.assertEqual(mail.selected, ('INBOX', True))
        self.assertEqual(mail.fetch_mode, '(BODY.PEEK[])')
        self.assertEqual(len(result['alerts']), 1)
        self.assertIn('private-secret', result['alerts'][0]['link'])
        self.assertNotIn('private-secret', output.getvalue())

    def test_connection_failure_is_not_an_empty_success_and_hides_details(self):
        module = load_collector()
        output = io.StringIO()
        with patch.object(module.imaplib, 'IMAP4_SSL', side_effect=ValueError('private-secret')), contextlib.redirect_stdout(output):
            with self.assertRaises(RuntimeError): module.GoogleAlertsCollector('user', 'password').fetch()
        self.assertNotIn('private-secret', output.getvalue())

    def test_private_scratch_does_not_touch_public_file_and_uses_restrictive_permissions(self):
        class Collector:
            def __init__(self, *_): pass
            def fetch(self): return {'alerts':[{'subject':'private-secret'}]}
        module = load_script(Collector)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); module.ROOT = root; (root/'data').mkdir()
            historical = root/'data/google_alerts.json'; historical.write_text('existing')
            with patch.dict(os.environ, {'GMAIL_USER':'fixture','GMAIL_PASSWORD':'fixture'}): module.main()
            output = root/'.local-news/google_alerts.json'
            self.assertEqual(json.loads(output.read_text())['alerts'][0]['subject'], 'private-secret')
            self.assertEqual(historical.read_text(), 'existing')
            if os.name == 'posix': self.assertEqual(output.stat().st_mode & 0o077, 0)
            self.assertEqual(list(output.parent.glob('*.tmp')), [])

    def test_collection_failure_preserves_previous_scratch_and_does_not_log_exception(self):
        class Collector:
            def __init__(self, *_): pass
            def fetch(self): raise RuntimeError('private-secret')
        module = load_script(Collector)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); module.ROOT = root; (root/'.local-news').mkdir()
            target = root/'.local-news/google_alerts.json'; target.write_text('previous')
            output = io.StringIO()
            with patch.dict(os.environ, {'GMAIL_USER':'fixture','GMAIL_PASSWORD':'fixture'}), contextlib.redirect_stdout(output):
                with self.assertRaises(SystemExit): module.main()
            self.assertEqual(target.read_text(), 'previous')
            self.assertNotIn('private-secret', output.getvalue())

    def test_git_pages_and_workflow_exclude_scratch_from_publication(self):
        self.assertIn('/.local-news/', (ROOT/'.gitignore').read_text())
        self.assertIn('  - .local-news', (ROOT/'_config.yml').read_text())
        self.assertIn('  - data/google_alerts.json', (ROOT/'_config.yml').read_text())
        workflow = (ROOT/'.github/workflows/update_news.yml').read_text()
        self.assertIn('git add data/news.json trends.html sitemap.xml rss.xml', workflow)
        self.assertNotIn('git add data/', workflow.replace('git add data/news.json', ''))
        result = subprocess.run(['git', 'check-ignore', '-q', '.local-news/google_alerts.json'], cwd=ROOT)
        self.assertEqual(result.returncode, 0)

if __name__ == '__main__': unittest.main()
