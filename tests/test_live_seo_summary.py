import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import live_seo_summary

class SummaryTests(unittest.TestCase):
    def test_success_and_findings_are_explicit_and_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / 'report.json'
            report.write_text(json.dumps({'pages_expected':21,'requests_expected':23,'findings':[]}), encoding='utf-8')
            text=live_seo_summary.render(report)
            self.assertIn('Замечаний в проверенном наборе нет',text)
            self.assertIn('не проверка индексации',text)
            report.write_text(json.dumps({'pages_expected':21,'requests_expected':23,'findings':['<script>x</script>']}), encoding='utf-8')
            text=live_seo_summary.render(report)
            self.assertIn('Найдены замечания',text)
            self.assertIn('&lt;script&gt;',text)
            self.assertNotIn('<script>',text)
    def test_absent_malformed_or_oversized_report_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)/'report.json'
            for text in (None, '{bad', json.dumps({'pages_expected':True,'requests_expected':1,'findings':[]}), 'x'*131073):
                if text is not None: report.write_text(text,encoding='utf-8')
                self.assertIn('результат проверки не подтверждён',live_seo_summary.render(report))
    def test_scheduled_workflow_preserves_failure_and_adds_summary(self):
        workflow=(ROOT/'.github/workflows/live-seo-monitor.yml').read_text(encoding='utf-8')
        self.assertIn("cron: '41 8 * * *'",workflow)
        self.assertIn('name: Daily public SEO smoke check',workflow)
        self.assertIn('set -o pipefail',workflow)
        self.assertIn('python scripts/live_seo_check.py | tee',workflow)
        self.assertIn('if: always()',workflow)
        self.assertIn('python scripts/live_seo_summary.py',workflow)
        self.assertNotIn('continue-on-error: true',workflow)

if __name__ == '__main__': unittest.main()
