-- Apply once to an existing journal only after backing up and inspecting it.
-- The two nullable columns preserve all prior records. Never run on a fresh
-- schema.sql database (it already contains them), or repeat this migration.
ALTER TABLE drafts ADD COLUMN resolution_kind TEXT CHECK (resolution_kind IS NULL OR resolution_kind IN ('confirmed_channel_message', 'abandoned_review'));
ALTER TABLE drafts ADD COLUMN resolved_at TEXT;
