import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_encrypted_backup as b

class Tests(unittest.TestCase):
    def info(self,*a,**k):return {'domain_matches':True,'can_edit':True,'property':'properties/123','token':'secret','key_event_count':2,'present':[b.GOALS[0]],'old_custom_deletable':1}
    def pages(self,*a):return [{'eventName':b.GOALS[0]},{'eventName':'private_old','custom':True,'deletable':True,'name':'private_id'}]
    def test_only_ciphertext_posted(self):
        calls=[];plaintext=[]
        def seal(raw):plaintext.append(json.loads(raw));return {'ciphertext':'encrypted'}
        def post(*a,**kw):
            calls.append((a,kw));return {'id':77} if kw.get('method')=='POST' else {'id':1102759388}
        result=b.backup(('a','b','c'),'owner/repo','token',find=self.info,list_pages=self.pages,seal=seal,post=post)
        self.assertEqual(result,(1,77));self.assertEqual(plaintext[0]['key_events'][0]['eventName'],'private_old')
        self.assertNotIn('private_old',str(calls));self.assertNotIn('private_id',str(calls));self.assertEqual(calls[-1][1]['method'],'POST')
    def test_state_change_stops_before_post(self):
        def find(*a,**kw):return dict(self.info(),key_event_count=4)
        called=[]
        with self.assertRaises(b.AnalyticsError):b.backup(('a','b','c'),'owner/repo','token',find=find,list_pages=self.pages,seal=lambda _:called.append('seal'),post=lambda *a,**k: {'id':1102759388})
        self.assertEqual(called,[])
    def test_wrong_repo_rejected(self):
        with self.assertRaises(b.AnalyticsError):b.backup(('a','b','c'),'bad/repo','token',post=lambda *a,**kw:{'id':1})
if __name__=='__main__':unittest.main()
