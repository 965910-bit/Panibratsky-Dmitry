import json
import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import webmaster_after_deploy as w
import webmaster_actions as actions

SHA='b'*40
BEFORE='a'*40
EVENT={'action':'completed','workflow_run':{'head_sha':SHA,'head_branch':'main','conclusion':'success','workflow_id':55,'created_at':'2026-01-02T00:00:00Z','id':100,'run_attempt':1}}
class Fake:
    def __init__(self, advance=False):self.refs=0;self.advance=advance
    def __call__(self, url, token=None, body=None):
        if '/workflows/55/runs?' in url:
            data={'workflow_runs':[{'id':99,'created_at':'2026-01-01T00:00:00Z','head_sha':BEFORE,'head_branch':'main','conclusion':'success'}]}
        elif '/workflows/55' in url:
            data={'name':'pages-build-deployment','path':'dynamic/pages/pages-build-deployment'}
        elif '/git/ref/heads/main' in url:
            self.refs+=1;data={'object':{'sha':'c'*40 if self.advance and self.refs>1 else SHA}}
        else: raise AssertionError(url)
        return 200,{},json.dumps(data).encode()

def fake_git(*args):
    if args[0]=='rev-parse':return SHA
    return 'wiki.html\nREADME.md\n'

def ancestry(*args,**kwargs):pass

