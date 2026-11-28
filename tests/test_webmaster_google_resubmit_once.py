import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_google_resubmit_once as g

class Tests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,16,tzinfo=timezone.utc)
        self.item={'path':g.MAP,'errors':'100','isPending':False,'lastDownloaded':'2026-09-01T00:00:00Z','lastSubmitted':'2026-09-01T00:00:00Z'}
        self.calls=[];self.validate=Mock()
    def request(self,url,token,scheme,method='GET'):
        self.calls.append((url,method))
        if url==g.GOOGLE_API+'/sites':return {'siteEntry':[{'siteUrl':g.DOMAIN_PROPERTY,'permissionLevel':'siteOwner'}]}
        if method=='PUT':return {}
        return {'sitemap':[self.item]}
    def run_action(self):return g.resubmit(('id','secret','refresh'),refresh=lambda *a:'token',request=self.request,validate=self.validate,now=self.now)
    def test_one_write_after_validation(self):
        self.assertEqual(self.run_action(),'submitted');self.validate.assert_called_once_with([])
        self.assertEqual([method for _,method in self.calls],['GET','GET','PUT'])
        self.assertTrue(self.calls[-1][0].endswith(g.quote(g.MAP,safe='')))
    def test_recent_or_unknown_are_not_eligible(self):
        for key,value in [('lastSubmitted','2026-11-15T00:00:00Z'),('lastDownloaded',None),('isPending',True),('errors','0'),('lastSubmitted',None)]:
            with self.subTest(key=key):
                old=self.item[key];self.item[key]=value;self.assertEqual(self.run_action(),'not_eligible');self.item[key]=old
        self.validate.assert_not_called();self.assertFalse(any(m=='PUT' for _,m in self.calls))
    def test_validation_failure_has_no_write(self):
        self.validate.side_effect=ValueError('private');
        with self.assertRaises(ValueError):self.run_action()
        self.assertFalse(any(m=='PUT' for _,m in self.calls))
    def test_failure_is_not_retried(self):
        def req(*a,**kw):
            if kw.get('method')=='PUT':self.calls.append(('write','PUT'));raise TimeoutError()
            return self.request(*a,**kw)
        with self.assertRaises(TimeoutError):g.resubmit(('a','b','c'),refresh=lambda *a:'t',request=req,validate=self.validate,now=self.now)
        self.assertEqual(sum(m=='PUT' for _,m in self.calls),1)
if __name__=='__main__':unittest.main()
