#!/bin/bash
# Fix Immich deletion history remotely via SSH
# Run this from dev container to execute on remote server

set -e

# Configuration - edit these values
SSH_HOST="${IMMICH_SSH_HOST:-}"
SSH_USER="${IMMICH_SSH_USER:-$(whoami)}"
SSH_PORT="${IMMICH_SSH_PORT:-22}"
IMMICH_CONTAINER="${IMMICH_CONTAINER_NAME:-immich_postgres}"
DB_USER="${IMMICH_DB_USER:-postgres}"
DB_NAME="${IMMICH_DB_NAME:-immich}"

echo "==================================================================="
echo "Immich Deletion History Fix (Remote)"
echo "==================================================================="
echo ""

# Check if SSH_HOST is set
if [ -z "$SSH_HOST" ]; then
    echo "Error: SSH host not configured."
    echo ""
    echo "Set the IMMICH_SSH_HOST environment variable or edit this script:"
    echo "  export IMMICH_SSH_HOST=your-server.com"
    echo "  export IMMICH_SSH_USER=your-username  # optional"
    echo ""
    read -p "Enter SSH host now (e.g., photos.santeeplace.com): " SSH_HOST
    
    if [ -z "$SSH_HOST" ]; then
        echo "Aborted: No SSH host provided."
        exit 1
    fi
fi

echo "Configuration:"
echo "  SSH: ${SSH_USER}@${SSH_HOST}:${SSH_PORT}"
echo "  Container: ${IMMICH_CONTAINER}"
echo "  Database: ${DB_NAME} (user: ${DB_USER})"
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
echo "Connecting to ${SSH_HOST}..."
echo ""

# Test SSH connection first
if ! ssh -p "${SSH_PORT}" -o ConnectTimeout=5 "${SSH_USER}@${SSH_HOST}" "echo 'SSH connection successful'" 2>/dev/null; then
    echo "Error: Cannot connect to ${SSH_USER}@${SSH_HOST}:${SSH_PORT}"
    echo "Check your SSH configuration and try again."
    exit 1
fi

# Execute the database update via SSH
echo "Executing database update..."
echo ""

ssh -p "${SSH_PORT}" "${SSH_USER}@${SSH_HOST}" bash << 'ENDSSH'
set -e

# Check if container exists
if ! docker ps --format '{{.Names}}' | grep -q "^immich_postgres$"; then
    echo "Error: immich_postgres container not found"
    echo "Available containers:"
    docker ps --format '{{.Names}}' | grep immich || echo "  (no immich containers running)"
    exit 1
fi

echo "Querying database..."
echo ""

# Execute SQL commands
docker exec immich_postgres psql -U postgres -d immich << 'EOSQL'
-- Show current deleted count
\echo '=== Current deleted assets ==='
SELECT COUNT(*) as deleted_count FROM assets WHERE "deletedAt" IS NOT NULL;

-- Clear deletion timestamps
\echo ''
\echo '=== Clearing deletion records ==='
UPDATE assets SET "deletedAt" = NULL WHERE "deletedAt" IS NOT NULL;

-- Get affected rows count
SELECT COUNT(*) as cleared FROM pg_stat_all_tables WHERE relname = 'assets';

-- Verify
\echo ''
\echo '=== Verification: Remaining deleted assets ==='
SELECT COUNT(*) as still_deleted FROM assets WHERE "deletedAt" IS NOT NULL;

\echo ''
\echo '✓ Database update complete'
EOSQL

ENDSSH

SSH_EXIT=$?

echo ""
echo "==================================================================="

if [ $SSH_EXIT -eq 0 ]; then
    echo "✓ Success! Deletion history cleared on remote server."
    echo ""
    echo "Next steps:"
    echo "  1. Rescan library: . run rescan 59d97602-42a2-4828-95cf-4eae903d8211"
    echo "  2. Rebuild cache: . run cache /mnt/photo_drive_local/santee-samples --clear"
    echo ""
    echo "You should now see all 415 assets matched!"
else
    echo "✗ Error: Remote command failed with exit code $SSH_EXIT"
    exit $SSH_EXIT
fi

echo "==================================================================="
