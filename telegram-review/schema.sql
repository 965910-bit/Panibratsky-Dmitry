-- Never drop or reset the journal during deployment.
CREATE TABLE IF NOT EXISTS drafts (
  id TEXT PRIMARY KEY,
  source_url TEXT NOT NULL UNIQUE,
  text TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('notifying', 'ready', 'rejected', 'sending', 'sent')),
  created_at TEXT NOT NULL,
  review_message_id INTEGER,
  channel_message_id INTEGER
);
