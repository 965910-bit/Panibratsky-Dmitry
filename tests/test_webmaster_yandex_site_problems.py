import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_yandex_site_problems as d
from webmaster_actions import SITE, ActionError

class Tests(unittest.TestCase):
    def fake(self, problems, verified=True):
        calls=[]
        def request(url,token,scheme,method='GET',body=None):
            calls.append(method)
            if url.endswith('/user'):return {'user_id':1}
            if url.endswith('/hosts'):return {'hosts':[{'ascii_host_url':SITE,'verified':verified,'host_id':'https:scm-news.ru:443'}]}
            if url.endswith('/diagnostics'):return {'problems':problems}
            raise AssertionError('unexpected')
        return request,calls
    def test_fixed_codes_read_only(self):
        req,calls=self.fake({'ERRORS_IN_SITEMAPS':{'state':'PRESENT'},'UNTRUSTED secret':{'state':'PRESENT'}})
        result=d.inspect('private',request=req)
        self.assertEqual(result['ERRORS_IN_SITEMAPS'],'PRESENT');self.assertEqual(result['NO_SITEMAPS'],'NOT_REPORTED')
        self.assertNotIn('secret',str(result));self.assertEqual(calls,['GET']*3)
    def test_bad_data(self):
        for problems,verified in (({},False),([],True)):
            req,_=self.fake(problems,verified)
            with self.assertRaises(ActionError):d.inspect('x',request=req)
    def test_unknown_state_not_leaked_or_treated_as_clear(self):
        req,_=self.fake({'ERRORS_IN_SITEMAPS':{'state':'private'}})
        result=d.inspect('t',request=req)
        self.assertEqual(result['ERRORS_IN_SITEMAPS'],'UNKNOWN_STATE')
        self.assertNotIn('private',str(result))
    def test_sanitized_http_error(self):
        with mock.patch.dict('os.environ',{'SCM_WM_YANDEX_ACCESS_TOKEN':'secret'},clear=True),mock.patch.object(d,'inspect',side_effect=d.ApiError(504,'secret')),mock.patch('builtins.print') as p:
            self.assertEqual(d.main(),1);self.assertIn('http=504',str(p.call_args_list));self.assertNotIn('secret',str(p.call_args_list))
    def test_no_leaks(self):
        with mock.patch.dict('os.environ',{'SCM_WM_YANDEX_ACCESS_TOKEN':'secret'},clear=True),mock.patch.object(d,'inspect',side_effect=ValueError('secret')),mock.patch('builtins.print') as p:
            self.assertEqual(d.main(),1);self.assertNotIn('secret',str(p.call_args_list))
if __name__=='__main__':unittest.main()