class Tests(unittest.TestCase):
    def test_verified_changed_only(self):
        plan=w.build_plan(EVENT,'org/repo','private',fetch=Fake(),git=fake_git,ancestry=ancestry)
        self.assertEqual(plan['urls'],[actions.BASE+'wiki.html'])
    def test_no_writes_if_main_advances(self):
        google=mock.Mock();yandex=mock.Mock()
        with self.assertRaises(actions.ActionError):
            w.run(EVENT,'org/repo','gh',{'id':'a','secret':'b','refresh':'c'},'y',fetch=Fake(True),git=fake_git,ancestry=ancestry,validate=lambda urls:None,refresh=lambda *x:'g',google_call=google,yandex_call=yandex)
        google.assert_not_called();yandex.assert_not_called()
    def test_provider_failure_does_not_suppress_other(self):
        def fail(*args):raise RuntimeError('secret error')
        r=w.run(EVENT,'org/repo','gh',{'id':'a','secret':'b','refresh':'c'},'y',fetch=Fake(),git=fake_git,ancestry=ancestry,validate=lambda urls:None,refresh=lambda *x:'g',google_call=fail,yandex_call=lambda t,u,a:{'sitemap':'already_present','recrawl':[{'url':u[0],'status':'accepted','task_id':'c7fe80c0-36e3-11e6-8b2d-df96aa592c0a'}]})
        self.assertEqual(r['sources']['google']['status'],'error')
        self.assertEqual(r['sources']['yandex']['status'],'ok')
        self.assertNotIn('secret',json.dumps(r))
    def test_more_than_five_are_reported_not_lost_in_summary(self):
        from generate_sitemap import PAGES
        changed = [p for p in PAGES if p][:7]
        def git(*args):
            return SHA if args[0]=='rev-parse' else '\n'.join(changed)
        submitted=[]
        def yandex(t, urls, apply):
            submitted.extend(urls)
            return {'sitemap':'already_present','recrawl':[{'url':urls[0],'status':'already_added'}]}
        r=w.run(EVENT,'org/repo','gh',{},'y',fetch=Fake(),git=git,ancestry=ancestry,validate=lambda urls:None,yandex_call=yandex)
        self.assertEqual(len(submitted),5)
        self.assertEqual(len(r['sources']['yandex']['deferred_urls']),2)

    def test_partial_failure_keeps_receipt_unknown_and_deferred(self):
        urls=[actions.BASE + p for p in list(actions.PAGES)[:4]]
        plan={'urls':urls,'sha':SHA,'github_api':'https://api.github.com/repos/org/repo'}
        calls=[]
        def action(token,batch,apply):
            calls.append(batch[0])
            if len(calls)==2:raise TimeoutError('secret')
            return {'sitemap':'already_present','recrawl':[{'url':batch[0],'status':'accepted','task_id':'c7fe80c0-36e3-11e6-8b2d-df96aa592c0a'}]}
        r=w.run_yandex_batch(plan,'gh','token',Fake(),action)
        self.assertEqual(r['status'],'error');self.assertEqual(r['result']['recrawl'][0]['status'],'accepted')
        self.assertEqual(r['result']['recrawl'][1],{'url':urls[1],'status':'unknown'})
        self.assertEqual(r['deferred_urls'],urls[2:]);self.assertEqual(len(calls),2)
        self.assertNotIn('secret',json.dumps(r))
    def test_quota_exhaustion_stops_remaining(self):
        urls=[actions.BASE+p for p in list(actions.PAGES)[:3]]
        plan={'urls':urls,'sha':SHA,'github_api':'https://api.github.com/repos/org/repo'}
        action=mock.Mock(side_effect=lambda t,u,a:{'sitemap':'already_present','recrawl':[{'url':u[0],'status':'quota_exhausted'}]})
        r=w.run_yandex_batch(plan,'gh','token',Fake(),action)
        self.assertEqual(r['result']['recrawl'][0]['status'],'quota_exhausted');self.assertEqual(r['deferred_urls'],urls[1:]);self.assertEqual(action.call_count,1)
    def test_new_main_stops_before_next_write(self):
        urls=[actions.BASE+p for p in list(actions.PAGES)[:3]]
        plan={'urls':urls,'sha':SHA,'github_api':'https://api.github.com/repos/org/repo'}
        action=mock.Mock(side_effect=lambda t,u,a:{'sitemap':'already_present','recrawl':[{'url':u[0],'status':'already_added'}]})
        r=w.run_yandex_batch(plan,'gh','token',Fake(True),action)
        self.assertEqual(action.call_count,1);self.assertEqual(r['deferred_urls'],urls[1:]);self.assertEqual(r['status'],'error')
    def test_no_changes_still_checks_sitemap(self):
        plan={'urls':[],'sha':SHA,'github_api':'https://api.github.com/repos/org/repo'}
        action=mock.Mock(return_value={'sitemap':'submitted','recrawl':[]})
        r=w.run_yandex_batch(plan,'gh','token',Fake(),action)
        action.assert_called_once_with('token',[],True);self.assertEqual(r['status'],'ok')
    def test_bad_result_does_not_expose_provider_fields(self):
        url=actions.BASE+'wiki.html';plan={'urls':[url],'sha':SHA,'github_api':'https://api.github.com/repos/org/repo'}
        r=w.run_yandex_batch(plan,'gh','token',Fake(),lambda *a:{'sitemap':'already_present','recrawl':[{'url':url,'status':'accepted','task_id':'secret'}]})
        self.assertEqual(r['result']['recrawl'][0]['status'],'unknown');self.assertNotIn('secret',str(r))

    def test_preflight_failure_blocks_provider_calls(self):
        g=mock.Mock(); y=mock.Mock()
        def reject(urls):raise ValueError('mismatch')
        with self.assertRaises(ValueError):
            w.run(EVENT,'org/repo','gh',{'id':'a'},'y',fetch=Fake(),git=fake_git,ancestry=ancestry,validate=reject,google_call=g,yandex_call=y)
        g.assert_not_called();y.assert_not_called()
    def test_disabled_does_not_read_secrets_or_connect(self):
        with mock.patch.dict('os.environ',{},clear=True),mock.patch('builtins.print'),mock.patch.object(w,'run') as run:
            self.assertEqual(w.main(),0);run.assert_not_called()
    def test_rerun_blocked(self):
        with mock.patch.dict('os.environ',{'SCM_WEBMASTER_AUTOMATION':'1','GITHUB_RUN_ATTEMPT':'2'},clear=True),mock.patch('builtins.print'),mock.patch.object(w,'run') as run:
            self.assertEqual(w.main(),1);run.assert_not_called()
    def test_no_auth_fails_when_enabled(self):
        with mock.patch.dict('os.environ',{'SCM_WEBMASTER_AUTOMATION':'1'},clear=True),mock.patch('builtins.print'),mock.patch.object(w,'run') as run:
            self.assertEqual(w.main(),1);run.assert_not_called()
    def test_invalid_event_fails_closed(self):
        event={'action':'completed','workflow_run':dict(EVENT['workflow_run'],head_branch='other')}
        with self.assertRaises(actions.ActionError):w.build_plan(event,'org/repo','gh',fetch=Fake(),git=fake_git,ancestry=ancestry)

if __name__=='__main__':unittest.main()
