import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_products_inventory as p
class Tests(unittest.TestCase):
    def info(self,*a,**k):return {'property':'properties/123','stream':'properties/123/dataStreams/42','domain_matches':True,'token':'secret'}
    def run_info(self,bq,ad):return p.inspect(('a','b','c'),find=self.info,read_pages=lambda path,field,token,**k:bq if field=='bigqueryLinks' else ad)
    def test_returns_only_safe_flags(self):
        r=self.run_info([{'dailyExportEnabled':True,'streamingExportEnabled':True,'exportStreams':['properties/123/dataStreams/42'],'excludedEvents':['interest_book'],'project':'secret'}],[{'adClientCode':'secret'}])
        self.assertEqual(r['bigquery_links'],1);self.assertEqual(r['adsense_links'],1);self.assertTrue(r['flags'][0]['daily']);self.assertTrue(r['flags'][0]['target_stream_listed']);self.assertEqual(r['flags'][0]['agreed_events_excluded'],1);self.assertNotIn('secret',str(r))
    def test_absent_flags_and_empty_streams_are_not_guessed(self):
        r=self.run_info([{}],[]);self.assertFalse(r['flags'][0]['daily']);self.assertTrue(r['flags'][0]['stream_list_empty'])
    def test_rejects_bad_values(self):
        for x in [{'dailyExportEnabled':'true'},{'exportStreams':'bad'},{'excludedEvents':[None]}]:
            with self.assertRaises(p.AnalyticsError):self.run_info([x],[])
    def test_real_response_field_spelling(self):
        def fetch(path,token,params):
            return {'bigqueryLinks':[]} if path.endswith('/bigQueryLinks') else {'adsenseLinks':[{'adClientCode':'private'}]}
        r=p.inspect(('a','b','c'),find=self.info,fetch=fetch)
        self.assertEqual(r['adsense_links'],1)
    def test_rejects_arbitrary_destination(self):
        with self.assertRaises(p.AnalyticsError):p.get('https://example.com','token',{})
if __name__=='__main__':unittest.main()
