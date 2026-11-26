"""Exercise the workflow's Git publication step against a local throwaway remote."""
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


class NewsPublishGitTests(unittest.TestCase):
    def test_only_staged_public_outputs_trigger_commit(self):
        workflow = (ROOT / '.github/workflows/update_news.yml').read_text()
        start = workflow.index('      - name: Commit and push if changed')
        end = workflow.index('\n      # Opt-in only.', start)
        step = workflow[start:end].split('        run: |\n', 1)[1]
        script = textwrap.dedent(step)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / 'remote.git'
            repo = root / 'repo'
            subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
            subprocess.run(['git', 'init', '-b', 'main', str(repo)], check=True, capture_output=True)
            git(repo, 'config', 'user.name', 'Test')
            git(repo, 'config', 'user.email', 'test@example.invalid')
            git(repo, 'remote', 'add', 'origin', str(remote))
            (repo / 'data').mkdir()
            for name in ['data/news.json', 'trends.html', 'sitemap.xml', 'rss.xml', 'unrelated.txt']:
                (repo / name).write_text('old\n')
            git(repo, 'add', '.')
            git(repo, 'commit', '-m', 'base')
            git(repo, 'push', '-u', 'origin', 'main')
            before = git(repo, 'rev-parse', 'HEAD')
            (repo / 'unrelated.txt').write_text('local change\n')
            env = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1'}
            subprocess.run(['bash', '-e', '-c', script], cwd=repo, env=env, check=True, capture_output=True)
            self.assertEqual(before, git(repo, 'rev-parse', 'HEAD'))
            self.assertEqual('local change\n', (repo / 'unrelated.txt').read_text())
            (repo / 'data/news.json').write_text('new news\n')
            subprocess.run(['bash', '-e', '-c', script], cwd=repo, env=env, check=True, capture_output=True)
            head = git(repo, 'rev-parse', 'HEAD')
            self.assertNotEqual(before, head)
            self.assertEqual(head, git(remote, 'rev-parse', 'refs/heads/main'))
            self.assertEqual('data/news.json', git(repo, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'))
            self.assertEqual('local change\n', (repo / 'unrelated.txt').read_text())
            # A rejected push must remain an error; the committed output is still local.
            hook = remote / 'hooks/pre-receive'
            hook.write_text('#!/bin/sh\nexit 1\n')
            hook.chmod(0o755)
            (repo / 'data/news.json').write_text('rejected news\n')
            result = subprocess.run(['bash', '-e', '-c', script], cwd=repo, env=env, capture_output=True)
            self.assertNotEqual(0, result.returncode)
            self.assertEqual(head, git(remote, 'rev-parse', 'refs/heads/main'))
            self.assertNotEqual(head, git(repo, 'rev-parse', 'HEAD'))
            self.assertEqual('rejected news\n', (repo / 'data/news.json').read_text())


if __name__ == '__main__':
    unittest.main()
