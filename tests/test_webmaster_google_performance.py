import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_google_performance as p
class Tests(unittest.TestCase):
    def test_periods_are_equal_and_nonoverlapping(self):
        (a,b),(c,d)=p.periods(date(2026,11,16));self.assertEqual((b-a).days,27);self.assertEqual((d-c).days,27);self.assertEqual((a-d).days,1)
    def test_compare_and_fixed_property(self):
        calls=[]
        def request(url,token,scheme,body):
            calls.append((url,body));return {'rows':[{'clicks':4 if len(calls)==1 else 2,'impressions':8 if len(calls)==1 else 10}]}
        result=p.run(('a','b','c'),refresh=lambda *x:'token',identify=lambda *a,**kw:{'status':'connected','property_type':'domain'},request=request,today=date(2026,11,16))
        self.assertEqual(result,{'status':'available','clicks':'up','impressions':'down'})
        self.assertEqual(len(calls),2);self.assertIn('sc-domain%3Ascm-news.ru',calls[0][0]);self.assertEqual(calls[0][1]['dataState'],'final')
        self.assertNotIn('4',str(result))
    def test_missing_data_is_not_zero(self):
        result=p.run(('a','b','c'),refresh=lambda *x:'token',identify=lambda *a,**kw:{'status':'connected','property_type':'domain'},request=lambda *a:{},today=date(2026,11,16))
        self.assertEqual(result['status'],'insufficient_data')
    def test_no_baseline_and_invalid_metric(self):
        self.assertEqual(p.direction(1,0),'no_baseline')
        with self.assertRaises(p.PerformanceError):p.run(('a','b','c'),refresh=lambda *x:'t',identify=lambda *a,**kw:{'status':'connected','property_type':'domain'},request=lambda *a:{'rows':[{'clicks':True,'impressions':2}]})
    def test_untrusted_property_is_blocked(self):
        with self.assertRaises(p.PerformanceError):p.run(('a','b','c'),refresh=lambda *x:'t',identify=lambda *a,**kw:{'status':'connected','property_type':'other'},request=lambda *a: self.fail('request made'))
if __name__=='__main__':unittest.main()
