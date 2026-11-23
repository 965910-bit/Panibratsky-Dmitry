-- Apply only after migration 003 in an isolated, backed-up database.
-- Ordering prevents stale/retried subscription updates from undoing newer choices.
ALTER TABLE audience_subscribers ADD COLUMN last_update_id INTEGER NOT NULL DEFAULT -1;
