import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_deploy_summary as s

class Tests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'out'
    def tearDown(self):self.tmp.cleanup()
    def write(self,data):self.path.write_text(data,encoding='utf-8');return s.render(self.path)
    def test_disabled_and_missing(self):
        self.assertIn('не подтверждено',s.render(self.path));self.assertIn('выключена',self.write(s.DISABLED))
    def test_safe_summary_and_unknown(self):
        data={'sources':{'google':{'status':'not_connected'},'yandex':{'status':'error','result':{'recrawl':[{'url':'<script>','status':'unknown'}]},'deferred_urls':['<img>']}}}
        text=self.write(json.dumps(data));self.assertIn('&lt;script&gt;',text);self.assertNotIn('<script>',text);self.assertIn('unknown',text);self.assertIn('Не отправлены: 1',text)
    def test_unknown_data_fails_closed(self):
        for data in ({'sources':{'google':{'status':'ok'},'yandex':{'status':'ok','result':{'recrawl':[{'url':'x','status':'evil'}]}}}},'x'):
            self.assertIn('не подтверждено',self.write(json.dumps(data)))
    def test_many_urls_are_bounded(self):
        data={'sources':{'google':{'status':'ok'},'yandex':{'status':'not_connected','deferred_urls':['u']*30}}}
        text=self.write(json.dumps(data));self.assertIn('Не отправлены: 30',text);self.assertEqual(text.count('<code>u</code>'),25)
    def test_accepts_success_and_no_url(self):
        data={'sources':{'google':{'status':'ok'},'yandex':{'status':'ok','result':{'sitemap':'submitted','recrawl':[]},'deferred_urls':[]}}}
        self.assertIn('вызов завершён',self.write(json.dumps(data)))

if __name__=='__main__':unittest.main()
