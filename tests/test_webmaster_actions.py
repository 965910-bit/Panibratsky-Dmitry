import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import webmaster_actions as w

PAGE = w.BASE + 'wiki.html'
class Fake:
    def __init__(self, sitemap=False, quota=2, recrawl_error=None):
        self.calls = []; self.sitemap=sitemap; self.quota=quota; self.recrawl_error=recrawl_error
    def __call__(self, url, token, scheme, method='GET', body=None):
        self.calls.append((url, method, body))
        if url.endswith('/user'): return {'user_id': 12}
        if url.endswith('/hosts'): return {'hosts':[{'ascii_host_url':w.SITE,'host_id':'https:scm-news.ru:443','verified':True}]}
        if url.endswith('/sites'): return {'siteEntry':[{'siteUrl':w.SITE}]}
        if url.endswith('/sitemaps') and method=='GET': return {'sitemap':[{'path':w.MAP}] if self.sitemap else []}
        if 'user-added-sitemaps?limit=100' in url:
            return {'count':1 if self.sitemap else 0,'sitemaps':[{'sitemap_url':w.MAP}] if self.sitemap else []}
        if url.endswith('/user-added-sitemaps'): return {'sitemap_id':'x'}
        if url.endswith('/recrawl/quota'): return {'quota_remainder':self.quota}
        if url.endswith('/recrawl/queue'):
            if self.recrawl_error: raise self.recrawl_error
            return {'task_id':'task-1','quota_remainder':self.quota-1}
        return {}

class Tests(unittest.TestCase):
    def test_dry_run_never_writes(self):
        f=Fake(); self.assertEqual(w.google_action('secret',False,f)['status'],'would_submit')
        r=w.yandex_action('secret',[PAGE],False,f)
        self.assertEqual(r['recrawl'][0]['status'],'would_submit')
        self.assertTrue(all(method=='GET' for _,method,_ in f.calls))
    def test_google_submit_once_only_missing(self):
        f=Fake(sitemap=True);self.assertEqual(w.google_action('x',True,f)['status'],'already_present')
        self.assertTrue(all(method=='GET' for _,method,_ in f.calls))
        f=Fake();self.assertEqual(w.google_action('x',True,f)['status'],'submitted')
        self.assertEqual([x[1] for x in f.calls],['GET','GET','PUT'])
    @mock.patch.object(w, "SITEMAP_WRITES_PAUSED", False)
    def test_yandex_write_and_quota(self):
        f=Fake(quota=0);r=w.yandex_action('x',[PAGE],True,f)
        self.assertEqual(r['sitemap'],'submitted');self.assertEqual(r['recrawl'][0]['status'],'quota_exhausted')
        self.assertFalse(any(u.endswith('/recrawl/queue') for u,_,_ in f.calls))
    @mock.patch.object(w, "SITEMAP_WRITES_PAUSED", False)
    def test_yandex_sitemap_missing_id_is_unknown_not_success(self):
        f=Fake()
        def req(url,*a,**kw):
            if url.endswith('/user-added-sitemaps') and kw.get('method') == 'POST':
                return {}
            return f(url,*a,**kw)
        with self.assertRaises(w.ActionError): w.yandex_action('x',[],True,req)

    def test_sitemap_provider_read_only_stops_before_any_post(self):
        f=Fake()
        with mock.patch.object(w,'SITEMAP_WRITES_PAUSED',True):
            with self.assertRaises(w.ActionError): w.yandex_action('x',[PAGE],True,f)
        self.assertTrue(all(method=='GET' for _,method,_ in f.calls))
    def test_already_added_and_quota_errors(self):
        for code,status,expected in [('URL_ALREADY_ADDED',409,'already_added'),('QUOTA_EXCEEDED',429,'quota_exhausted')]:
            f=Fake(sitemap=True,recrawl_error=w.ApiError(status,code));r=w.yandex_action('x',[PAGE],True,f)
            self.assertEqual(r['recrawl'][0]['status'],expected)
    def test_incomplete_sitemap_list_fails_closed(self):
        f=Fake();orig=f.__call__
        def req(url,*a,**kw):
            if 'user-added-sitemaps?limit=100' in url:return {'count':101,'sitemaps':[]}
            return orig(url,*a,**kw)
        with self.assertRaises(w.ActionError): w.yandex_action('x',[PAGE],True,req)
        self.assertTrue(all(method=='GET' for _,method,_ in f.calls))
    def test_url_allowlist(self):
        self.assertEqual(w.allowed_urls([PAGE]),[PAGE])
        for urls in [['https://evil.test/'],[PAGE,PAGE],[PAGE+'?x=1'],[PAGE+'#x']]:
            with self.assertRaises(w.ActionError): w.allowed_urls(urls)
    def test_preflight_failure_prevents_all_provider_calls(self):
        with mock.patch.dict('os.environ', {'SCM_YANDEX_WEBMASTER_TOKEN':'secret'}, clear=True), mock.patch.object(w, 'validate_live', side_effect=ValueError('bad live data')), mock.patch.object(w, 'yandex_action') as action, mock.patch('builtins.print'):
            self.assertEqual(w.main(['--apply','--url',PAGE]), 1)
            action.assert_not_called()
    def test_missing_tokens_means_no_changes(self):
        with mock.patch.dict('os.environ',{},clear=True), mock.patch.object(w,'validate_live') as validate, mock.patch('builtins.print'):
            self.assertEqual(w.main(['--apply','--url',PAGE]),1)
            validate.assert_not_called()

if __name__=='__main__': unittest.main()
