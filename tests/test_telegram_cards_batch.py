import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'telegram-review' / 'cards_batch.py'

@unittest.skipIf(Image is None, 'Pillow is an optional dependency')
class CardsBatchTests(unittest.TestCase):
    def test_gallery_is_offline_unapproved_escaped_and_cannot_overwrite(self):
        draft = {'version':1, 'title':'Склад <script>alert(1)</script>', 'source_name':'Источник', 'source_url':'https://example.org/1', 'description':'<b>Текст</b>', 'comment':'', 'ready_for_review':False}
        with tempfile.TemporaryDirectory() as tmp:
            batch = Path(tmp)/'batch.json'; batch.write_text(json.dumps({'version':1,'drafts':[draft]},ensure_ascii=False),encoding='utf-8')
            output = Path(tmp)/'gallery'
            def run(): return subprocess.run([sys.executable,str(SCRIPT),str(batch),str(output)],capture_output=True,text=True)
            result=run(); self.assertEqual(result.returncode,0,result.stderr)
            with Image.open(output/'card-01.png') as image:
                self.assertEqual(image.size,(1080,1080)); self.assertIn('SCM-Draft-SHA256',image.info)
            self.assertEqual(json.loads((output/'draft-01.json').read_text(encoding='utf-8')),draft)
            page=(output/'index.html').read_text(encoding='utf-8'); self.assertNotIn('<script>',page); self.assertIn('&lt;script&gt;',page)
            self.assertNotEqual(run().returncode,0)
    def test_approved_or_commentary_cannot_enter_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch=Path(tmp)/'batch.json'; batch.write_text(json.dumps({'version':1,'drafts':[{'version':1,'title':'Склад','ready_for_review':True,'comment':'x'}]}),encoding='utf-8')
            output=Path(tmp)/'gallery'; result=subprocess.run([sys.executable,str(SCRIPT),str(batch),str(output)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0); self.assertFalse(output.exists())

if __name__ == '__main__': unittest.main()
