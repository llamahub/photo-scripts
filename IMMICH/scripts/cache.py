#!/usr/bin/env python3
"""
Extract metadata from Immich into a cache and map it to files in target folder.

This script extracts description, tags, and other metadata from Immich assets
and caches them with file path mappings. It does NOT modify any files - just
builds a searchable cache for later use.
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime

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
from file_matcher import FileMatcher


SCRIPT_INFO = {
    'name': 'Cache',
    'description': 'Extract metadata from Immich and cache with file mappings',
    'examples': [
        '/mnt/photos',
        '--target /mnt/photos --after 2025-10-24T16:00:00Z',
        '/mnt/photos --album album_id_here',
        '--target /mnt/photos --cache ./custom_cache.json --clear',
        '/mnt/photos --before 2025-12-31T23:59:59Z --verbose'
    ]
}

SCRIPT_ARGUMENTS = {
    'target': {
        'flag': '--target',
        'positional': True,
        'required': True,
        'help': 'Root directory of library to search for files matching asset filepaths'
    },
    'cache': {
        'flag': '--cache',
        'help': 'Path to metadata cache file (default: .log/cache_{target_basename}.json)'
    },
    'clear': {
        'flag': '--clear',
        'action': 'store_true',
        'help': 'Clear cache before extracting (default: add/update cache with new metadata)'
    },
    'before': {
        'flag': '--before',
        'help': 'Only extract assets modified before ISO date/time (e.g., 2025-06-30T00:00:00Z)'
    },
    'after': {
        'flag': '--after',
        'help': 'Only extract assets modified after ISO date/time (e.g., 2025-06-30T00:00:00Z)'
    },
    'album': {
        'flag': '--album',
        'help': 'Only extract assets from this album ID'
    }
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def validate_iso8601_date(date_str: str, arg_name: str, parser: ScriptArgumentParser) -> bool:
    """
    Validate ISO 8601 date format.
    
    Args:
        date_str: Date string to validate
        arg_name: Argument name for error messages
        parser: Parser instance for error reporting
        
    Returns:
        True if valid, raises error otherwise
    """
    if not date_str:
        return True
    
    # Pattern for full ISO 8601 with time
    iso8601_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})?$")
    
    if not iso8601_pattern.match(date_str):
        parser.error(
            f"Invalid value for {arg_name}: '{date_str}'. "
            f"Must be full ISO 8601 format (e.g., 2025-06-30T00:00:00Z)"
        )
    
    # Try parsing to catch impossible dates
    try:
        # Use datetime.fromisoformat for proper ISO 8601 parsing
        # Handle 'Z' suffix (fromisoformat doesn't support it until Python 3.11)
        test_date = date_str.replace("Z", "+00:00")
        datetime.fromisoformat(test_date)
    except (ValueError, IndexError) as e:
        parser.error(
            f"Invalid value for {arg_name}: '{date_str}'. Date/time is not valid."
        )
    
    return True


def main():
    """Main entry point."""
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()
    
    args = parser.parse_args()
    
    # Validate required arguments
    resolved_args = parser.validate_required_args(args, {
        'target': ['target']
    })
    
    # Validate ISO 8601 dates
    validate_iso8601_date(resolved_args.get('before'), '--before', parser)
    validate_iso8601_date(resolved_args.get('after'), '--after', parser)
    
    # Validate target directory exists
    target_path = Path(resolved_args['target'])
    if not target_path.exists():
        parser.error(f"Target directory does not exist: {target_path}")
    
    # Determine cache path
    cache_path = resolved_args.get('cache')
    if not cache_path:
        target_basename = target_path.name or "root"
        cache_path = f".log/cache_{target_basename}.json"
    
    resolved_args['cache'] = cache_path
    
    # Setup logging
    logger = parser.setup_logging(resolved_args, "cache")
    
    # Load Immich configuration
    config = None
    try:
        config = ImmichConfig(_env_file=project_root / ".env", _env_file_encoding="utf-8")
    except Exception:
        try:
            config = ImmichConfig(_env_file=Path.cwd() / ".env", _env_file_encoding="utf-8")
        except Exception:
            config = ImmichConfig()
    
    env_url = os.environ.get("IMMICH_URL")
    env_api_key = os.environ.get("IMMICH_API_KEY")
    url = env_url or getattr(config, 'immich_url', None)
    api_key = env_api_key or getattr(config, 'immich_api_key', None)
    
    if not url or not api_key:
        parser.error(
            "Immich URL and API key must be provided via "
            "IMMICH_URL/IMMICH_API_KEY environment variables or .env file"
        )
    
    # Display configuration
    if not resolved_args.get("quiet"):
        logger.info("Configuration:")
        logger.info(f"  Target directory: {target_path}")
        logger.info(f"  Cache file: {cache_path}")
        logger.info(f"  Clear cache: {resolved_args.get('clear', False)}")
        if resolved_args.get('before'):
            logger.info(f"  Before: {resolved_args['before']}")
        if resolved_args.get('after'):
            logger.info(f"  After: {resolved_args['after']}")
        if resolved_args.get('album'):
            logger.info(f"  Album: {resolved_args['album']}")
        logger.info(f"  Immich URL: {url}")
        logger.info("")
    
    try:
        # Initialize components
        logger.info("Initializing Immich connection...")
        connection = ImmichConnection(url, api_key, logger)
        
        # Validate connection
        if not connection.validate_connection():
            logger.error("Failed to connect to Immich server")
            print("❌ Failed to connect to Immich server")
            return 1
        
        logger.info("✓ Connected to Immich server")
        
        # Initialize cache
        cache = ImmichCache(cache_path, logger)
        
        # Load or clear cache
        if resolved_args.get('clear'):
            logger.info("Clearing cache...")
            cache.clear()
            cache.metadata['created'] = datetime.now().isoformat() + "Z"
        else:
            logger.info("Loading existing cache...")
            cache.load()
            if not cache.metadata.get('created'):
                cache.metadata['created'] = datetime.now().isoformat() + "Z"
        
        cache.metadata['target_path'] = str(target_path)
        
        # Search for assets
        logger.info("Fetching assets from Immich...")
        assets = connection.search_assets(
            updated_before=resolved_args.get('before'),
            updated_after=resolved_args.get('after'),
            album_id=resolved_args.get('album')
        )
        
        logger.info(f"Found {len(assets)} assets")
        
        # Initialize file matcher
        logger.info("Building file index...")
        matcher = FileMatcher(str(target_path), logger)
        
        # Process each asset
        logger.info("Processing assets and matching files...")
        stats = {
            'exact_matches': 0,
            'fuzzy_matches': 0,
            'no_matches': 0,
            'skipped_older': 0
        }
        
        for i, asset in enumerate(assets, 1):
            asset_id = asset.get('id', 'unknown')
            filename = asset.get('originalFileName', 'unknown')
            
            # Match file
            matched_path, confidence, method = matcher.match_asset(asset)
            
            # Determine AUDIT status
            if confidence == "exact":
                status = "matched_exact"
                stats['exact_matches'] += 1
            elif confidence == "fuzzy":
                status = "matched_fuzzy"
                stats['fuzzy_matches'] += 1
            else:
                status = method  # Will be like "no_file_found", "ambiguous_3_files", etc.
                stats['no_matches'] += 1
            
            # Add to cache (will check if update needed)
            original_count = len(cache.assets)
            cache.add_asset(asset, matched_path, confidence, method)
            
            # Check if asset was actually added/updated
            if len(cache.assets) == original_count and asset_id in cache.assets:
                # Asset existed and wasn't updated (older data)
                status = "skipped_older"
                stats['skipped_older'] += 1
            
            # AUDIT log
            logger.log(
                15,  # AUDIT level
                f"Asset {i}/{len(assets)}: {filename} -> {status} -> {matched_path or 'none'}"
            )
            
            # Progress logging
            if i % 100 == 0:
                logger.info(f"Processed {i}/{len(assets)} assets...")
        
        # Save cache
        logger.info("Saving cache...")
        cache.save()
        
        # Display summary
        cache_stats = cache.get_stats()
        
        logger.info("\n" + "="*50)
        logger.info("SUMMARY")
        logger.info("="*50)
        logger.info(f"Total assets processed: {len(assets)}")
        logger.info(f"Exact matches: {stats['exact_matches']}")
        logger.info(f"Fuzzy matches: {stats['fuzzy_matches']}")
        logger.info(f"No matches: {stats['no_matches']}")
        logger.info(f"Skipped (older data): {stats['skipped_older']}")
        logger.info(f"\nCache statistics:")
        logger.info(f"  Total cached assets: {cache_stats['total_assets']}")
        logger.info(f"  Matched files: {cache_stats['matched_files']}")
        logger.info(f"  Unmatched: {cache_stats['unmatched_files']}")
        logger.info(f"  Unique filenames: {cache_stats['unique_filenames']}")
        logger.info(f"  Albums tracked: {cache_stats['albums']}")
        logger.info(f"  Tags tracked: {cache_stats['tags']}")
        logger.info(f"\nCache saved to: {cache_path}")
        
        if not resolved_args.get('quiet'):
            print(f"✅ Cache updated successfully: {cache_path}")
            print(f"   {cache_stats['total_assets']} assets, "
                  f"{cache_stats['matched_files']} matched files")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
