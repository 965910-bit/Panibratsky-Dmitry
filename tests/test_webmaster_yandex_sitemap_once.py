import json
import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_yandex_sitemap_once as w

SHA='a'*40
class Tests(unittest.TestCase):
    def fetch(self, *, advance=False, build=True):
        calls=[]
        def f(url,token):
            calls.append(url)
            if url.endswith('/pages/builds/latest'):result={'status':'built' if build else 'error','commit':SHA}
            else:result={'object':{'sha':'b'*40 if advance and len(calls)>2 else SHA}}
            return 200,{},json.dumps(result).encode()
        return f
    def test_success_only_sitemap_no_recrawl(self):
        action=mock.Mock(return_value={'sitemap':'submitted','recrawl':[]});validate=mock.Mock()
        result=w.run('a/b','g','t',git=lambda *a:SHA,fetch=self.fetch(),validate=validate,action=action)
        self.assertEqual(result,'submitted');validate.assert_called_once_with([]);action.assert_called_once_with('t',[],True)
    def test_blocks_stale_or_bad_deployment(self):
        for fetch in (self.fetch(build=False),self.fetch(advance=True)):
            action=mock.Mock()
            with self.assertRaises(w.ActionError):w.run('a/b','g','t',git=lambda *a:SHA,fetch=fetch,validate=lambda u:None,action=action)
            action.assert_not_called()
    def test_preflight_failure_has_no_write(self):
        action=mock.Mock()
        with self.assertRaises(ValueError):w.run('a/b','g','t',git=lambda *a:SHA,fetch=self.fetch(),validate=mock.Mock(side_effect=ValueError()),action=action)
        action.assert_not_called()
    def test_invalid_response_is_error_not_success(self):
        with self.assertRaises(w.ActionError):w.run('a/b','g','t',git=lambda *a:SHA,fetch=self.fetch(),validate=lambda u:None,action=lambda *a:{'sitemap':'secret','recrawl':[]})
    def test_reruns_and_other_events_blocked(self):
        for event,attempt in [('workflow_dispatch','2'),('push','1')]:
            with mock.patch.dict('os.environ',{'GITHUB_EVENT_NAME':event,'GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':attempt},clear=True),mock.patch('builtins.print'),mock.patch.object(w,'run') as run:
                self.assertEqual(w.main(),1);run.assert_not_called()
    def test_sanitized_notice(self):
        env={'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':'1','GITHUB_TOKEN':'secret','SCM_WM_YANDEX_ACCESS_TOKEN':'secret','GITHUB_REPOSITORY':'a/b'}
        with mock.patch.dict('os.environ',env,clear=True),mock.patch.object(w,'run',return_value='already_present'),mock.patch('builtins.print') as p:
            self.assertEqual(w.main(),0);self.assertNotIn('secret',str(p.call_args_list))

if __name__=='__main__':unittest.main()
