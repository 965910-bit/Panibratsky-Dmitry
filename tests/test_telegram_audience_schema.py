import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class AudienceSchemaTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript((ROOT / 'telegram-review/schema.sql').read_text())
        self.db.executescript((ROOT / 'telegram-review/migrations/003-audience.sql').read_text())
        self.db.execute("INSERT INTO drafts(id,source_url,text,state,created_at) VALUES('draft','https://example.org/1','text','sent','now')")

    def tearDown(self):
        self.db.close()

    def test_target_disabled_by_default_and_one_delivery_per_recipient(self):
        self.db.execute("INSERT INTO audience_destinations(chat_id,kind,created_at) VALUES('-100','channel','now')")
        self.assertEqual(self.db.execute('SELECT enabled FROM audience_destinations').fetchone()[0], 0)
        sql = "INSERT INTO audience_deliveries(draft_id,recipient_type,recipient_id,state,created_at,updated_at) VALUES('draft','destination','-100','pending','now','now')"
        self.db.execute(sql)
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute(sql)

    def test_invalid_delivery_state_or_missing_draft_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO audience_deliveries VALUES('draft','subscriber','1','delivered','now','now',NULL)")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO audience_deliveries VALUES('missing','subscriber','1','pending','now','now',NULL)")

if __name__ == '__main__': unittest.main()
