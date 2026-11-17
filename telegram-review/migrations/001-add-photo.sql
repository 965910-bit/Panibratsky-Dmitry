-- Apply exactly once to an existing pre-photo schema, after a backup.
-- For new databases use schema.sql only; do not also apply this migration.
ALTER TABLE drafts ADD COLUMN photo_file_id TEXT;
