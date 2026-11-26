import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_publication_candidate.py'


class PublicationCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.write('data/news.json', 'old')
        self.write('data/open-logistics.json', 'old')
        self.write('trends.html', 'old')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, path, data):
        file = self.repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(data)

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-qm', 'candidate')
        return self.git('rev-parse', 'HEAD')

    def check(self, candidate, kind='news', base=None):
        return subprocess.run([sys.executable, str(SCRIPT), '--repo', str(self.repo),
                               '--base', base or self.base, '--candidate', candidate,
                               '--kind', kind], capture_output=True, text=True)

    def test_data_only_candidate_passes(self):
        self.write('data/news.json', 'new')
        self.assertEqual(0, self.check(self.commit()).returncode)

    def test_code_and_deletions_are_rejected(self):
        self.write('data/news.json', 'new')
        self.write('scripts/unexpected.py', 'code')
        self.assertNotEqual(0, self.check(self.commit()).returncode)
        self.git('reset', '--hard', self.base)
        (self.repo / 'trends.html').unlink()
        self.assertNotEqual(0, self.check(self.commit()).returncode)

    def test_wrong_base_and_multiple_commits_rejected(self):
        self.write('data/news.json', 'first')
        first = self.commit()
        self.write('data/news.json', 'second')
        second = self.commit()
        self.assertNotEqual(0, self.check(second).returncode)
        self.assertEqual(0, self.check(second, base=first).returncode)
        self.assertNotEqual(0, self.check(second, base='main').returncode)

    def test_symlink_and_executable_rejected(self):
        news = self.repo / 'data/news.json'
        news.unlink()
        news.symlink_to('../trends.html')
        self.assertNotEqual(0, self.check(self.commit()).returncode)
        self.git('reset', '--hard', self.base)
        news.write_text('new')
        news.chmod(0o755)
        self.assertNotEqual(0, self.check(self.commit()).returncode)

    def test_open_data_only_allows_new_archive_files(self):
        prefix = 'data/open-logistics-archives/' + 'a' * 64
        self.write(prefix + '/manifest.json', '{}')
        self.write('data/open-logistics.json', 'new')
        first = self.commit()
        self.assertEqual(0, self.check(first, 'open-data').returncode)
        self.write(prefix + '/manifest.json', '{"altered": true}')
        second = self.commit()
        self.assertNotEqual(0, self.check(second, 'open-data', base=first).returncode)


if __name__ == '__main__':
    unittest.main()
