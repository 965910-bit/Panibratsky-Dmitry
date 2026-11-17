import copy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import open_data_review as module


def sample():
    return {'schema_version': 1, 'saved_on': '2026-11-17', 'indicators': {
        'world_bank': {'period': '2022', 'value': 2.6, 'provider_updated': '2026-11-11'},
        'eurostat': {'period': '2025', 'value': 2804335, 'status': None}}}


class ReviewTests(unittest.TestCase):
    def test_committed_snapshot_read_only_deterministic(self):
        path = ROOT / 'data/open-logistics.json'
        before = path.read_bytes()
        result = module.review(path)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(result, module.review(path))
        self.assertEqual(result['indicators']['world_bank']['comparison'], 'no_previous_snapshot')
        self.assertEqual(len(result['current']['sha256']), 64)

    def test_missing_revisions_and_new_period(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.json', Path(tmp) / 'b.json'
            old = sample(); new = copy.deepcopy(old)
            new['saved_on'] = '2026-12-01'
            new['indicators']['world_bank']['value'] = 2.7
            new['indicators']['eurostat']['period'] = '2026'
            a.write_text(json.dumps(old)); b.write_text(json.dumps(new))
            results = module.review(b, a)['indicators']
            self.assertEqual(results['world_bank']['comparison'], 'same_period_changed')
            self.assertEqual(results['eurostat']['comparison'], 'new_period')
            del new['indicators']['world_bank']
            new['indicators']['eurostat']['period'] = '2024'
            b.write_text(json.dumps(new))
            results = module.review(b, a)['indicators']
            self.assertEqual(results['world_bank']['comparison'], 'missing_current')
            self.assertEqual(results['eurostat']['comparison'], 'period_regression')
            with self.assertRaises(ValueError): module.review(a, b)
            a.write_text(json.dumps({'schema_version': 1, 'saved_on':'2026-10-01','indicators':{}}))
            self.assertEqual(module.review(b, a)['indicators']['eurostat']['comparison'], 'missing_previous')

    def test_status_changes_and_unchanged_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a', Path(tmp) / 'b'
            old = sample(); new = copy.deepcopy(old)
            new['indicators']['eurostat']['status'] = 'p'
            new['indicators']['world_bank']['provider_updated'] = '2026-12-01'
            a.write_text(json.dumps(old)); b.write_text(json.dumps(new))
            results = module.review(b, a)['indicators']
            self.assertEqual(results['world_bank']['comparison'], 'unchanged_observation')
            self.assertEqual(results['eurostat']['comparison'], 'same_period_changed')

    def test_cli_require_complete_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshot.json'
            obj = sample(); del obj['indicators']['world_bank']
            path.write_text(json.dumps(obj))
            before = path.read_bytes()
            proc = subprocess.run([sys.executable, str(ROOT / 'scripts/open_data_review.py'), str(path), '--require-complete'],
                                  capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('missing', proc.stderr)
            self.assertEqual(path.read_bytes(), before)

    def test_cli_regression_blocks_publication_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_path, new_path = Path(tmp) / 'old', Path(tmp) / 'new'
            old, new = sample(), sample()
            new['indicators']['eurostat']['period'] = '2024'
            old_path.write_text(json.dumps(old)); new_path.write_text(json.dumps(new))
            cmd = [sys.executable, str(ROOT / 'scripts/open_data_review.py'), str(new_path), '--previous', str(old_path),
                   '--require-complete', '--reject-regression']
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['indicators']['eurostat']['comparison'], 'period_regression')
            new['indicators']['eurostat']['period'] = '2026'
            new_path.write_text(json.dumps(new))
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            workflow = (ROOT / '.github/workflows/open_logistics_data.yml').read_text()
            self.assertLess(workflow.index('scripts/open_data_review.py'), workflow.index('git add data/open-logistics.json'))

    def test_invalid_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshot.json'
            for mutation in ('schema', 'date', 'period', 'bool', 'nan', 'negative', 'unexpected'):
                obj = sample()
                if mutation == 'schema': obj['schema_version'] = True
                if mutation == 'date': obj['saved_on'] = '2026-02-30'
                if mutation == 'period': obj['indicators']['world_bank']['period'] = '22'
                if mutation == 'bool': obj['indicators']['world_bank']['value'] = True
                if mutation == 'nan': obj['indicators']['world_bank']['value'] = float('nan')
                if mutation == 'negative': obj['indicators']['eurostat']['value'] = -1
                if mutation == 'unexpected': obj['indicators']['other'] = {}
                path.write_text(json.dumps(obj))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): module.review(path)


if __name__ == '__main__': unittest.main()
