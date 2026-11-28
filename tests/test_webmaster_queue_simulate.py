import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_queue_simulate as s

A='a'*40
class Tests(unittest.TestCase):
    def test_only_temporary_preparation_and_cleanup(self):
        with tempfile.TemporaryDirectory() as root:
            paths=[]
            def prepare(queue,repo,token,baseline):
                self.assertEqual((repo,token,baseline),('x/y','private',A))
                path=queue.db.execute('PRAGMA database_list').fetchone()[2];paths.append(path)
                self.assertTrue(os.path.isfile(path))
                return {'mode':'prepare_only','blocked':0,'deployment':{'count':0},'pending':[]}
            result=s.run('x/y','private',root,git=lambda *a:A,prepare_queue=prepare)
            self.assertEqual(result['yandex_requests'],0);self.assertFalse(result['persistent'])
            self.assertFalse(os.path.exists(paths[0]));self.assertNotIn('private',str(result))
    def test_no_run_for_nonmanual_or_nonmain(self):
        for event,ref in [('push','refs/heads/main'),('workflow_dispatch','refs/heads/other')]:
            with mock.patch.dict(os.environ,{'GITHUB_EVENT_NAME':event,'GITHUB_REF':ref},clear=True),mock.patch.object(s,'run') as run,mock.patch('builtins.print'):
                self.assertEqual(s.main(),1);run.assert_not_called()
    def test_suppresses_private_errors(self):
        with mock.patch.dict(os.environ,{'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_TOKEN':'secret'},clear=True),mock.patch.object(s,'run',side_effect=ValueError('secret')),mock.patch('builtins.print') as output:
            self.assertEqual(s.main(),1);self.assertNotIn('secret',str(output.call_args_list))
    def test_invalid_temp_no_preparation(self):
        prepare=mock.Mock()
        with self.assertRaises(ValueError):s.run('x/y','secret','relative',prepare_queue=prepare)
        prepare.assert_not_called()
if __name__=='__main__':unittest.main()
