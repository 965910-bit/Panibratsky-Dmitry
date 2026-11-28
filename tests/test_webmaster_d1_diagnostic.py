import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_d1_diagnostic as d
A='a'*32
class Tests(unittest.TestCase):
    def test_no_config_no_network(self):
        read=mock.Mock();self.assertEqual(d.inspect('','',read=read),'not_configured');read.assert_not_called()
    def test_present_and_absent(self):
        def read(entries,pages=1):return lambda *a:{'success':True,'result':entries,'result_info':{'total_pages':pages}}
        self.assertEqual(d.inspect(A,'secret',read=read([{'name':'scm-webmaster-queue'}])),'separate_queue_exists')
        self.assertEqual(d.inspect(A,'secret',read=read([{'name':'scm-review'}])),'separate_queue_not_found')
    def test_pagination_and_exact_match(self):
        calls=[]
        def read(a,t,page):
            calls.append(page);return {'success':True,'result':[{'name':'scm-webmaster-queue-staging' if page==1 else d.NAME}],'result_info':{'total_pages':2}}
        self.assertEqual(d.inspect(A,'secret',read=read),'separate_queue_exists');self.assertEqual(calls,[1,2])
    def test_invalid_or_incomplete_never_means_absent(self):
        for data in ({'success':False,'result':[],'result_info':{'total_pages':1}}, {'success':True,'result':[]}, {'success':True,'result':[{}],'result_info':{'total_pages':1}}, {'success':True,'result':[],'result_info':{'total_pages':11}}):
            with self.assertRaises(d.DiagnosticError):d.inspect(A,'secret',read=lambda *a:data)
    def test_incomplete_credentials_no_network(self):
        read=mock.Mock()
        for account,token in ((A,''),('','x'),('bad','x'),(A,'x\ny')):
            with self.assertRaises(d.DiagnosticError):d.inspect(account,token,read=read)
        read.assert_not_called()
    def test_http_status_sanitized(self):
        with mock.patch.dict('os.environ',{'CLOUDFLARE_ACCOUNT_ID':A,'CLOUDFLARE_API_TOKEN':'secret'},clear=True),mock.patch.object(d,'inspect',side_effect=d.HttpStatus(403)),mock.patch('builtins.print') as p:
            self.assertEqual(d.main(),1);self.assertIn('http=403',str(p.call_args_list));self.assertNotIn('secret',str(p.call_args_list));self.assertNotIn(A,str(p.call_args_list))
    def test_safe_error_output(self):
        with mock.patch.dict('os.environ',{'CLOUDFLARE_ACCOUNT_ID':A,'CLOUDFLARE_API_TOKEN':'secret'},clear=True),mock.patch.object(d,'inspect',side_effect=Exception('secret')),mock.patch('builtins.print') as p:
            self.assertEqual(d.main(),1);self.assertNotIn('secret',str(p.call_args_list));self.assertNotIn(A,str(p.call_args_list))
    def test_redirects_refused(self):self.assertIsNone(d.NoRedirect().redirect_request(None,None,302,'',{},'https://example.com'))
if __name__=='__main__':unittest.main()
