import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_reports_diagnostic as r
class Tests(unittest.TestCase):
    def find(self,*a,**kw):return {'property':'properties/123','domain_matches':True}
    def fetch(self,prop,token,method,body):
        self.assertEqual(prop,'properties/123');self.assertEqual(token,'report-token');self.assertEqual(method,'runReport')
        self.assertEqual(body['dateRanges'][0]['endDate'],'yesterday')
        return {'rows':[{'dimensionValues':[{'value':'presentation_download'}],'metricValues':[{'value':'12'}]}]}
    def test_find_only_observed_and_no_counts(self):
        res=r.inspect(('a','b','c'),('d','e','f'),identify=self.find,refresh=lambda *a:'report-token',fetch=self.fetch)
        self.assertEqual(res['observed'],['presentation_download']);self.assertNotIn('12',str(res))
    def test_absence_is_not_zero(self):
        res=r.inspect(('a','b','c'),('d','e','f'),identify=self.find,refresh=lambda *a:'t',fetch=lambda *a:{})
        self.assertEqual(res['observed'],[])
    def test_unknown_names_or_invalid_metric_fail(self):
        for name,value in [('private','2'),('presentation_download','-1')]:
            with self.assertRaises(r.ReportError):r.inspect(('a','b','c'),('d','e','f'),identify=self.find,refresh=lambda *a:'t',fetch=lambda *a:{'rows':[{'dimensionValues':[{'value':name}],'metricValues':[{'value':value}]}]})
    def test_property_and_endpoint_allowlist(self):
        for prop,method in [('https://evil','runReport'),('properties/1','other')]:
            with self.assertRaises(r.ReportError):r.request(prop,'token',method,{})
    def test_domain_mismatch_stops_before_report(self):
        def wrong(*a,**kw):return {'property':'properties/123','domain_matches':False}
        fetch=mock.Mock()
        with self.assertRaises(r.ReportError):r.inspect(('a','b','c'),('d','e','f'),identify=wrong,refresh=lambda *a:'t',fetch=fetch)
        fetch.assert_not_called()
if __name__=='__main__':unittest.main()
