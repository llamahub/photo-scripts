#!/usr/bin/env python3
"""
Fix deletion history in Immich database.

Clears the deletedAt timestamp from deleted assets in Immich's PostgreSQL database,
allowing previously deleted files to be re-imported during library scans. This is
useful when files have been renamed on disk and you want Immich to re-import them
with the new filenames, even though the file content (checksum) hasn't changed.

Requires SSH access to the Immich server and uses Docker to execute SQL commands
on the immich_postgres container.
"""

import os
import sys
from pathlib import Path

# Add project src and COMMON to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root.parent / "COMMON" / "src"))

from common.logging import ScriptLogging
from common.argument_parser import (
    ScriptArgumentParser,
    create_standard_arguments,
    merge_arguments,
)
from immich_config import ImmichConfig
from immich_database import ImmichDatabase


SCRIPT_INFO = {
    'name': 'Fix Deleted',
    'description': 'Clear Immich deletion history to allow re-import of renamed files',
    'examples': [
        '',
        '--dry-run',
        '--verbose'
    ]
}

SCRIPT_ARGUMENTS = {
    # No additional arguments needed - uses config from .env
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def main():
    """Main entry point."""
    
    # Create argument parser
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    
    # Print standardized header
    parser.print_header()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    logger = parser.setup_logging(vars(args), "fix_deleted")
    
    # Display configuration
    parser.display_configuration(vars(args))
    
    try:
        # Load configuration
        logger.info("Loading Immich configuration...")
        config = ImmichConfig()
        
        # Validate SSH configuration
        if not config.immich_ssh_host:
            logger.error("IMMICH_SSH_HOST not configured in .env")
            if not args.quiet:
                print("❌ Error: IMMICH_SSH_HOST not set")
                print("   Add to .env: IMMICH_SSH_HOST=your-server.com")
            return 1
        
        if not config.immich_ssh_user:
            logger.error("IMMICH_SSH_USER not configured in .env")
            if not args.quiet:
                print("❌ Error: IMMICH_SSH_USER not set")
                print("   Add to .env: IMMICH_SSH_USER=your-username")
            return 1
        
        # Initialize database handler
        logger.info(f"Connecting to {config.immich_ssh_user}@{config.immich_ssh_host}:{config.immich_ssh_port}...")
        db = ImmichDatabase(
            ssh_host=config.immich_ssh_host,
            ssh_user=config.immich_ssh_user,
            ssh_port=config.immich_ssh_port,
            container_name=config.immich_db_container,
            db_user=config.immich_db_user,
            db_name=config.immich_db_name,
            logger=logger
        )
        
        # Test SSH connection
        if not db.test_ssh_connection():
            logger.error("Failed to connect via SSH")
            if not args.quiet:
                print(f"❌ Cannot connect to {config.immich_ssh_host}")
                print("   Check SSH configuration and network connectivity")
            return 1
        
        logger.info("✓ SSH connection successful")
        
        # Get current deleted count
        logger.info("Querying deleted assets...")
        deleted_count = db.get_deleted_count()
        
        if deleted_count is None:
            logger.error("Failed to query database")
            if not args.quiet:
                print("❌ Database query failed")
            return 1
        
        logger.info(f"Found {deleted_count} deleted assets in database")
        
        if deleted_count == 0:
            logger.info("No deleted assets to clear")
            if not args.quiet:
                print("✅ No deleted assets found - nothing to do")
            return 0
        
        # Show what will be cleared
        if not args.quiet:
            print(f"\n📊 Database Status:")
            print(f"   Deleted assets: {deleted_count}")
            print()
        
        # Dry run check
        if args.dry_run:
            logger.info(f"[DRY RUN] Would clear deletion records for {deleted_count} assets")
            if not args.quiet:
                print(f"✅ [DRY RUN] Would clear {deleted_count} deletion records")
                print()
                print("Next steps after clearing:")
                print("  1. Run library rescan")
                print("  2. Files will be re-imported with current filenames")
            return 0
        
        # Confirm action
        if not args.quiet:
            print(f"⚠️  This will clear deletion records for {deleted_count} assets")
            print("   allowing them to be re-imported during next library scan.")
            print()
            response = input("Continue? (y/n): ")
            if response.lower() not in ['y', 'yes']:
                print("Aborted.")
                return 0
            print()
        
        # Execute the clear operation
        logger.info("Clearing deletion records...")
        result = db.clear_deletion_records()
        
        if not result['success']:
            logger.error(f"Failed to clear deletion records: {result['error']}")
            if not args.quiet:
                print(f"❌ Error: {result['error']}")
            return 1
        
        logger.info(f"Successfully cleared {result['affected_rows']} deletion records")
        
        if not args.quiet:
            print(f"✅ Cleared {result['affected_rows']} deletion records")
            print()
            print("Next steps:")
            print(f"  1. Rescan library: . run rescan <library-id>")
            print(f"  2. Verify: . run cache <directory> --clear")
            print()
            print("Previously deleted files will now be re-imported with their current filenames.")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        if not args.quiet:
            print("\n⚠️  Cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Error during operation: {e}")
        if not args.quiet:
            print(f"❌ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
