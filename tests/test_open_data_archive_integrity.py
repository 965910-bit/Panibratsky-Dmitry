"""Offline integration checks against copies of the existing public capture."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_open_data_archives.py'


class ArchiveIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.snapshot = root / 'snapshot.json'
        self.archives = root / 'archives'
        shutil.copyfile(ROOT / 'data/open-logistics.json', self.snapshot)
        shutil.copytree(ROOT / 'data/open-logistics-archives', self.archives)
        self.bundle = next(self.archives.iterdir())

    def run_check(self):
        return subprocess.run([sys.executable, str(SCRIPT), '--snapshot', str(self.snapshot),
                               '--archives', str(self.archives)], capture_output=True, text=True)

    def test_both_publication_and_ci_call_verifier(self):
        for name in ('site-tests.yml', 'open_logistics_data.yml'):
            text = (ROOT / '.github/workflows' / name).read_text()
            self.assertIn('run: python scripts/check_open_data_archives.py', text)

    def test_real_fixture_passes_without_changes(self):
        before = {str(p.relative_to(self.archives)): p.read_bytes()
                  for p in self.archives.rglob('*') if p.is_file()}
        result = self.run_check()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(before, {str(p.relative_to(self.archives)): p.read_bytes()
                                  for p in self.archives.rglob('*') if p.is_file()})

    def test_detects_tampered_raw_data(self):
        (self.bundle / 'world_bank.json').write_bytes(b'{}')
        self.assertNotEqual(0, self.run_check().returncode)

    def test_rejects_valid_snapshot_without_matching_capture(self):
        snapshot = json.loads(self.snapshot.read_text())
        old = snapshot['indicators']['world_bank']['value']
        snapshot['indicators']['world_bank']['value'] = 3.0 if old != 3.0 else 4.0
        self.snapshot.write_text(json.dumps(snapshot))
        result = self.run_check()
        self.assertNotEqual(0, result.returncode)
        self.assertIn('does not match', result.stderr)

    def test_rejects_unexpected_files_and_symlinks(self):
        extra = self.bundle / 'private.txt'
        extra.write_text('example')
        self.assertNotEqual(0, self.run_check().returncode)
        extra.unlink()
        original = self.bundle / 'eurostat.json'
        copy = self.archives.parent / 'outside.json'
        shutil.copyfile(original, copy)
        original.unlink()
        original.symlink_to(copy)
        self.assertNotEqual(0, self.run_check().returncode)

    def test_rejects_missing_archive(self):
        shutil.rmtree(self.archives)
        self.assertNotEqual(0, self.run_check().returncode)


if __name__ == '__main__':
    unittest.main()
