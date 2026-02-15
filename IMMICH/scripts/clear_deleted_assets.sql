-- Query to find and restore deleted assets
-- Run this on the Immich PostgreSQL database

-- First, check how many deleted assets exist
SELECT COUNT(*) as deleted_count 
FROM assets 
WHERE "deletedAt" IS NOT NULL;

-- View sample of deleted assets
SELECT id, "originalFileName", checksum, "deletedAt" 
FROM assets 
WHERE "deletedAt" IS NOT NULL 
LIMIT 10;

-- Clear the deletedAt timestamp to restore them
-- This allows Immich to re-import files with the same checksum
UPDATE assets 
SET "deletedAt" = NULL 
WHERE "deletedAt" IS NOT NULL;

-- Verify they're cleared
SELECT COUNT(*) as still_deleted 
FROM assets 
WHERE "deletedAt" IS NOT NULL;
