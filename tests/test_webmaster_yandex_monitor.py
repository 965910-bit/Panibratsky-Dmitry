import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import webmaster_yandex_monitor as m

class Tests(unittest.TestCase):
    def test_present_and_missing_are_read_only_success(self):
        for state in ('already_present', 'would_submit'):
            read=mock.Mock(return_value={'verified':True,'sitemap':state,'quota_remaining':50})
            alert=mock.Mock(return_value='clear')
            self.assertEqual(m.monitor('private','a/b','123','github-private',read=read,alert=alert),('success',state,50,'clear'))
            self.assertEqual(alert.call_args.args[3],'success')
    def test_failure_or_invalid_data_opens_access_alert_not_map_alert(self):
        for read in (mock.Mock(side_effect=Exception('secret')),mock.Mock(return_value={'verified':True,'sitemap':'would_submit','quota_remaining':True})):
            alert=mock.Mock(return_value='created')
            self.assertEqual(m.monitor('private','a/b','123','private',read=read,alert=alert),('failure','unknown',None,'created'))
            self.assertEqual(alert.call_args.args[3],'failure')
    def test_no_secrets_in_exception_output(self):
        with mock.patch.dict('os.environ',{'SCM_WM_YANDEX_ACCESS_TOKEN':'secret','GITHUB_TOKEN':'secret'},clear=True),mock.patch.object(m,'monitor',side_effect=RuntimeError('secret')),mock.patch('builtins.print') as p:
            self.assertEqual(m.main(),1)
            self.assertNotIn('secret',str(p.call_args_list))
    def test_alert_sync_failure_is_failure(self):
        with self.assertRaises(RuntimeError):
            m.monitor('t','a/b','123','t',read=lambda t: {'verified':True,'sitemap':'already_present','quota_remaining':1},alert=mock.Mock(side_effect=RuntimeError()))

if __name__=='__main__': unittest.main()
