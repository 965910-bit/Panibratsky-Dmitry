import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_synthetic_history as m
class Tests(unittest.TestCase):
 def execute(self,response):return m.inspect(('a','b','c'),('d','e','f'),identify=lambda *a,**k:{'property':'properties/123','domain_matches':True},refresh=lambda *a:'t',fetch=lambda *a:response)
 def test_empty_is_not_seen(self):self.assertEqual(self.execute({}), (False,False,False))
 def test_observed(self):self.assertEqual(self.execute({'rows':[{'dimensionValues':[{'value':'scm_delivery_test'}],'metricValues':[{'value':'3'}]}]}),(True,False,False))
 def test_unapproved_row(self):
  with self.assertRaises(m.Error):self.execute({'rows':[{'dimensionValues':[{'value':'private'}],'metricValues':[{'value':'3'}]}]})
if __name__=='__main__':unittest.main()
