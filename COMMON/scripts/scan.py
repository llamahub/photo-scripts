#!/usr/bin/env python3
"""
Scan utility script for analyzing file types in a directory tree.

Reports total file counts and breakdown by image, video, and other types.
Optionally shows detailed breakdown per subfolder and extension.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import os

# Standard COMMON import pattern
common_src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    import logging
    ScriptLogging = None


IMAGE_EXTS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
    '.heic', '.raw'
}
VIDEO_EXTS = {
    '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
    '.mts', '.m2ts', '.3gp'
}

  
class ScanAnalyzer:
    """Handles scanning and reporting file type counts."""
    def __init__(self, source_path: Path, logger):
        self.source_path = Path(source_path)
        self.logger = logger
        self.stats = {
            'total_files': 0,
            'image_files': 0,
            'video_files': 0,
            'other_files': 0,
            'errors': 0,
            'detail': {}
        }

    def classify_file(self, ext: str) -> str:
        ext = ext.lower()
        if ext in IMAGE_EXTS:
            return 'image'
        elif ext in VIDEO_EXTS:
            return 'video'
        else:
            return 'other'

    def scan(self, detail: bool = False):
        """Scan directory tree and count files by type."""
        for root, dirs, files in os.walk(self.source_path):
            root_path = Path(root)
            folder_stats = {'image': 0, 'video': 0, 'other': 0, 'exts': {}}
            for fname in files:
                ext = Path(fname).suffix.lower()
                ftype = self.classify_file(ext)
                self.stats['total_files'] += 1
                self.stats[f"{ftype}_files"] += 1
                folder_stats[ftype] += 1
                folder_stats['exts'][ext] = folder_stats['exts'].get(ext, 0) + 1
            if detail:
                self.stats['detail'][str(root_path)] = folder_stats

    def report(self, detail: bool = False):
        self.logger.info("=" * 60)
        self.logger.info("SCAN SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Source: {self.source_path}")
        self.logger.info(f"Total files: {self.stats['total_files']:,}")
        self.logger.info(f"Image files: {self.stats['image_files']:,}")
        self.logger.info(f"Video files: {self.stats['video_files']:,}")
        self.logger.info(f"Other files: {self.stats['other_files']:,}")
        if detail:
            self.logger.info("")
            self.logger.info("DETAIL BREAKDOWN BY FOLDER AND EXTENSION")
            self.logger.info("-" * 40)
            for folder, stats in self.stats['detail'].items():
                self.logger.info(f"{folder}:")
                self.logger.info(
                    f"  Images: {stats['image']}, Videos: {stats['video']}, "
                    f"Other: {stats['other']}"
                )
                self.logger.info("  Extensions:")
                for ext, count in sorted(stats['exts'].items(), key=lambda x: -x[1]):
                    self.logger.info(f"    {ext or '[no ext]'}: {count}")
        self.logger.info("=" * 60)
        if self.stats['errors'] > 0:
            self.logger.warning(f"Access errors: {self.stats['errors']}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Scan directory for file type counts (image, video, other)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/folder                    # Basic scan analysis
  %(prog)s --source /path/to/folder          # Using named argument
  %(prog)s /path/to/folder --detail          # Show detailed breakdown
  %(prog)s /path/to/folder --detail --debug  # With debug output
        """
    )
    
    # Positional argument (also available as named)
    parser.add_argument('source', nargs='?',
                        help='Path to source directory to scan')
    
    # Named arguments
    parser.add_argument('--source', dest='source_named',
                        help='Path to source directory to scan')
    parser.add_argument('--detail', action='store_true',
                        help='Show breakdown by subfolder and extension')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug output')
    
    args = parser.parse_args()
    
    # Resolve source: positional takes precedence over named
    if args.source:
        final_source = args.source
    elif args.source_named:
        final_source = args.source_named
    else:
        parser.error("Source directory is required "
                     "(provide as positional argument or --source)")
    
    # Create a new namespace with resolved values
    final_args = argparse.Namespace()
    final_args.source = Path(final_source)
    final_args.detail = args.detail
    final_args.debug = args.debug
    
    return final_args


def main():
    args = parse_arguments()
    # Standard logging setup
    if ScriptLogging:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"scan_{timestamp}",
            debug=args.debug
        )
    else:
        logging.basicConfig(
            level=logging.DEBUG if args.debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger("scan")
    if not args.source.exists():
        logger.error(f"Source directory does not exist: {args.source}")
        return 1
    if not args.source.is_dir():
        logger.error(f"Source path is not a directory: {args.source}")
        return 1
    logger.info("Starting scan analysis")
    logger.info(f"Source directory: {args.source}")
    if args.detail:
        logger.info("Detail breakdown enabled")
    analyzer = ScanAnalyzer(args.source, logger)
    try:
        analyzer.scan(detail=args.detail)
        analyzer.report(detail=args.detail)
        logger.info("Scan analysis completed successfully")
        return 0
    except KeyboardInterrupt:
        logger.warning("Analysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during scan: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
