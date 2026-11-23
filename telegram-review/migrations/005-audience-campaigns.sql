-- Staged only; apply after 003 and 004, and never against live D1 without backup.
CREATE TABLE IF NOT EXISTS audience_campaigns (
  draft_id TEXT PRIMARY KEY REFERENCES drafts(id),
  created_at TEXT NOT NULL
);
