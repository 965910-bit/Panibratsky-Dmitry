import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_privacy_inventory as p
class Tests(unittest.TestCase):
    def find(self,*args,**kwargs):return {'domain_matches':True,'property':'properties/123','stream':'properties/123/dataStreams/456','token':'private'}
    def read(self,path,token,params=None):
        if path.endswith('enhancedMeasurementSettings'):return {'name':'properties/123/dataStreams/456/enhancedMeasurementSettings','streamEnabled':True,'formInteractionsEnabled':True}
        if path.endswith('dataRedactionSettings'):return {'name':'properties/123/dataStreams/456/dataRedactionSettings','emailRedactionEnabled':True}
        if path.endswith('googleAdsLinks'):return {'googleAdsLinks':[{'customerId':'private-customer'}]}
        raise AssertionError()
    def test_returns_flags_and_count_only(self):
        data=p.inventory_settings(('a','b','c'),find=self.find,read=self.read)
        self.assertEqual(data['ads_links'],1);self.assertTrue(data['forms']);self.assertTrue(data['email_redaction']);self.assertNotIn('private',str(data))
    def test_wrong_stream_fails_before_request(self):
        def bad(*a,**kw):
            result=self.find();result['stream']='properties/987/dataStreams/456';return result
        with self.assertRaises(p.AnalyticsError):p.inventory_settings(('a','b','c'),find=bad,read=self.read)
    def test_invalid_flag_stops(self):
        def bad(path,token,params=None):
            if path.endswith('enhancedMeasurementSettings'):return {'name':'properties/123/dataStreams/456/enhancedMeasurementSettings','streamEnabled':'false'}
            return self.read(path,token,params)
        with self.assertRaises(p.AnalyticsError):p.inventory_settings(('a','b','c'),find=self.find,read=bad)
    def test_untrusted_endpoint_rejected(self):
        with self.assertRaises(p.AnalyticsError):p.get('https://attacker','secret')
if __name__=='__main__':unittest.main()
