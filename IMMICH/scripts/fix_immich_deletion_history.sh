#!/bin/bash
# Fix Immich deletion history to allow re-import of renamed files
# This script clears the deletedAt timestamp from deleted assets

set -e

echo "==================================================================="
echo "Immich Deletion History Fix"
echo "==================================================================="
echo ""
echo "This will clear deletion records from Immich's database,"
echo "allowing previously deleted files to be re-imported."
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Connecting to Immich PostgreSQL database..."
echo ""

# Execute SQL to clear deletion records
docker exec -i immich_postgres psql -U ${DB_USERNAME:-postgres} -d ${DB_DATABASE_NAME:-immich} << 'EOF'
-- Show current deleted count
\echo 'Current deleted assets:'
SELECT COUNT(*) as deleted_count FROM assets WHERE "deletedAt" IS NOT NULL;

-- Clear deletion timestamps
\echo ''
\echo 'Clearing deletion records...'
UPDATE assets SET "deletedAt" = NULL WHERE "deletedAt" IS NOT NULL;

-- Verify
\echo ''
\echo 'Remaining deleted assets:'
SELECT COUNT(*) as still_deleted FROM assets WHERE "deletedAt" IS NOT NULL;

\echo ''
\echo 'Done! Run a library scan to re-import files.'
EOF

echo ""
echo "==================================================================="
echo "Success! Deletion history cleared."
echo ""
echo "Next steps:"
echo "1. Run library rescan: . run rescan <library-id>"
echo "2. Rebuild cache: . run cache /mnt/photo_drive_local/santee-samples --clear"
echo "==================================================================="
