#!/usr/bin/env python3
"""
Delete unmatched assets from Immich library.

This script reads a cache file (created by cache.py) and deletes assets from
Immich that could not be matched to files in the target directory. This is useful
for cleaning up Immich after files have been renamed or reorganized on disk.

WARNING: This permanently deletes assets from Immich. Use --dry-run first!
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

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
from immich_cache import ImmichCache


SCRIPT_INFO = {
    'name': 'Delete Unmatched',
    'description': 'Delete unmatched assets from Immich library',
    'examples': [
        '.log/cache_santee-samples.json',
        '--input cache.json --dry-run',
        'cache.json --force --verbose'
    ]
}

SCRIPT_ARGUMENTS = {
    'input': {
        'flag': '--input',
        'positional': True,
        'required': True,
        'help': 'Path to cache file (created by cache.py)'
    },
    'force': {
        'flag': '--force',
        'action': 'store_true',
        'help': 'Permanently delete (skip trash). Default: move to trash'
    }
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


class AssetDeleter:
    """Handles deletion of Immich assets."""
    
    def __init__(self, connection: ImmichConnection, dry_run: bool = False, logger=None):
        """
        Initialize asset deleter.
        
        Args:
            connection: ImmichConnection instance
            dry_run: If True, simulate deletions without actually deleting
            logger: Logger instance
        """
        self.connection = connection
        self.dry_run = dry_run
        self.logger = logger
    
    def delete_assets(self, asset_ids: List[str], force: bool = False) -> Dict[str, int]:
        """
        Delete assets from Immich.
        
        Args:
            asset_ids: List of asset IDs to delete
            force: If True, permanently delete (bypass trash)
            
        Returns:
            Dictionary with deletion statistics
        """
        if not asset_ids:
            return {'deleted': 0, 'failed': 0}
        
        deleted = 0
        failed = 0
        
        # Process in batches of 100
        batch_size = 100
        for i in range(0, len(asset_ids), batch_size):
            batch = asset_ids[i:i + batch_size]
            
            if self.dry_run:
                if self.logger:
                    self.logger.info(
                        f"[DRY RUN] Would delete {len(batch)} assets "
                        f"(force={force}): {batch[:3]}..."
                    )
                deleted += len(batch)
                continue
            
            try:
                # Delete assets via API
                success = self.connection.delete_assets(batch, force=force)
                if success:
                    deleted += len(batch)
                    if self.logger:
                        action = "Permanently deleted" if force else "Moved to trash"
                        self.logger.info(f"{action} {len(batch)} assets")
                else:
                    failed += len(batch)
                    if self.logger:
                        self.logger.warning(f"Failed to delete batch of {len(batch)} assets")
            except Exception as e:
                failed += len(batch)
                if self.logger:
                    self.logger.error(f"Error deleting batch: {e}")
        
        return {'deleted': deleted, 'failed': failed}


def main():
    """Main entry point."""
    
    # Create argument parser
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    
    # Print standardized header
    parser.print_header()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate and resolve required arguments
    resolved_args = parser.validate_required_args(args, {
        'input': ['input', 'cache_file']
    })
    
    # Setup logging
    logger = parser.setup_logging(resolved_args, "delete_unmatched")
    
    # Display configuration
    parser.display_configuration(resolved_args)
    
    try:
        # Validate cache file exists
        cache_file = Path(resolved_args['input'])
        if not cache_file.exists():
            raise FileNotFoundError(f"Cache file not found: {cache_file}")
        
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
        
        # Load cache
        logger.info(f"Loading cache from {cache_file}...")
        cache = ImmichCache(str(cache_file), logger)
        cache.load()
        
        # Get cache statistics
        stats = cache.get_stats()
        logger.info(f"Cache contains {stats['total_assets']} total assets")
        logger.info(f"Matched files: {stats['matched_files']}")
        logger.info(f"Unmatched: {stats['unmatched_files']}")
        
        # Find unmatched assets
        unmatched_ids = []
        for asset_id, asset_data in cache.assets.items():
            file_mapping = asset_data.get('file_mapping', {})
            if file_mapping.get('match_confidence') == 'none':
                unmatched_ids.append(asset_id)
        
        if not unmatched_ids:
            logger.info("No unmatched assets found in cache")
            if not resolved_args.get('quiet'):
                print("✅ No unmatched assets to delete")
            return
        
        logger.info(f"Found {len(unmatched_ids)} unmatched assets to delete")
        
        # Log sample of assets to be deleted
        for i, asset_id in enumerate(unmatched_ids[:5]):
            asset = cache.get_asset(asset_id)
            filename = asset.get('immich_data', {}).get('originalFileName', 'unknown')
            logger.audit(f"  {i+1}. {filename} (ID: {asset_id})")
        
        if len(unmatched_ids) > 5:
            logger.audit(f"  ... and {len(unmatched_ids) - 5} more")
        
        # Confirm deletion if not in dry-run mode
        if not resolved_args.get('dry_run'):
            force = resolved_args.get('force', False)
            action = "permanently delete" if force else "move to trash"
            logger.warning(f"About to {action} {len(unmatched_ids)} assets from Immich")
            
            response = input(f"\nProceed with deletion? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("Deletion cancelled by user")
                print("❌ Deletion cancelled")
                return
        
        # Delete assets
        logger.info("Deleting unmatched assets...")
        deleter = AssetDeleter(connection, resolved_args.get('dry_run', False), logger)
        results = deleter.delete_assets(unmatched_ids, resolved_args.get('force', False))
        
        # Report results
        logger.info(
            f"Deletion complete: {results['deleted']} deleted, {results['failed']} failed"
        )
        
        if not resolved_args.get('quiet'):
            if resolved_args.get('dry_run'):
                print(f"✅ [DRY RUN] Would delete {results['deleted']} assets")
            else:
                action = "Permanently deleted" if resolved_args.get('force') else "Moved to trash"
                print(f"✅ {action} {results['deleted']} assets")
                if results['failed'] > 0:
                    print(f"⚠️  {results['failed']} assets failed to delete")
        
    except Exception as e:
        logger.error(f"Error during deletion: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
