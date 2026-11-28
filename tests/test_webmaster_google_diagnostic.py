import os
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_google_diagnostic as g

class Tests(unittest.TestCase):
    def setUp(self):self.calls=[]
    def req(self,sites,maps):
        def call(url,token,scheme):
            self.calls.append((url,scheme))
            if url==g.GOOGLE_API+'/sites':return sites
            if url.endswith('/sitemaps'):return maps
            self.fail('unexpected URL')
        return call
    def run_inspect(self,sites,maps):
        return g.inspect('id','secret','refresh',refresh=lambda *args:'access',request=self.req(sites,maps))
    def test_no_creds_no_network(self):
        request=mock.Mock();refresh=mock.Mock()
        self.assertEqual(g.inspect('','','',request=request,refresh=refresh),{'status':'not_connected'})
        request.assert_not_called();refresh.assert_not_called()
    def test_incomplete_creds_no_network(self):
        request=mock.Mock();refresh=mock.Mock()
        with self.assertRaises(g.GoogleDiagnosticError):g.inspect('id','','',request=request,refresh=refresh)
        request.assert_not_called();refresh.assert_not_called()
    def test_select_exact_prefix_and_present_sitemap(self):
        sites={'siteEntry':[{'siteUrl':g.DOMAIN_PROPERTY,'permissionLevel':'siteOwner'},{'siteUrl':g.SITE,'permissionLevel':'siteFullUser'}]}
        self.assertEqual(self.run_inspect(sites,{'sitemap':[{'path':g.MAP}]}),{'status':'connected','property_type':'url_prefix','permission':'siteFullUser','sitemap':'present','sitemap_health':'unknown'})
        self.assertTrue(self.calls[-1][0].endswith('/sites/'+quote(g.SITE,safe='')+'/sitemaps'))
    def test_missing_property_does_not_query_sitemaps(self):
        self.assertEqual(self.run_inspect({'siteEntry':[{'siteUrl':'https://other.example/'}]},{}),{'status':'property_missing'})
        self.assertEqual(len(self.calls),1)
    def test_unverified_not_considered_connected(self):
        self.assertEqual(self.run_inspect({'siteEntry':[{'siteUrl':g.SITE,'permissionLevel':'siteUnverifiedUser'}]},{}),{'status':'unverified','permission':'siteUnverifiedUser'})
        self.assertEqual(len(self.calls),1)
    def test_domain_and_absent_sitemap(self):
        result=self.run_inspect({'siteEntry':[{'siteUrl':g.DOMAIN_PROPERTY,'permissionLevel':'siteOwner'}]}, {})
        self.assertEqual(result['property_type'],'domain');self.assertEqual(result['sitemap'],'not_listed')
    def test_invalid_data_fails_closed(self):
        for sites,maps in [({'siteEntry':'wrong'},{}),({'siteEntry':[{'siteUrl':g.SITE,'permissionLevel':'mystery'}]},{}),({'siteEntry':[{'siteUrl':g.SITE,'permissionLevel':'siteOwner'}]},{'sitemap':'wrong'}),({'siteEntry':[{'siteUrl':g.SITE,'permissionLevel':'siteOwner'}]*2},{})]:
            with self.assertRaises(g.GoogleDiagnosticError):self.run_inspect(sites,maps)
    def test_sitemap_health_conservative(self):
        self.assertEqual(g.sitemap_health({'errors':'2'}),'error')
        self.assertEqual(g.sitemap_health({'errors':'0','isPending':True}),'pending')
        self.assertEqual(g.sitemap_health({'errors':'0','isPending':False,'lastDownloaded':'2020-01-01T00:00:00Z'}),'healthy')
        for item in ({},{'errors':0,'isPending':False},{'errors':'bad'},{'errors':True},{'errors':0,'isPending':False,'lastDownloaded':'2999-01-01T00:00:00Z'}):
            self.assertEqual(g.sitemap_health(item),'unknown')
    def test_safe_sitemap_metadata(self):
        from datetime import datetime, timezone
        now=datetime(2026,11,16,tzinfo=timezone.utc)
        result=g.sitemap_metadata({'errors':'2','warnings':'3','isPending':False,'lastDownloaded':'2026-11-01T00:00:00Z','private':'secret'},now=now)
        self.assertEqual(result,{'errors':2,'warnings':3,'pending':'false','download_age':'7_to_30_days'})
        self.assertNotIn('secret',str(result))
        invalid=g.sitemap_metadata({'errors':True,'warnings':'-1','isPending':'yes','lastDownloaded':'2999-01-01T00:00:00Z'},now=now)
        self.assertEqual(invalid,{'errors':None,'warnings':None,'pending':'unknown','download_age':'unknown'})
    def test_redacts_error(self):
        with mock.patch.dict(os.environ,{'SCM_WM_GOOGLE_CLIENT_ID':'secret'},clear=True),mock.patch.object(g,'inspect',side_effect=ValueError('secret')),mock.patch('builtins.print') as output:
            self.assertEqual(g.main(),1);self.assertNotIn('secret',str(output.call_args_list))
if __name__=='__main__':unittest.main()
