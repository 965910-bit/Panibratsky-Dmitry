import os
import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_diagnostic as a

class Tests(unittest.TestCase):
    def setUp(self):self.calls=[]
    def fetch(self,path,token,params):
        self.calls.append((path,params.copy()))
        if path=='accountSummaries':return {'accountSummaries':[{'propertySummaries':[{'property':'properties/123','canEdit':True}]}]}
        if path=='properties/123/dataStreams':return {'dataStreams':[{'webStreamData':{'measurementId':a.MEASUREMENT,'defaultUri':'https://scm-news.ru/'}}]}
        if path=='properties/123/keyEvents':return {'keyEvents':[{'eventName':'contact_phone_click'},{'eventName':'unrelated_private_event'}]}
        raise AssertionError('unexpected endpoint')
    def run_inventory(self,fetch=None):return a.inventory('id','secret','refresh',refresh=lambda *args:'token',fetch=fetch or self.fetch)
    def test_inventory_identifies_exact_stream_without_leaking_other_events(self):
        data=self.run_inventory();self.assertTrue(data['can_edit']);self.assertTrue(data['domain_matches'])
        self.assertEqual(data['key_event_count'],2);self.assertEqual(data['present'],['contact_phone_click'])
        self.assertNotIn('unrelated_private_event',str(data));self.assertEqual(len(self.calls),3)
    def test_pagination_all_pages_and_repeated_token_fails(self):
        def two(path,token,params):
            if 'pageToken' not in params:return {'keyEvents':[{'eventName':'a'}],'nextPageToken':'n'}
            return {'keyEvents':[{'eventName':'b'}]}
        self.assertEqual(len(a.pages('properties/123/keyEvents','keyEvents','token',fetch=two)),2)
        with self.assertRaises(a.AnalyticsError):a.pages('properties/123/keyEvents','keyEvents','token',fetch=lambda *x:{'nextPageToken':'repeat'})
    def test_bad_property_or_ambiguous_match_stops(self):
        def bad(path,token,params):return {'accountSummaries':[{'propertySummaries':[{'property':'properties/123/other'}]}]}
        with self.assertRaises(a.AnalyticsError):self.run_inventory(bad)
        def duplicate(path,token,params):
            result=self.fetch(path,token,params)
            if path.endswith('dataStreams'):result['dataStreams']*=2
            return result
        with self.assertRaises(a.AnalyticsError):self.run_inventory(duplicate)
    def test_unknown_permissions_stop(self):
        def bad(path,token,params):
            data=self.fetch(path,token,params)
            if path=='accountSummaries':data['accountSummaries'][0]['propertySummaries'][0].pop('canEdit')
            return data
        with self.assertRaises(a.AnalyticsError):self.run_inventory(bad)
    def test_wrong_domain_not_proven(self):
        def other(path,token,params):
            data=self.fetch(path,token,params)
            if path.endswith('dataStreams'):data['dataStreams'][0]['webStreamData']['defaultUri']='https://other.example/'
            return data
        self.assertFalse(self.run_inventory(other)['domain_matches'])
    def test_missing_token_no_requests(self):
        fetch=mock.Mock();refresh=mock.Mock()
        with self.assertRaises(a.AnalyticsError):a.inventory('','','',fetch=fetch,refresh=refresh)
        refresh.assert_not_called();fetch.assert_not_called()
    def test_untrusted_endpoint_rejected(self):
        with self.assertRaises(a.AnalyticsError):a.request('https://evil/','secret',{})
    def test_redact_error(self):
        env={'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY_ID':'1102759388'}
        with mock.patch.dict(os.environ,env,clear=True),mock.patch.object(a,'inventory',side_effect=ValueError('secret')),mock.patch('builtins.print') as output:
            self.assertEqual(a.main(),1);self.assertNotIn('secret',str(output.call_args_list))
if __name__=='__main__':unittest.main()
