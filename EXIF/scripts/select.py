#!/usr/bin/env python3
"""
Select Images Script

Creates a random sample of image files from a source directory, copying them to a target 
directory while preserving folder structure and including associated metadata files (sidecars).

This script provides a command-line interface for the ImageSelector class.
"""

import argparse
import sys
from pathlib import Path

# Add the src directory to Python path for imports
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

try:
    from exif.image_selector import ImageSelector
except ImportError as e:
    print(f"Error importing ImageSelector: {e}", file=sys.stderr)
    print("Make sure the exif module is properly installed or PYTHONPATH is set correctly", file=sys.stderr)
    sys.exit(1)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Select a random sample of image files from source directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/photos
  %(prog)s --source /path/to/photos --target /tmp/sample --files 50 --clean
  %(prog)s /path/to/photos /tmp/test --depth 3 --perfolder 5 --debug
        """
    )
    
    # Positional arguments
    parser.add_argument('source', nargs='?', help='Root source folder')
    parser.add_argument('target', nargs='?', help='Root target folder')
    
    # Named arguments
    parser.add_argument('--source', dest='source_named', 
                       help='Root source folder (required)')
    parser.add_argument('--target', dest='target_named', 
                       help='Root target folder (default: /mnt/photo_drive/Test-input)')
    parser.add_argument('--files', type=int, default=10,
                       help='Max number of files (default: 10)')
    parser.add_argument('--folders', type=int, default=3,
                       help='Max number of subfolders (default: 3)')
    parser.add_argument('--depth', type=int, default=2,
                       help='Max depth of subfolders (default: 2)')
    parser.add_argument('--perfolder', type=int, default=2,
                       help='Max number of image files per subfolder (default: 2)')
    parser.add_argument('--clean', action='store_true',
                       help='Delete everything from target first')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    # Determine source and target
    source = args.source_named or args.source
    target = args.target_named or args.target or '/mnt/photo_drive/Test-input'
    
    if not source:
        parser.error("source folder is required")
    
    try:
        # Create and run ImageSelector
        selector = ImageSelector(
            source=source,
            target=target,
            max_files=args.files,
            max_folders=args.folders,
            max_depth=args.depth,
            max_per_folder=args.perfolder,
            clean_target=args.clean,
            debug=args.debug
        )
        
        stats = selector.run()
        
        # Print final summary
        if stats['errors'] == 0:
            print(f"Successfully copied {stats['copied_files']} files with {stats['copied_sidecars']} sidecars")
        else:
            print(f"Copied {stats['copied_files']} files with {stats['copied_sidecars']} sidecars ({stats['errors']} errors)")
            return 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())