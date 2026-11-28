import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_replace_goals as m
class Tests(unittest.TestCase):
    def setUp(self):
        self.events=[{'name':f'properties/123/keyEvents/{i+1}','eventName':f'old_{i}','custom':True,'deletable':True} for i in range(6)]
        self.events += [{'name':f'properties/123/keyEvents/{i+20}','eventName':n,'custom':True,'deletable':True} for i,n in enumerate(m.GOALS) if n not in m.TARGETS]
        self.events += [{'name':'properties/123/keyEvents/999','eventName':'system','custom':False,'deletable':False}]
        self.fps=frozenset(m.fingerprint(e) for e in self.events[:6]);self.deletes=[];self.posts=[];self.ads=[]
    def find(self,*a,**k):
        names={e['eventName'] for e in self.events};old=[e for e in self.events if e['eventName'] not in m.GOALS]
        return {'property':'properties/123','token':'token','domain_matches':True,'can_edit':True,'key_event_count':len(self.events),'present':[n for n in m.GOALS if n in names],'missing':[n for n in m.GOALS if n not in names],'old_custom_deletable':sum(e.get('custom',False) and e.get('deletable',False) for e in old),'custom_total':sum(e.get('custom',False) for e in self.events)}
    def pages(self,path,field,token,**kw):return list(self.ads) if field=='googleAdsLinks' else list(self.events)
    def delete(self,prop,token,name):self.deletes.append(name);self.events=[e for e in self.events if e['name']!=name]
    def post(self,prop,token,name):self.posts.append(name);self.events.append({'name':f'properties/123/keyEvents/{100+len(self.posts)}','eventName':name,'custom':True,'deletable':True})
    def run_migration(self,**kw):return m.migrate(('a','b','c'),find=self.find,list_pages=self.pages,delete=kw.get('delete',self.delete),post=kw.get('post',self.post),fingerprints=kw.get('fingerprints',self.fps))
    def test_migrate_all_and_keep_system(self):
        r=self.run_migration();self.assertEqual(r,{'deleted':6,'created':7,'present':30,'missing':0,'old_custom':0,'total':31})
        self.assertEqual(self.posts[-1],'interest_book');self.assertTrue(any(e['eventName']=='system' for e in self.events))
    def test_ads_or_backup_mismatch_prevents_all_writes(self):
        self.ads=[{'name':'linked'}]
        with self.assertRaises(m.AnalyticsError):self.run_migration()
        self.ads=[];self.events[0]['eventName']='changed'
        with self.assertRaises(m.AnalyticsError):self.run_migration()
        self.assertEqual(self.deletes,[]);self.assertEqual(self.posts,[])
    def test_uncertain_delete_stops_without_retry(self):
        def fail(*a):self.deletes.append('attempt');raise TimeoutError()
        with self.assertRaises(TimeoutError):self.run_migration(delete=fail)
        self.assertEqual(len(self.deletes),1);self.assertEqual(self.posts,[])
    def test_unconfirmed_create_stops(self):
        def fail(*a):self.posts.append(a[-1])
        with self.assertRaises(m.AnalyticsError):self.run_migration(post=fail)
        self.assertEqual(len(self.deletes),6);self.assertEqual(len(self.posts),1)
if __name__=='__main__':unittest.main()
