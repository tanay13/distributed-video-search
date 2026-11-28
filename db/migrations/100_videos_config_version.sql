-- Tanay. Which indexing settings (models, sampling) a video was indexed with; from indexing.config_version().
ALTER TABLE videos ADD COLUMN IF NOT EXISTS config_version TEXT;
