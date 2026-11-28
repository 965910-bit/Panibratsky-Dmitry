import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import pagespeed_monitor as p
class Tests(unittest.TestCase):
    def data(self):return {'lighthouseResult':{'requestedUrl':p.SITE,'finalDisplayedUrl':p.SITE,'categories':{'performance':{'score':.87}},'audits':{'largest-contentful-paint':{'numericValue':2200},'cumulative-layout-shift':{'numericValue':.052},'total-blocking-time':{'numericValue':140}}},'loadingExperience':{'metrics':{'LARGEST_CONTENTFUL_PAINT_MS':{'category':'FAST'},'INTERACTION_TO_NEXT_PAINT':{'category':'SLOW'}}}}
    def test_lab_and_field_remain_separate(self):
        result=p.parse(self.data());self.assertEqual(result,{'score':87,'lcp_ms':2200,'cls':.052,'tbt_ms':140,'field_lcp':'good','field_cls':'unknown','field_inp':'poor'})
    def test_missing_field_is_unknown_not_zero(self):
        data=self.data();data.pop('loadingExperience');data['lighthouseResult']['audits'].pop('total-blocking-time')
        r=p.parse(data);self.assertIsNone(r['tbt_ms']);self.assertEqual(r['field_lcp'],'unknown')
    def test_invalid_or_unrelated_results_rejected(self):
        for field,value in [('requestedUrl','https://other.test/'),('finalDisplayedUrl','https://other.test/'),('runtimeError',{'code':'bad'})]:
            d=self.data();d['lighthouseResult'][field]=value
            with self.assertRaises(p.PageSpeedError):p.parse(d)
        d=self.data();d['lighthouseResult']['categories']['performance']['score']=float('nan')
        with self.assertRaises(p.PageSpeedError):p.parse(d)
    def test_quota_falls_back_to_local_lab_without_field(self):
        def quota():raise p.PageSpeedError('http_429')
        local=self.data();local.pop('loadingExperience')
        result,source=p.measure(remote=quota,local=lambda:local)
        self.assertEqual(source,'local_lighthouse');self.assertEqual(result['field_lcp'],'unknown')
        def failure():raise p.PageSpeedError('network_or_response')
        with self.assertRaises(p.PageSpeedError):p.measure(remote=failure,local=lambda:self.fail('unexpected fallback'))
    def test_guard_before_network(self):
        with patch.dict('os.environ',{'GITHUB_EVENT_NAME':'pull_request'},clear=True),patch.object(p,'request') as req:
            self.assertEqual(p.main(),1);req.assert_not_called()
if __name__=='__main__':unittest.main()
