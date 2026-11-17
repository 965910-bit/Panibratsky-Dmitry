import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'telegram-review'


class TelegramSchemaTests(unittest.TestCase):
    def test_new_schema_and_existing_database_migration_preserve_records(self):
        new = sqlite3.connect(':memory:')
        new.executescript((ROOT / 'schema.sql').read_text())
        self.assertIn('photo_file_id', {row[1] for row in new.execute('PRAGMA table_info(drafts)')})
        new.execute("INSERT INTO drafts (id, source_url, text, state, created_at) VALUES (?, ?, ?, ?, ?)", ('id', 'https://example.org', 'text', 'notifying', '2026-11-16T00:00:00.000Z'))
        self.assertEqual(new.execute("SELECT state, COUNT(*) AS count FROM drafts GROUP BY state").fetchall(), [('notifying', 1)])
        info = new.execute('SELECT state, created_at, text, source_url, review_message_id, channel_message_id FROM drafts WHERE id = ?', ('id',)).fetchone()
        self.assertEqual(info, ('notifying', '2026-11-16T00:00:00.000Z', 'text', 'https://example.org', None, None))
        self.assertEqual(new.execute("SELECT id, state, created_at FROM drafts WHERE state IN ('notifying', 'sending') ORDER BY created_at ASC LIMIT 5").fetchone()[0], 'id')
        old = sqlite3.connect(':memory:')
        old.executescript("""CREATE TABLE drafts (id TEXT PRIMARY KEY, source_url TEXT NOT NULL UNIQUE,
            text TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL,
            review_message_id INTEGER, channel_message_id INTEGER);
            INSERT INTO drafts VALUES ('id', 'https://example.org', 'text', 'sent', 'date', 1, 2);""")
        old.executescript((ROOT / 'migrations/001-add-photo.sql').read_text())
        self.assertEqual(old.execute('SELECT state, channel_message_id, photo_file_id FROM drafts').fetchone(), ('sent', 2, None))
        with self.assertRaises(sqlite3.OperationalError):
            old.executescript((ROOT / 'migrations/001-add-photo.sql').read_text())


if __name__ == '__main__':
    unittest.main()
