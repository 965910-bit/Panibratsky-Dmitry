import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import site_uptime_monitor as m
class Tests(unittest.TestCase):
    def setUp(self):self.comments=[];self.posts=[]
    def call(self,url,token,*,method='GET',body=None):
        if method=='POST':self.posts.append(body);return {'id':1000}
        if url.endswith('/issues/244'):return {'number':244,'state':'open'}
        if '/comments?' in url:return self.comments
        return {'id':m.REPOSITORY_ID,'has_issues':True}
    def alert(self,up):return m.alert('owner/repo','123','token',up,call=self.call)
    def test_retry_and_recovery(self):
        calls=iter([False,False,True]);wait=[]
        self.assertTrue(m.availability(check=lambda:next(calls),wait=lambda n:wait.append(n)))
        self.assertEqual(wait,[8,8])
        self.assertFalse(m.availability(check=lambda:False,wait=lambda _:None))
    def test_failure_and_recovery_comment_only_on_transition(self):
        self.assertEqual(self.alert(True),'unchanged');self.assertEqual(self.alert(False),'notified')
        self.comments=[{'id':1,'user':{'login':'github-actions[bot]','type':'Bot'},'body':self.posts[-1]['body']}]
        self.assertEqual(self.alert(False),'unchanged');self.assertEqual(self.alert(True),'notified')
        self.assertEqual(len(self.posts),2);self.assertIn('status=recovery',self.posts[-1]['body'])
    def test_foreign_comment_does_not_change_state(self):
        self.comments=[{'id':1,'user':{'login':'someone','type':'User'},'body':m.MARKER+'\nstatus=failure\nX'}]
        self.assertEqual(self.alert(True),'unchanged')
    def test_wrong_repo_and_unknown_are_rejected(self):
        with self.assertRaises(m.MonitorError):m.alert('owner/repo','123','token',True,call=lambda *a,**k:{'id':1})
        with self.assertRaises(m.MonitorError):self.alert(None)
if __name__=='__main__':unittest.main()
