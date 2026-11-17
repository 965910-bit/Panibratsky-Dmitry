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
    def test_empty_gallery_explains_no_candidates_without_creating_drafts(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch=Path(tmp)/'batch.json'; batch.write_text(json.dumps({'version':1,'drafts':[]}),encoding='utf-8')
            output=Path(tmp)/'gallery'; result=subprocess.run([sys.executable,str(SCRIPT),str(batch),str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('Подходящих кандидатов не найдено', (output/'index.html').read_text(encoding='utf-8'))
            self.assertEqual([p.name for p in output.iterdir()], ['index.html'])
            self.assertIn('Создано карточек: 0',result.stdout)

    def test_duplicate_hints_are_advisory_symmetric_and_preserve_all_drafts(self):
        base = {'version':1, 'source_name':'Источник', 'description':'Текст', 'comment':'', 'ready_for_review':False}
        drafts = [
            {**base, 'title':'Как устроить надёжные складские процессы', 'source_url':'https://example.org/story?id=1&utm_source=news'},
            {**base, 'title':'КАК УСТРОИТЬ НАДЁЖНЫЕ СКЛАДСКИЕ ПРОЦЕССЫ!', 'source_url':'https://other.example/story'},
            {**base, 'title':'Совсем другой проверяемый заголовок', 'source_url':'https://example.org/story?id=1#section'},
            {**base, 'title':'Отдельная новость про управление запасами', 'source_url':'https://example.org/story?id=2&utm_source=news'},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            batch=Path(tmp)/'batch.json'; batch.write_text(json.dumps({'version':1,'drafts':drafts},ensure_ascii=False),encoding='utf-8')
            output=Path(tmp)/'gallery'; result=subprocess.run([sys.executable,str(SCRIPT),str(batch),str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            page=(output/'index.html').read_text(encoding='utf-8')
            self.assertEqual(page.count('Возможный повтор:'), 3)
            self.assertIn('сравните с №02, №03',page)
            self.assertIn('сравните с №01',page)
            self.assertIn('№04 ·',page)
            for i, draft in enumerate(drafts, 1):
                self.assertEqual(json.loads((output/f'draft-{i:02}.json').read_text(encoding='utf-8')),draft)
                self.assertTrue((output/f'card-{i:02}.png').exists())

    def test_matching_helpers_do_not_guess_short_titles_or_unrelated_urls(self):
        sys.path.insert(0,str(ROOT/'telegram-review'))
        try:
            from cards_batch import possible_duplicates, source_key
            items=[{'title':'Склад','source_url':'https://example.org/?p=1'},
                   {'title':'СКЛАД!','source_url':'https://example.org/?p=2'},
                   {'title':'','source_url':'javascript:alert(1)'},
                   {'title':'','source_url':'https://example.org/?p=1&gclid=123'}]
            self.assertEqual(possible_duplicates(items),[[4],[],[],[1]])
            self.assertIsNone(source_key('https://user:pass@example.org/article'))
            self.assertIsNone(source_key('https://[broken'))
        finally:
            sys.path.pop(0)

    def test_approved_or_commentary_cannot_enter_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch=Path(tmp)/'batch.json'; batch.write_text(json.dumps({'version':1,'drafts':[{'version':1,'title':'Склад','ready_for_review':True,'comment':'x'}]}),encoding='utf-8')
            output=Path(tmp)/'gallery'; result=subprocess.run([sys.executable,str(SCRIPT),str(batch),str(output)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0); self.assertFalse(output.exists())

if __name__ == '__main__': unittest.main()
