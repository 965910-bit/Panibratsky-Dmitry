-- Staged only: never apply to a live database before backup and integration tests.
-- Opt-in is explicit and revocable; do not store names, handles, or message text.
CREATE TABLE IF NOT EXISTS audience_subscribers (
  chat_id TEXT PRIMARY KEY,
  subscribed_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  active INTEGER NOT NULL CHECK (active IN (0, 1))
);
-- Destinations must be configured explicitly after access and admin rights are verified.
CREATE TABLE IF NOT EXISTS audience_destinations (
  chat_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('channel', 'group')),
  enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
  created_at TEXT NOT NULL
);
-- One attempt per recipient and approved draft; uncertain sends are never automatically retried.
CREATE TABLE IF NOT EXISTS audience_deliveries (
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  recipient_type TEXT NOT NULL CHECK (recipient_type IN ('subscriber', 'destination')),
  recipient_id TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending', 'sending', 'sent', 'failed', 'uncertain', 'cancelled')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  message_id INTEGER,
  PRIMARY KEY (draft_id, recipient_type, recipient_id)
);
CREATE INDEX IF NOT EXISTS audience_delivery_state_idx ON audience_deliveries (state, created_at);
