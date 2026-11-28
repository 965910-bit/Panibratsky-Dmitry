import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_google_monitor as m

class Tests(unittest.TestCase):
    def run_monitor(self,status,health=None):
        calls=[]
        def alert(repo,run,token,outcome,*,title,body_template):
            calls.append((title,outcome));return 'synced'
        def read(*args):
            if status=='error':raise ValueError('private')
            return {'status':status,'sitemap_health':health}
        result=m.monitor(('id','secret','refresh'),'a/b','1','gh',read=read,alert=alert)
        return result,calls
    def test_missing_error_alert(self):
        for health in ('missing','error'):
            result,calls=self.run_monitor('connected',health)
            self.assertEqual(result[:2],('success',health))
            self.assertEqual(calls,[(m.ACCESS_TITLE,'success'),(m.SITEMAP_TITLE,'failure')])
    def test_healthy_resolves(self):
        _,calls=self.run_monitor('connected','healthy')
        self.assertEqual(calls,[(m.ACCESS_TITLE,'success'),(m.SITEMAP_TITLE,'success')])
    def test_pending_unknown_does_not_close_or_open(self):
        for health in ('pending','unknown'):
            result,calls=self.run_monitor('connected',health)
            self.assertEqual(result[3],'unknown');self.assertEqual(calls,[(m.ACCESS_TITLE,'success')])
    def test_failed_read_alerts_access_does_not_touch_sitemap(self):
        for status in ('error','not_connected','unverified','property_missing'):
            result,calls=self.run_monitor(status)
            self.assertEqual(result[:2],('failure','unknown'))
            self.assertEqual(calls,[(m.ACCESS_TITLE,'failure')])
    def test_unrecognized_health_is_failure_not_success(self):
        result,calls=self.run_monitor('connected','bogus')
        self.assertEqual(result[:2],('failure','unknown'));self.assertEqual(calls,[(m.ACCESS_TITLE,'failure')])
if __name__=='__main__':unittest.main()
