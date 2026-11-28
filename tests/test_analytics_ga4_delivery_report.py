import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_delivery_report as d
class Tests(unittest.TestCase):
    def info(self,*a,**k):return {'domain_matches':True,'property':'properties/123','token':'private'}
    def query(self,result,events=None):
        return d.status(('a','b','c'),('d','e','f'),identify=self.info,list_pages=lambda *a: events or [],refresh=lambda *a:'token',fetch=lambda *a:result)
    def test_absent_and_present(self):
        self.assertFalse(self.query({}))
        self.assertTrue(self.query({'rows':[{'dimensionValues':[{'value':d.EVENT}],'metricValues':[{'value':'1'}]}]}))
    def test_rejects_invalid_data(self):
        for data in ({'rows':'bad'},{'rows':[{'dimensionValues':[{'value':'other'}],'metricValues':[{'value':'1'}]}]}, {'rows':[{'dimensionValues':[{'value':d.EVENT}],'metricValues':[{'value':'-1'}]}]}):
            with self.assertRaises(d.AnalyticsError):self.query(data)
    def test_rejects_key_event(self):
        with self.assertRaises(d.AnalyticsError):self.query({},events=[{'eventName':d.EVENT}])
if __name__=='__main__':unittest.main()
