"""All remote workflow actions must use immutable full Git commit hashes."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ActionsPinsTests(unittest.TestCase):
    def test_remote_actions_use_full_commit_sha(self):
        count = 0
        for path in (ROOT / '.github' / 'workflows').glob('*.yml'):
            for use in re.findall(r'^\s*-?\s*uses:\s*([^\s#]+)', path.read_text(encoding='utf-8'), re.M):
                if use.startswith('./') or use.startswith('docker://'):
                    continue
                count += 1
                self.assertRegex(use, r'^[\w.-]+/[\w./-]+@[a-f0-9]{40}$', f'{path}: {use}')
        self.assertGreater(count, 0)


if __name__ == '__main__': unittest.main()
