import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_yandex_discovered as d
from webmaster_actions import MAP, SITE, ActionError

class Tests(unittest.TestCase):
    def fake(self, entries, verified=True):
        calls=[]
        def request(url, token, scheme, method='GET', body=None):
            calls.append(method)
            if url.endswith('/user'): return {'user_id':42}
            if url.endswith('/hosts'): return {'hosts':[{'ascii_host_url':SITE,'verified':verified,'host_id':'https:scm-news.ru:443'}]}
            if url.endswith('/sitemaps?limit=100'): return {'sitemaps':entries}
            raise AssertionError('unexpected')
        return request,calls
    def test_found_and_read_only(self):
        req,calls=self.fake([{'sitemap_url':MAP,'errors_count':0,'urls_count':37,'sources':['ROBOTS_TXT','untrusted'], 'last_access_date':'2025-01-02T00:00:00,000+0300'}])
        self.assertEqual(d.inspect('secret',request=req),{'state':'found','errors':0,'urls':37,'sources':['ROBOTS_TXT'],'access_date':'2025-01-02'})
        self.assertEqual(calls,['GET']*3)
    def test_missing_first_page_not_global_absence(self):
        req,_=self.fake([]);self.assertEqual(d.inspect('x',request=req),{'state':'not_found_in_first_page'})
    def test_fail_closed(self):
        for entries,verified in (([],False),([{'sitemap_url':MAP,'urls_count':True,'errors_count':0,'sources':[]}],True),([{'sitemap_url':MAP}]*2,True)):
            req,calls=self.fake(entries,verified)
            with self.assertRaises(ActionError):d.inspect('x',request=req)
            self.assertTrue(all(c=='GET' for c in calls))
    def test_no_leak(self):
        with mock.patch.dict('os.environ',{'SCM_WM_YANDEX_ACCESS_TOKEN':'secret'},clear=True),mock.patch.object(d,'inspect',side_effect=ValueError('secret')),mock.patch('builtins.print') as p:
            self.assertEqual(d.main(),1);self.assertNotIn('secret',str(p.call_args_list))

if __name__=='__main__':unittest.main()
