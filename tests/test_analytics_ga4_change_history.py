import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_change_history as c
class Tests(unittest.TestCase):
    def find(self,*a,**kw):return {'property':'properties/123','token':'private','domain_matches':True,'present':['contact_phone_click']}
    def accounts(self,*a,**kw):return [{'account':'accounts/987','propertySummaries':[{'property':'properties/123'}]}]
    def test_pagination_and_no_private_details(self):
        def read(acct,token,body):
            if 'pageToken' not in body:return {'changeHistoryEvents':[{'changes':[{'action':'CREATED','resourceAfterChange':{'keyEvent':{'eventName':'contact_phone_click'}}}],'userActorEmail':'private'}],'nextPageToken':'n'}
            return {'changeHistoryEvents':[{'changes':[{'resourceAfterChange':{'keyEvent':{'eventName':'interest_book'}}}]}]}
        result=c.inspect_history(('a','b','c'),find=self.find,read_pages=self.accounts,read=read)
        self.assertEqual(result['known_creations_observed'],1);self.assertEqual(result['target_changes'],1);self.assertNotIn('private',str(result))
    def test_filtered_history_is_reported(self):
        result=c.inspect_history(('a','b','c'),find=self.find,read_pages=self.accounts,read=lambda *a:{'changeHistoryEvents':[{'changesFiltered':True}]})
        self.assertTrue(result['filtered'])
    def test_loop_or_ambiguous_account_fails(self):
        with self.assertRaises(c.AnalyticsError):c.inspect_history(('a','b','c'),find=self.find,read_pages=self.accounts,read=lambda *a:{'nextPageToken':'repeat'})
        with self.assertRaises(c.AnalyticsError):c.inspect_history(('a','b','c'),find=self.find,read_pages=lambda *a:self.accounts()*2,read=lambda *a:{})
    def test_untrusted_account_rejected(self):
        with self.assertRaises(c.AnalyticsError):c.history_request('https://evil','secret',{})
if __name__=='__main__':unittest.main()
