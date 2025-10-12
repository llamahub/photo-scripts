#!/usr/bin/env python3
"""
Find duplicate images/videos between source and target directories.

This script finds duplicates using multiple strategies:
1. Target Filename match (using getTargetFilename)
2. Exact filename match 
3. Partial filename match

Results are saved to a CSV file with source file, target file, and match type.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Import COMMON framework modules with graceful fallback
try:
    # Add parent directories to path for imports
    project_root = Path(__file__).parent.parent.parent
    common_src = project_root / "COMMON" / "src"
    sys.path.insert(0, str(common_src))
    
    from common.logging import ScriptLogging
    HAS_SCRIPT_LOGGING = True
except ImportError:
    import logging
    HAS_SCRIPT_LOGGING = False

# Import EXIF modules
try:
    # Add EXIF src to path
    exif_src = Path(__file__).parent.parent / "src"
    sys.path.insert(0, str(exif_src))
    
    from exif.duplicate_finder import DuplicateFinder
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Find duplicate images/videos between source and target directories",
        epilog="""
Examples:
  %(prog)s --source /path/to/source --target /path/to/target
  %(prog)s --source /path/to/source --target /path/to/target --output results.csv
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--source', required=True,
                       help='Source directory to scan for images/videos')
    parser.add_argument('--target', required=True,
                       help='Target directory to search for duplicates')
    parser.add_argument('--output',
                       help='Output CSV file (default: .log/find_dups_TIMESTAMP.csv)')
    
    return parser.parse_args()


def setup_logging(debug=False):
    """Set up logging using ScriptLogging if available, otherwise basic logging."""
    if HAS_SCRIPT_LOGGING:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"find_dups_{timestamp}",
            debug=debug
        )
    else:
        # Fallback to basic logging
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger("find_dups")
    
    return logger


def validate_directories(source_dir, target_dir, logger):
    """Validate that source and target directories exist."""
    source_path = Path(source_dir)
    target_path = Path(target_dir)
    
    if not source_path.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        return False
    
    if not source_path.is_dir():
        logger.error(f"Source path is not a directory: {source_dir}")
        return False
    
    if not target_path.exists():
        logger.error(f"Target directory does not exist: {target_dir}")
        return False
    
    if not target_path.is_dir():
        logger.error(f"Target path is not a directory: {target_dir}")
        return False
    
    return True


def get_output_file(output_arg):
    """Determine output file path."""
    if output_arg:
        return Path(output_arg)
    else:
        # Create .log directory if it doesn't exist
        log_dir = Path('.log')
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return log_dir / f"find_dups_{timestamp}.csv"


def main():
    """Main function."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Set up logging
        logger = setup_logging()
        logger.info("Starting duplicate finder")
        logger.info(f"Source directory: {args.source}")
        logger.info(f"Target directory: {args.target}")
        
        # Validate directories
        if not validate_directories(args.source, args.target, logger):
            return 1
        
        # Determine output file
        output_file = get_output_file(args.output)
        logger.info(f"Output file: {output_file}")
        
        # Initialize duplicate finder
        finder = DuplicateFinder(
            source_dir=Path(args.source),
            target_dir=Path(args.target),
            logger=logger
        )
        
        # Process duplicates
        results = finder.process_duplicates()
        
        # Save results
        finder.save_results(results, output_file)
        
        # Print summary
        finder.print_summary()
        
        logger.info("Duplicate finder completed successfully")
        return 0
        
    except KeyboardInterrupt:
        print("\\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        if 'logger' in locals():
            logger.error(f"Unexpected error: {e}")
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())