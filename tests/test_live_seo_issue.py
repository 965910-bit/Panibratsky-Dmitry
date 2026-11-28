import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import live_seo_issue as a

REPO='owner/repo';RUN='123';TOKEN='private-token';BASE='https://api.github.com/repos/'+REPO

def bot_issue(number=1,body=None):
    return {'number':number,'title':a.TITLE,'body':body if body is not None else a.BODY.format(run='https://github.com/'+REPO+'/actions/runs/2'), 'user':{'login':'github-actions[bot]','type':'Bot'}}
class Fake:
    def __init__(self,issues=(),repo_id=a.REPOSITORY_ID):self.issues=list(issues);self.id=repo_id;self.calls=[]
    def __call__(self,url,token,*,method='GET',body=None):
        self.calls.append((url,method,body));
        if url == BASE:return {'id':self.id,'has_issues':True}
        if '?state=open' in url:return self.issues
        return {'number':42}

class Tests(unittest.TestCase):
    def test_failure_creates_fixed_public_issue_without_token(self):
        f=Fake();self.assertEqual(a.sync(REPO,RUN,TOKEN,'failure',call=f),'created')
        url,method,body=f.calls[-1];self.assertEqual((url,method),(BASE+'/issues','POST'))
        self.assertIn('https://github.com/'+REPO+'/actions/runs/'+RUN,body['body']);self.assertNotIn(TOKEN,str(body))
    def test_failure_deduplicates(self):
        f=Fake([bot_issue()]);self.assertEqual(a.sync(REPO,RUN,TOKEN,'failure',call=f),'already_open')
        self.assertTrue(all(c[1]=='GET' for c in f.calls))
    def test_success_closes_only_matching_bot_issue(self):
        f=Fake([bot_issue()]);self.assertEqual(a.sync(REPO,RUN,TOKEN,'success',call=f),'closed')
        self.assertEqual(f.calls[-1],(BASE+'/issues/1','PATCH',{'state':'closed','state_reason':'completed'}))
    def test_unrelated_user_or_edited_issue_not_touched(self):
        for issue in (dict(bot_issue(),user={'login':'person','type':'User'}),bot_issue(body=a.MARKER+' changed'),dict(bot_issue(),pull_request={})):
            f=Fake([issue]);self.assertEqual(a.sync(REPO,RUN,TOKEN,'success',call=f),'clear')
            self.assertTrue(all(c[1]=='GET' for c in f.calls))
    def test_duplicate_match_or_wrong_repo_no_mutation(self):
        for f in (Fake([bot_issue(),bot_issue(2)]),Fake(repo_id=3)):
            with self.assertRaises(a.AlertError):a.sync(REPO,RUN,TOKEN,'failure',call=f)
            self.assertTrue(all(c[1]=='GET' for c in f.calls))
    def test_unverified_outcome_no_network(self):
        f=Fake()
        for outcome in ('','skipped','cancelled','bogus'):
            with self.assertRaises(a.AlertError):a.sync(REPO,RUN,TOKEN,outcome,call=f)
        self.assertEqual(f.calls,[])
    def test_too_many_pages_fail_closed(self):
        def f(url,token,**kw):return {'id':a.REPOSITORY_ID,'has_issues':True} if url==BASE else [{}]*100
        with self.assertRaises(a.AlertError):a.sync(REPO,RUN,TOKEN,'failure',call=f)
    def test_ambiguous_write_not_retried(self):
        f=Fake();calls=[]
        def call(url,token,**kw):
            calls.append((url,kw.get('method','GET')))
            if kw.get('method')=='POST':raise TimeoutError()
            return f(url,token,**kw)
        with self.assertRaises(TimeoutError):a.sync(REPO,RUN,TOKEN,'failure',call=call)
        self.assertEqual(sum(method=='POST' for _,method in calls),1)
    def test_separate_templates_never_close_each_others_issue(self):
        import webmaster_yandex_monitor as m
        user_issue=bot_issue()
        f=Fake([user_issue]);self.assertEqual(a.sync(REPO,RUN,TOKEN,'success',call=f,title=m.TITLE,body_template=m.BODY),'clear')
        self.assertTrue(all(c[1]=='GET' for c in f.calls))
        f=Fake([user_issue]);self.assertEqual(a.sync(REPO,RUN,TOKEN,'failure',call=f,title=m.TITLE,body_template=m.BODY),'created')
        created=f.calls[-1][2]
        bot={'number':45,'title':created['title'],'body':created['body'],'user':{'login':'github-actions[bot]','type':'Bot'}}
        f=Fake([user_issue,bot]);self.assertEqual(a.sync(REPO,RUN,TOKEN,'success',call=f,title=m.TITLE,body_template=m.BODY),'closed')
        self.assertEqual(f.calls[-1][0],BASE+'/issues/45')
    def test_bad_credentials_never_printed(self):
        with mock.patch.dict('os.environ',{'GITHUB_TOKEN':TOKEN},clear=True),mock.patch('builtins.print') as p:
            self.assertEqual(a.main(),1);self.assertNotIn(TOKEN,str(p.call_args))

if __name__=='__main__':unittest.main()
