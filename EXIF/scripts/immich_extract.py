
#!/usr/bin/env python3
"""
Immich Album Description and Tag Extractor/EXIF Updater

Extracts description and tags from Immich for all photos in a given album or search, and updates EXIF data accordingly.
"""

import sys
import os
from pathlib import Path

# Add COMMON to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))

try:
    from common.argument_parser import ScriptArgumentParser, create_standard_arguments, merge_arguments
    from common.logging import ScriptLogging
except ImportError:
    ScriptArgumentParser = None
    print("Warning: COMMON modules not available")

from exif.immich_extractor import ImmichExtractor

SCRIPT_INFO = {
    'name': 'immich_extract',
    'description': 'Extract description and tags from Immich for all photos in a given album or search, and update EXIF data.',
    'examples': [
        '--search --search-paths /mnt/photo_drive/santee-images --updatedAfter 2025-10-24T16:00 --dry-run',
        '--album <album_id> --search-paths /mnt/photo_drive/santee-images',
        '--search --search-paths /mnt/photo_drive/santee-images --dry-run'
    ]
}

SCRIPT_ARGUMENTS = {
    'search': {
        'flag': '--search',
        'action': 'store_true',
        'help': 'Use Immich search API instead of album (enables --updatedAfter)'
    },
    'album': {
        'flag': '--album',
        'help': 'Immich album ID'
    },
    'search_paths': {
        'flag': '--search-paths',
        'nargs': '+',
        'required': True,
        'help': 'Paths to search for image files'
    },
    'updated_after': {
        'flag': '--updatedAfter',
        'dest': 'updated_after',
        'help': 'Only process assets updated after this ISO date/time (e.g., 2025-06-30T00:00:00Z)'
    },
    'search_archive': {
        'flag': '--search-archive',
        'action': 'store_true',
        'help': 'Search for archived assets (Immich isArchived=true)'
    },
    'refresh_album_cache': {
        'flag': '--refresh-album-cache',
        'action': 'store_true',
        'help': 'Force refresh album cache from Immich'
    },
    'use_album_cache': {
        'flag': '--use-album-cache',
        'action': 'store_true',
        'help': 'Use local album cache if present (default: use cache if present, refresh if not)'
    },
    'log_file': {
        'flag': '--log-file',
        'help': 'Path to log file (default: .log/extract_<timestamp>.log)'
    },
    'force_update_fuzzy': {
        'flag': '--force-update-fuzzy',
        'action': 'store_true',
        'help': 'Force update files with fuzzy datetime matches'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)

def main():
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()

    args = parser.parse_args()

    # If --help is present, argparse will exit before this point, but for subprocess-based tests,
    # we add a defensive check to skip validation if only --help is present in sys.argv
    if '--help' in sys.argv or '-h' in sys.argv:
        return


    # Enforce that either --album or --search is provided, but not both
    has_album = getattr(args, 'album', None)
    has_search = getattr(args, 'search', False)
    if not (has_album or has_search):
        parser.error("You must specify either --album or --search.")
    if has_album and has_search:
        parser.error("You cannot specify both --album and --search.")

    # Validate and resolve required arguments
    # Only require search_paths for both modes
    resolved_args = parser.validate_required_args(args, {
        'search_paths': ['search_paths']
    })

    # Additional fast validation for --search mode: require --updatedAfter
    if has_search:
        updated_after = getattr(args, 'updated_after', None)
        if not updated_after:
            parser.error("Required arguments missing: updated_after (for --search mode)")

    # --- Load .env using common config ---
    from exif.immich_config import ImmichConfig
    import os
    from pathlib import Path
    project_path = Path(__file__).resolve().parent.parent
    config = None
    try:
        config = ImmichConfig(_env_file=project_path / ".env", _env_file_encoding="utf-8")
    except Exception:
        try:
            config = ImmichConfig(_env_file=Path.cwd() / ".env", _env_file_encoding="utf-8")
        except Exception:
            config = ImmichConfig()

    env_url = os.environ.get("IMMICH_URL")
    env_api_key = os.environ.get("IMMICH_API_KEY")
    url = getattr(resolved_args, 'url', None) or env_url or getattr(config, 'immich_url', None)
    api_key = getattr(resolved_args, 'api_key', None) or env_api_key or getattr(config, 'immich_api_key', None)
    if not url or not api_key:
        parser.error("Immich URL and API key must be provided via --url/--api-key, IMMICH_URL/IMMICH_API_KEY in .env, or ImmichConfig.")

    # Setup logging with consistent pattern
    logger = parser.setup_logging(resolved_args, "immich_extract")

    # Display configuration for audit
    config_map = {
        'search_paths': 'Paths to search for image files',
        'album': 'Immich album ID',
        'search': 'Use search API',
        'updated_after': 'Only process assets updated after this ISO date/time',
        'search_archive': 'Search for archived assets',
        'refresh_album_cache': 'Force refresh album cache',
        'use_album_cache': 'Use local album cache',
        'log_file': 'Log file',
        'force_update_fuzzy': 'Force update fuzzy datetime matches',
        'dry_run': 'Dry run',
        'verbose': 'Verbose',
        'quiet': 'Quiet'
    }
    # Log configuration instead of printing
    if not resolved_args.get("quiet"):
        for arg_key, display_label in config_map.items():
            value = resolved_args.get(arg_key)
            if value:
                logger.info(f"{display_label}: {value}")
        if resolved_args.get("dry_run"):
            logger.info("Mode: DRY RUN (simulation only)")
        logger.info("")

    # Call business logic, passing the logger instance
    extractor = ImmichExtractor(
        url=url,
        api_key=api_key,
        search_paths=resolved_args['search_paths'],
        album=resolved_args.get('album'),
        search=resolved_args.get('search', False),
        updated_after=resolved_args.get('updated_after'),
        search_archive=resolved_args.get('search_archive', False),
        refresh_album_cache=resolved_args.get('refresh_album_cache', False),
        use_album_cache=resolved_args.get('use_album_cache', False),
        dry_run=resolved_args.get('dry_run', False),
        force_update_fuzzy=resolved_args.get('force_update_fuzzy', False),
        logger=logger
    )
    result = extractor.run()
    # Log summary output instead of printing
    if result and isinstance(result, dict):
        logger.info("\n" + ("="*50))
        logger.info("SUMMARY")
        logger.info("="*50)
        logger.info(f"Total assets processed: {result.get('total_assets', 0)}")
        logger.info(f"Successfully updated: {result.get('updated_count', 0)}")
        logger.info(f"Skipped: {result.get('skipped_count', 0)}")
        logger.info(f"Fuzzy datetime matches: {result.get('fuzzy_match_count', 0)}")
        logger.info(f"Errors: {result.get('error_count', 0)}")
        error_files = result.get('error_files', [])
        if error_files:
            logger.info("\nError details:")
            for ef in error_files:
                logger.info(f"  - {ef}")
        if resolved_args.get("dry_run"):
            logger.info("\nThis was a dry run. No files were actually modified.")

if __name__ == '__main__':
    main()
