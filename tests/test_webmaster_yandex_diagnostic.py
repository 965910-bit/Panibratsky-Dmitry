import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_yandex_diagnostic as d
from webmaster_actions import ActionError, MAP, SITE

class Tests(unittest.TestCase):
    def fake(self, verified=True, present=True, quota=3):
        calls=[]
        def request(url,token,scheme,method='GET',body=None):
            calls.append((url,method))
            if url.endswith('/user'):return {'user_id':1}
            if url.endswith('/hosts'):return {'hosts':[{'ascii_host_url':SITE,'verified':verified,'host_id':'https:scm-news.ru:443'}]}
            if '/user-added-sitemaps?' in url:return {'count':int(present),'sitemaps':[{'sitemap_url':MAP}] if present else []}
            if url.endswith('/recrawl/quota'):return {'quota_remainder':quota}
            raise AssertionError(url)
        return request,calls
    def test_real_shape_is_read_only(self):
        request,calls=self.fake();self.assertEqual(d.inspect('private',request=request),{'verified':True,'sitemap':'already_present','quota_remaining':3})
        self.assertTrue(all(method=='GET' for url,method in calls));self.assertTrue(any('https%3Ascm-news.ru%3A443' in url for url,method in calls))
    def test_missing_map_never_adds_it(self):
        request,calls=self.fake(present=False);self.assertEqual(d.inspect('t',request=request)['sitemap'],'would_submit')
        self.assertTrue(all(method=='GET' for url,method in calls))
    def test_unverified_or_malformed_quota_fails(self):
        for args in ({'verified':False},{'quota':True},{'quota':-1}):
            request,_=self.fake(**args)
            with self.assertRaises(ActionError):d.inspect('t',request=request)
    def test_no_token_never_calls_api(self):
        request=mock.Mock()
        with self.assertRaises(ActionError):d.inspect('',request=request)
        request.assert_not_called()
    def test_main_suppresses_provider_error(self):
        with mock.patch.dict('os.environ',{'SCM_WM_YANDEX_ACCESS_TOKEN':'secret'},clear=True),mock.patch.object(d,'inspect',side_effect=Exception('secret')),mock.patch('builtins.print') as p:
            self.assertEqual(d.main(),1);self.assertNotIn('secret',str(p.call_args))

if __name__=='__main__':unittest.main()
