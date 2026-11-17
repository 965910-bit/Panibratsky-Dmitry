import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    import PIL
except ImportError:
    PIL = None

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / 'telegram-review' / 'card.py'


@unittest.skipIf(PIL is None, 'Pillow is an optional dependency for offline cards')
class TelegramCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('telegram_card', CARD)
        cls.card = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.card)

    def test_card_png_dimensions_and_no_network(self):
        with tempfile.TemporaryDirectory() as d:
            draft = Path(d) / 'draft.json'
            out = Path(d) / 'card.png'
            draft.write_text(json.dumps({'version': 1, 'title': 'Как подготовить склад к WMS', 'source_name': 'Пример'}), encoding='utf-8')
            proc = subprocess.run([sys.executable, str(CARD), str(draft), str(out)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with PIL.Image.open(out) as image:
                self.assertEqual(image.format, 'PNG')
                self.assertEqual(image.size, (1080, 1080))
            # Existing images are never overwritten.
            original = out.read_bytes()
            second = subprocess.run([sys.executable, str(CARD), str(draft), str(out)], capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(out.read_bytes(), original)

    def test_png_metadata_matches_js_client_and_rejects_changed_draft(self):
        with tempfile.TemporaryDirectory() as d:
            draft_path, png_path = Path(d) / 'draft.json', Path(d) / 'card.png'
            draft = {'version': 1, 'title': 'Склад 📦 и WMS', 'source_name': 'Источник', 'source_url': 'https://example.org/a', 'description': '', 'comment': 'Проверено', 'ready_for_review': True}
            draft_path.write_text(json.dumps(draft, ensure_ascii=False), encoding='utf-8')
            proc = subprocess.run([sys.executable, str(CARD), str(draft_path), str(png_path)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with PIL.Image.open(png_path) as image:
                self.assertEqual(image.info['SCM-Draft-SHA256'], self.card.draft_fingerprint(draft))
            js = """import {readFileSync} from 'node:fs'; import {buildPayload,attachCard} from './telegram-review/drafts.mjs';
                const d=JSON.parse(readFileSync(process.argv[1],'utf8')); const p=readFileSync(process.argv[2]);
                attachCard(buildPayload(d),p,d); let rejected=false;
                try { attachCard(buildPayload(d),p,{...d,title:'Изменённый заголовок'}); } catch { rejected=true; }
                if (!rejected) process.exit(2);"""
            check = subprocess.run(['node', '--input-type=module', '-e', js, str(draft_path), str(png_path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_wrapping_handles_long_unbroken_strings_and_marks_truncation(self):
        from PIL import Image, ImageDraw, ImageFont
        draw = ImageDraw.Draw(Image.new('RGB', (1080, 1080)))
        font = ImageFont.truetype(self.card.FONT_BOLD, 57)
        lines = self.card.wrap_title(draw, 'Склад' * 100, font, 855, 7)
        self.assertEqual(len(lines), 7)
        self.assertTrue(lines[-1].endswith('…'))
        self.assertTrue(all(draw.textlength(line, font=font) <= 855 for line in lines))

    def test_invalid_drafts_are_rejected_and_control_chars_removed(self):
        self.assertEqual(self.card.clean('склад\u202eновость\nтекст'), 'склад новость текст')
        with self.assertRaises(ValueError):
            self.card.make_card({'version': 1, 'title': '  '})
        with self.assertRaises(ValueError):
            self.card.make_card({'version': 2, 'title': 'заголовок'})


if __name__ == '__main__':
    unittest.main()
