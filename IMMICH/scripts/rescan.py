#!/usr/bin/env python3
"""
Trigger library re-scan in Immich.

This script triggers a library scan to re-import assets with current filenames
from disk. Useful after renaming files or deleting mismatched assets to refresh
Immich's database with the current state of the filesystem.
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
from immich_connection import ImmichConnection


SCRIPT_INFO = {
    'name': 'Rescan Library',
    'description': 'Trigger Immich library re-scan to import current filenames',
    'examples': [
        '--list-libraries',
        '59d97602-42a2-4828-95cf-4eae903d8211',
        '--library library_id_here',
        'library_id --verbose'
    ]
}

SCRIPT_ARGUMENTS = {
    'library': {
        'flag': '--library',
        'positional': True,
        'required': False,
        'help': 'Immich library ID to scan'
    },
    'list_libraries': {
        'flag': '--list-libraries',
        'action': 'store_true',
        'help': 'List all available libraries and their IDs'
    }
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
    logger = parser.setup_logging(vars(args), "rescan")
    
    # Display configuration
    parser.display_configuration(vars(args))
    
    try:
        # Load configuration
        logger.info("Loading Immich configuration...")
        config = ImmichConfig()
        
        # Initialize Immich connection
        logger.info("Connecting to Immich...")
        connection = ImmichConnection(config.immich_url, config.immich_api_key, logger)
        if not connection.validate_connection():
            logger.error("Failed to connect to Immich server")
            return 1
        logger.info("✓ Connected to Immich server")
        
        # List libraries if requested
        if args.list_libraries:
            logger.info("Fetching libraries...")
            libraries = connection.get_libraries()
            
            if not libraries:
                logger.warning("No libraries found")
                if not args.quiet:
                    print("⚠️  No libraries found")
                return 1
            
            logger.info(f"Found {len(libraries)} libraries")
            
            if not args.quiet:
                print(f"\n📚 Available Libraries ({len(libraries)}):\n")
                for lib in libraries:
                    lib_id = lib.get('id', 'unknown')
                    lib_name = lib.get('name', 'Unknown')
                    lib_type = lib.get('type', 'unknown')
                    asset_count = lib.get('assetCount', 0)
                    print(f"  • {lib_name}")
                    print(f"    ID: {lib_id}")
                    print(f"    Type: {lib_type}")
                    print(f"    Assets: {asset_count}")
                    print()
                print("Usage: rescan.py <library_id>")
            
            return 0
        
        # Get library ID - validate it's provided if not listing
        library_id = args.library
        if not library_id:
            logger.error("Library ID is required. Use --list-libraries to see available libraries.")
            if not args.quiet:
                print("❌ Error: Library ID is required")
                print("   Use: rescan.py --list-libraries")
            return 1
        
        # Trigger library scan
        logger.info(f"Triggering scan for library {library_id}...")
        
        if args.dry_run:
            logger.info(f"[DRY RUN] Would trigger scan for library {library_id}")
            if not args.quiet:
                print(f"✅ [DRY RUN] Would scan library {library_id}")
            return 0
        
        success = connection.scan_library(library_id)
        
        if success:
            logger.info(f"Library scan triggered successfully for {library_id}")
            if not args.quiet:
                print(f"✅ Library scan started for {library_id}")
                print("   Note: Scanning happens in background. Check Immich UI for progress.")
        else:
            logger.error(f"Failed to trigger library scan for {library_id}")
            if not args.quiet:
                print(f"❌ Failed to start library scan")
            return 1
        
    except Exception as e:
        logger.error(f"Error during library scan: {e}")
        if not args.quiet:
            print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
