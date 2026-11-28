import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_configure as c
import analytics_ga4_diagnostic as d

class ConfigureTests(unittest.TestCase):
    def setUp(self):
        self.names={'resume_click_hh','resume_click_zarplata'}; self.other=7; self.posts=[]
    def inspect(self,*args,**kwargs):
        return {'property':'properties/123','token':'secret','can_edit':True,'domain_matches':True,
            'present':[n for n in d.GOALS if n in self.names], 'missing':[n for n in d.GOALS if n not in self.names],
            'key_event_count':self.other+len(self.names)}
    def post(self,prop,token,name):self.posts.append(name);self.names.add(name)
    def test_bounded_preserves_existing_and_rerun_is_idempotent(self):
        r=c.configure(('a','b','c'),inspect=self.inspect,post=self.post)
        self.assertEqual(len(r['created']),21);self.assertEqual(len(r['present']),23);self.assertEqual(len(r['missing']),7)
        self.assertEqual(c.configure(('a','b','c'),inspect=self.inspect,post=self.post)['created'],[])
        self.assertEqual(len(self.posts),21)
    def test_wrong_domain_or_rights_stops(self):
        for field in ('domain_matches','can_edit'):
            def bad(*a,**kw):
                result=self.inspect();result[field]=False;return result
            with self.assertRaises(d.AnalyticsError):c.configure(('a','b','c'),inspect=bad,post=self.post)
        self.assertEqual(self.posts,[])
    def test_uncertain_post_stops_without_retry(self):
        def fail(prop,token,name):self.posts.append(name);self.names.add(name);raise TimeoutError()
        with self.assertRaises(d.AnalyticsError):c.configure(('a','b','c'),inspect=self.inspect,post=fail)
        self.assertEqual(len(self.posts),1)
    def test_success_without_readback_stops(self):
        with self.assertRaises(d.AnalyticsError):c.configure(('a','b','c'),inspect=self.inspect,post=lambda *args:None)
    def test_unapproved_request_rejected_before_network(self):
        for prop,name in [('https://evil','presentation_download'),('properties/123','other')]:
            with self.assertRaises(d.AnalyticsError):c.create(prop,'token',name)
if __name__=='__main__':unittest.main()
