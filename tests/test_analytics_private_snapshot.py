import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_private_snapshot as s
class Tests(unittest.TestCase):
 def sample(self,ga=None,gsc=None):
  def analytics(prop,token,method,body):
   if 'dimensions' in body:return {'rows':[{'dimensionValues':[{'value':s.GOALS[0]}],'metricValues':[{'value':'4'}]}]}
   return {'rows':[{'metricValues':[{'value':'1'},{'value':'2'},{'value':'3'}]}]}
  return s.collect(('a','b','c'),('d','e','f'),('g','h','i'),identify=lambda *a,**k:{'property':'properties/123','domain_matches':True},refresh=lambda *a:'token',ga=ga or analytics,gsc_identify=lambda *a,**k:{'status':'connected','property_type':'domain'},gsc=gsc or (lambda *a:{'rows':[{'clicks':1,'impressions':10,'ctr':.1,'position':3}]}))
 def test_aggregate_only_and_null(self):
  r=self.sample(gsc=lambda *a:{})
  self.assertEqual(r['ga4']['totals']['sessions'],2);self.assertIsNone(r['search_console'][0]['metrics']);self.assertEqual(r['ga4']['events'][s.GOALS[0]],4)
 def test_reject_unapproved_event(self):
  def ga(prop,token,method,body):
   return {'rows':[{'dimensionValues':[{'value':'private'}],'metricValues':[{'value':'1'}]}]} if 'dimensions' in body else {'rows':[]}
  with self.assertRaises(s.SnapshotError):self.sample(ga=ga)
 def test_publishes_ciphertext_only(self):
  calls=[]
  def call(url,token,**kw):
   calls.append(kw);return {'id':77} if kw.get('method')=='POST' else {'id':1102759388}
  self.assertEqual(s.publish({'private':123},'owner/repo','token',seal=lambda data:{'encrypted':'opaque'},call=call),77)
  self.assertNotIn('123',str(calls));self.assertNotIn('private\":',str(calls))
if __name__=='__main__':unittest.main()
