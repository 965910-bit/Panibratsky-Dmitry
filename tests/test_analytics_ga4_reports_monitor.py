import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_reports_monitor as m
class Tests(unittest.TestCase):
    def test_success_empty_is_still_success(self):
        alert=mock.Mock(return_value='clear')
        status,result,notice=m.monitor([],[],'owner/repo','1','token',read=lambda *args:{'observed':[],'thresholded':False,'sampled':False},alert=alert)
        self.assertEqual((status,notice),('success','clear'));self.assertEqual(result['observed'],[]);self.assertEqual(alert.call_args.args[3],'success')
    def test_read_failure_sends_generic_failure(self):
        def fail(*args):raise ValueError('sensitive')
        alert=mock.Mock(return_value='created')
        status,result,notice=m.monitor([],[],'owner/repo','1','token',read=fail,alert=alert)
        self.assertEqual((status,result,notice),('failure',None,'created'));self.assertEqual(alert.call_args.args[3],'failure');self.assertNotIn('sensitive',str(alert.call_args))
    def test_alert_failure_propagates(self):
        with self.assertRaises(ValueError):m.monitor([],[],'owner/repo','1','token',read=lambda *args:{'observed':[]},alert=mock.Mock(side_effect=ValueError()))
if __name__=='__main__':unittest.main()
