import os
import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_google_inspection as g

class Tests(unittest.TestCase):
    def diag(self,*args):return {'status':'connected','property_type':'domain'}
    def test_bounded_and_exact_property(self):
        calls=[]
        def call(token,url,prop):
            calls.append((url,prop));return {'inspectionResult':{'indexStatusResult':{'verdict':'PASS','coverageState':'Submitted and indexed'}}}
        result=g.inspect_pages(('id','secret','refresh'),diagnostic=self.diag,refresh=lambda *a:'token',call=call)
        self.assertEqual(len(result),5);self.assertEqual(calls,[(u,g.DOMAIN_PROPERTY) for u in g.URLS]);self.assertTrue(all(x['verdict']=='PASS' for x in result))
    def test_stop_on_unknown_network_no_retry(self):
        call=mock.Mock(side_effect=TimeoutError('private'))
        result=g.inspect_pages(('i','s','r'),diagnostic=self.diag,refresh=lambda *a:'token',call=call)
        self.assertEqual(call.call_count,1);self.assertEqual(result[0]['verdict'],'UNKNOWN')
    def test_untrusted_strings_redacted(self):
        call=lambda *a:{'inspectionResult':{'indexStatusResult':{'verdict':'evil','coverageState':'secret\nmessage'}}}
        result=g.inspect_pages(('i','s','r'),diagnostic=self.diag,refresh=lambda *a:'token',call=call)
        self.assertTrue(all(x['verdict']=='UNKNOWN' and x['coverage']=='UNKNOWN' for x in result))
    def test_failed_property_no_calls(self):
        call=mock.Mock()
        with self.assertRaises(g.InspectionError):g.inspect_pages(('i','s','r'),diagnostic=lambda *a:{'status':'property_missing'},call=call)
        call.assert_not_called()
    def test_rejects_untrusted_inputs_before_network(self):
        with self.assertRaises(g.InspectionError):g.request('secret','https://other/','anything')
    def test_entrypoint_guards(self):
        with mock.patch.dict(os.environ,{},clear=True),mock.patch.object(g,'inspect_pages') as check:
            self.assertEqual(g.main(),1);check.assert_not_called()
if __name__=='__main__':unittest.main()
