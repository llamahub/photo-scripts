#!/usr/bin/env python3
"""
Delete duplicate files based on CSV input.

This script reads a CSV file containing file information and deletes files
based on configurable status criteria. Supports dry-run mode for safe testing.
"""

import sys
import argparse
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

# Add the local src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

try:
    from exif.file_deleter import FileDeleter
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you're running from the EXIF directory and have set up the environment properly.")
    sys.exit(1)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Delete duplicate files based on CSV input with configurable filtering criteria",
        epilog="""
Examples:
  %(prog)s input.csv
  %(prog)s --input input.csv --dry-run
  %(prog)s input.csv --status-col match_type --status-val "Exact match"
  %(prog)s --input duplicates.csv --file-col source_path --dry-run
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Positional argument (also available as named)
    parser.add_argument('input', nargs='?',
                       help='Path to CSV file containing list of images to potentially delete')
    
    # Named arguments
    parser.add_argument('--input', dest='input_named',
                       help='Path to CSV file containing list of images to potentially delete')
    parser.add_argument('--status-col', default='match_type',
                       help='Name of the column containing status values (default: match_type)')
    parser.add_argument('--status-val', default='Exact match',
                       help='Status value indicating files should be deleted (default: "Exact match")')
    parser.add_argument('--file-col', default='source_file_path',
                       help='Name of the column containing file paths (default: source_file_path)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Only log files that would be deleted without actually deleting them')
    
    args = parser.parse_args()
    
    # Resolve input file: positional takes precedence over named
    if args.input:
        final_input = args.input
    elif args.input_named:
        final_input = args.input_named
    else:
        parser.error("Input CSV file is required (provide as positional argument or --input)")
    
    # Create a new namespace with resolved values
    final_args = argparse.Namespace()
    final_args.input = final_input
    final_args.status_col = args.status_col
    final_args.status_val = args.status_val
    final_args.file_col = args.file_col
    final_args.dry_run = args.dry_run
    
    return final_args


def setup_logging(debug=False):
    """Set up logging using ScriptLogging if available, otherwise basic logging."""
    if HAS_SCRIPT_LOGGING:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"delete_dups_{timestamp}",
            debug=debug
        )
    else:
        # Fallback to basic logging
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger("delete_dups")
    
    return logger


def main():
    """Main function."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Initialize logging
        logger = setup_logging()
        
        logger.info("Starting file deleter")
        logger.info(f"Input CSV file: {args.input}")
        logger.info(f"Status column: {args.status_col}")
        logger.info(f"Status value: {args.status_val}")
        logger.info(f"File path column: {args.file_col}")
        logger.info(f"Dry run mode: {args.dry_run}")
        
        # Validate input file exists
        if not Path(args.input).exists():
            logger.error(f"Input CSV file does not exist: {args.input}")
            return 1
        
        # Create file deleter and process files
        deleter = FileDeleter(logger)
        
        try:
            stats = deleter.delete_files_from_csv(
                csv_path=args.input,
                status_col=args.status_col,
                status_val=args.status_val,
                file_col=args.file_col,
                dry_run=args.dry_run
            )
            
            # Log final summary
            logger.info("============================================================")
            logger.info("FILE DELETER SUMMARY")
            logger.info("============================================================")
            logger.info(f"Total rows processed: {stats['total_rows']}")
            logger.info(f"Matching rows: {stats['matching_rows']}")
            
            if args.dry_run:
                logger.info(f"Files that would be deleted: {stats['files_deleted']}")
            else:
                logger.info(f"Files successfully deleted: {stats['files_deleted']}")
            
            logger.info(f"Files not found: {stats['files_not_found']}")
            logger.info(f"Errors: {stats['errors']}")
            logger.info("============================================================")
            
            if stats['errors'] > 0:
                logger.warning(f"Completed with {stats['errors']} errors")
                return 1
            else:
                logger.info("File deleter completed successfully")
                return 0
                
        except Exception as e:
            logger.error(f"Error during file deletion process: {e}")
            return 1
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())