#!/usr/bin/env python3
"""
Photo Organization Script - Simple CLI interface for PhotoOrganizer

Organizes photos from a source directory into a target directory with structured
subdirectories based on photo dates obtained from EXIF metadata.

Target directory structure: <decade>/<year>/<year>-<month>/<parent folder>/<filename>
- <decade>: Decade in format "YYYY+" (e.g., 1990+, 2000+, 2010+)  
- <year>: 4-digit year (e.g., 1995, 2021)
- <month>: 2-digit month (e.g., 01, 02, 12)
- <parent folder>: Name of immediate parent folder from source
- <filename>: Original filename
"""

import argparse
import sys
from pathlib import Path

# Add project source paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

try:
    from exif import PhotoOrganizer
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Organize photos by date using EXIF metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Target directory structure:
  <decade>/<year>/<year>-<month>/<parent folder>/<filename>

Where:
  - <decade>: Decade in format "YYYY+" (e.g., 1990+, 2000+, 2010+)
  - <year>: 4-digit year (e.g., 1995, 2021)
  - <month>: 2-digit month (e.g., 01, 02, 12)  
  - <parent folder>: Name of immediate parent folder from source
  - <filename>: Original filename

Examples:
  %(prog)s /path/to/photos /path/to/organized
  %(prog)s --source /path/to/photos --target /path/to/organized --dry-run
  %(prog)s /path/to/photos /path/to/organized --debug --move
  %(prog)s /path/to/photos /path/to/organized --workers 8 --move
  . run organize "tests/test_images .tmp/sorted" 
        """
    )
    
    # Positional arguments
    parser.add_argument('source', nargs='?', help='Source directory containing photos')
    parser.add_argument('target', nargs='?', help='Target directory for organized photos')
    
    # Named arguments
    parser.add_argument('--source', dest='source_named', 
                       help='Source directory containing photos (required)')
    parser.add_argument('--target', dest='target_named', 
                       help='Target directory for organized photos (required)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually copying files')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output with detailed logging')
    parser.add_argument('--move', action='store_true',
                       help='Move files instead of copying them (faster for large sets)')
    parser.add_argument('--workers', type=int, 
                       help='Number of parallel workers (default: auto-detect, use 1 for single-threaded)')
    
    args = parser.parse_args()
    
    # Determine source and target
    source = args.source_named or args.source
    target = args.target_named or args.target
    
    if not source:
        parser.error("source directory is required")
    if not target:
        parser.error("target directory is required")
    
    try:
        organizer = PhotoOrganizer(
            source=source,
            target=target,
            dry_run=args.dry_run,
            debug=args.debug,
            move_files=args.move,
            max_workers=args.workers
        )
        
        organizer.run()
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())