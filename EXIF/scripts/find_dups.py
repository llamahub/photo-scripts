#!/usr/bin/env python3
"""
Find duplicate images/videos between source and target directories.

Uses multiple detection strategies:
- Target Filename match (using getTargetFilename for organization patterns)
- Exact filename match (identical filenames)
- Partial filename match (similar filenames)

Results saved to CSV file with match details and statistics.
"""

import sys
import os
from pathlib import Path

# Add COMMON to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))

# Add project source paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

# Import COMMON framework modules
try:
    from common.logging import ScriptLogging
    from common.argument_parser import (
        ScriptArgumentParser,
        create_standard_arguments,
        merge_arguments
    )
except ImportError:
    ScriptLogging = None
    print("Warning: COMMON modules not available")
    sys.exit(1)

# Import EXIF modules
try:
    from exif.duplicate_finder import DuplicateFinder
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)

# Script metadata
SCRIPT_INFO = {
    'name': 'Duplicate Finder Script',
    'description': '''Find duplicate images/videos between source and target directories

Uses multiple detection strategies:
- Target Filename match (using getTargetFilename for organization patterns)
- Exact filename match (identical filenames)
- Partial filename match (similar filenames)

Results saved to CSV file with match details and statistics.''',
    'examples': [
        '/path/to/source /path/to/target',
        '--source /path/to/source --target /path/to/target',
        '/path/to/source /path/to/target --output results.csv',
        '/path/to/source /path/to/target --verbose --dry-run'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'source': {
        'positional': True,
        'help': 'Source directory to scan for images/videos'
    },
    'target': {
        'positional': True,
        'help': 'Target directory to search for duplicates'
    },
    'output': {
        'flag': '--output',
        'help': 'Output CSV file (default: .log/find_dups_TIMESTAMP.csv)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def main():
    """Main entry point with consistent argument parsing and structure."""
    
    # Create argument parser
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    
    # Print standardized header
    parser.print_header()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate and resolve required arguments
    resolved_args = parser.validate_required_args(args, {
        'source_directory': ['source_file', 'source'],
        'target_directory': ['target_file', 'target']
    })
    
    # Setup logging with consistent pattern
    logger = parser.setup_logging(resolved_args, "find_dups_script")
    
    # Display configuration with find_dups-specific labels
    config_map = {
        'source_directory': 'Source directory',
        'target_directory': 'Target directory',
        'output': 'Output CSV file'
    }
    parser.display_configuration(resolved_args, config_map)
    
    try:
        # Convert to Path objects and validate
        source_path = Path(resolved_args['source_directory'])
        target_path = Path(resolved_args['target_directory'])
        
        logger.info("Starting duplicate finder")
        logger.info(f"Source directory: {source_path}")
        logger.info(f"Target directory: {target_path}")
        
        # Validate directories
        for dir_path, name in [(source_path, "Source"), (target_path, "Target")]:
            if not dir_path.exists():
                error_msg = f"{name} directory does not exist: {dir_path}"
                logger.error(error_msg)
                if not resolved_args.get('quiet'):
                    print(f"❌ Error: {error_msg}")
                return 1
            
            if not dir_path.is_dir():
                error_msg = f"{name} path is not a directory: {dir_path}"
                logger.error(error_msg)
                if not resolved_args.get('quiet'):
                    print(f"❌ Error: {error_msg}")
                return 1
        
        # Determine output file
        if resolved_args.get('output'):
            output_file = Path(resolved_args['output'])
        else:
            # Create .log directory if it doesn't exist
            log_dir = Path('.log')
            log_dir.mkdir(exist_ok=True)
            
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = log_dir / f"find_dups_{timestamp}.csv"
        
        logger.info(f"Output file: {output_file}")
        
        if not resolved_args.get('quiet'):
            print(f"Source directory: {source_path}")
            print(f"Target directory: {target_path}")
            print(f"Output file: {output_file}")
            if resolved_args.get('dry_run'):
                print("Mode: DRY RUN (simulation only)")
            print()
        
        # Initialize duplicate finder
        logger.info("Initializing DuplicateFinder")
        finder = DuplicateFinder(
            source_dir=source_path,
            target_dir=target_path,
            logger=logger
        )
        
        logger.info("Starting duplicate detection process")
        
        # Process duplicates
        if resolved_args.get('dry_run'):
            # In dry run mode, we could potentially just scan and count
            # but the DuplicateFinder doesn't have a dry_run mode built in
            # so we'll run normally but not save results
            results = finder.process_duplicates()
            logger.info("Dry run completed - results not saved")
        else:
            results = finder.process_duplicates()
            
            # Save results
            finder.save_results(results, output_file)
            logger.info(f"Results saved to: {output_file}")
        
        # Print summary
        stats = finder.get_stats() if hasattr(finder, 'get_stats') else finder.stats
        
        logger.info("Duplicate finder completed successfully")
        logger.info(f"Files processed: {stats.get('total_processed', 0)}")
        logger.info(f"Target filename matches: {stats.get('target_filename_matches', 0)}")
        logger.info(f"Exact matches: {stats.get('exact_matches', 0)}")
        logger.info(f"Partial matches: {stats.get('partial_matches', 0)}")
        logger.info(f"No matches: {stats.get('no_matches', 0)}")
        if stats.get('errors', 0) > 0:
            logger.warning(f"Errors encountered: {stats.get('errors', 0)}")
        
        if not resolved_args.get('quiet'):
            print("✅ Duplicate finder completed successfully")
            print(f"Files processed: {stats.get('total_processed', 0)}")
            print(f"Target filename matches: {stats.get('target_filename_matches', 0)}")
            print(f"Exact matches: {stats.get('exact_matches', 0)}")
            print(f"Partial matches: {stats.get('partial_matches', 0)}")
            print(f"No matches: {stats.get('no_matches', 0)}")
            if stats.get('errors', 0) > 0:
                print(f"⚠️  Errors encountered: {stats.get('errors', 0)}")
            if not resolved_args.get('dry_run'):
                print(f"Results saved to: {output_file}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        if not resolved_args.get('quiet'):
            print("\\n❌ Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error during duplicate finding: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())