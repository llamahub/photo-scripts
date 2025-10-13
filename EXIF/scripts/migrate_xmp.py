#!/usr/bin/env python3
"""
XMP Sidecar Migration Script

This script finds orphaned XMP files in a source directory and moves them to match
the directory structure of their corresponding image files in a target directory.

This is useful when images have been organized but their XMP sidecar files were left behind.
"""

import argparse
import sys
from pathlib import Path
import shutil
from datetime import datetime

# Add project source paths
project_root = Path(__file__).parent.parent
common_root = project_root.parent / 'COMMON'
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(common_root / 'src'))

try:
    from common.logging import ScriptLogging
    HAS_SCRIPT_LOGGING = True
except ImportError:
    import logging
    HAS_SCRIPT_LOGGING = False


class XMPMigrator:
    """Handles migration of orphaned XMP sidecar files."""
    
    def __init__(self, logger):
        self.logger = logger
        self.stats = {
            'xmp_found': 0,
            'images_found': 0,
            'xmp_moved': 0,
            'xmp_skipped': 0,
            'errors': 0
        }
    
    def find_image_extensions(self) -> set:
        """Get supported image extensions."""
        return {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', 
               '.heic', '.heif', '.webp', '.raw', '.cr2', '.nef', '.arw', 
               '.dng', '.orf', '.rw2', '.pef', '.srw', '.raf', '.3fr'}
    
    def build_image_index(self, target_dir: Path) -> dict:
        """
        Build an index of all image files in target directory.
        
        Returns:
            Dict mapping image filename (without extension) to full target path
        """
        image_index = {}
        image_extensions = self.find_image_extensions()
        
        self.logger.info(f"Building image index from target directory: {target_dir}")
        
        for image_file in target_dir.rglob('*'):
            if image_file.is_file() and image_file.suffix.lower() in image_extensions:
                # Use stem (filename without extension) as key
                stem = image_file.stem
                image_index[stem] = image_file
                self.stats['images_found'] += 1
                
                if len(image_index) % 1000 == 0:
                    self.logger.debug(f"Indexed {len(image_index)} images...")
        
        self.logger.info(f"Found {len(image_index)} images in target directory")
        return image_index
    
    def find_orphaned_xmp_files(self, source_dir: Path) -> list:
        """Find all XMP files in source directory."""
        xmp_files = []
        
        self.logger.info(f"Scanning for XMP files in source directory: {source_dir}")
        
        for xmp_file in source_dir.rglob('*.xmp'):
            if xmp_file.is_file():
                xmp_files.append(xmp_file)
                self.stats['xmp_found'] += 1
                
                if len(xmp_files) % 100 == 0:
                    self.logger.debug(f"Found {len(xmp_files)} XMP files...")
        
        self.logger.info(f"Found {len(xmp_files)} XMP files in source directory")
        return xmp_files
    
    def migrate_xmp_file(self, xmp_file: Path, image_index: dict, dry_run: bool = False) -> bool:
        """
        Migrate a single XMP file to match its corresponding image location.
        
        Args:
            xmp_file: Path to the XMP file
            image_index: Index of image files in target
            dry_run: If True, only log what would be done
            
        Returns:
            True if successful or would be successful
        """
        # Get the stem (filename without .xmp extension)
        # For files like "image.jpg.xmp", we want "image" not "image.jpg"
        xmp_stem = xmp_file.stem  # This gives us "image.jpg"
        if xmp_stem.endswith('.jpg') or xmp_stem.endswith('.jpeg'):
            image_stem = Path(xmp_stem).stem  # This gives us "image"
        else:
            image_stem = xmp_stem
        
        # Look for corresponding image in target
        if image_stem not in image_index:
            self.logger.debug(f"No corresponding image found for XMP: {xmp_file} (looking for: {image_stem})")
            return False
        
        # Get target image path and create XMP target path
        target_image = image_index[image_stem]
        target_xmp = target_image.with_suffix('.xmp')
        
        try:
            if not dry_run:
                # Check if target XMP already exists
                if target_xmp.exists():
                    self.logger.warning(f"Target XMP already exists, skipping: {target_xmp}")
                    self.stats['xmp_skipped'] += 1
                    return False
                
                # Create target directory if needed
                target_xmp.parent.mkdir(parents=True, exist_ok=True)
                
                # Move the XMP file
                shutil.move(str(xmp_file), str(target_xmp))
                self.logger.debug(f"Moved XMP: {xmp_file} -> {target_xmp}")
                self.stats['xmp_moved'] += 1
            else:
                self.logger.debug(f"Would move XMP: {xmp_file} -> {target_xmp}")
                self.stats['xmp_moved'] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error moving XMP {xmp_file} to {target_xmp}: {e}")
            self.stats['errors'] += 1
            return False
    
    def run_migration(self, source_dir: Path, target_dir: Path, dry_run: bool = False) -> dict:
        """
        Run the complete XMP migration process.
        
        Args:
            source_dir: Directory containing orphaned XMP files
            target_dir: Directory containing organized images
            dry_run: If True, only show what would be done
            
        Returns:
            Statistics dictionary
        """
        # Validate directories
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory does not exist: {source_dir}")
        if not target_dir.exists():
            raise FileNotFoundError(f"Target directory does not exist: {target_dir}")
        
        # Build image index from target directory
        image_index = self.build_image_index(target_dir)
        
        if not image_index:
            self.logger.warning("No images found in target directory")
            return self.stats
        
        # Find orphaned XMP files
        xmp_files = self.find_orphaned_xmp_files(source_dir)
        
        if not xmp_files:
            self.logger.info("No XMP files found in source directory")
            return self.stats
        
        # Process each XMP file
        self.logger.info(f"Processing {len(xmp_files)} XMP files...")
        
        for i, xmp_file in enumerate(xmp_files):
            self.migrate_xmp_file(xmp_file, image_index, dry_run)
            
            # Progress reporting
            if (i + 1) % 50 == 0 or (i + 1) == len(xmp_files):
                self.logger.info(f"Progress: {i + 1}/{len(xmp_files)} XMP files processed")
        
        return self.stats
    
    def print_summary(self, dry_run: bool = False):
        """Print migration summary statistics."""
        self.logger.info("=" * 80)
        self.logger.info(" XMP MIGRATION COMPLETE" if not dry_run else " XMP MIGRATION PREVIEW")
        self.logger.info("=" * 80)
        self.logger.info(f"XMP files found in source: {self.stats['xmp_found']}")
        self.logger.info(f"Images found in target: {self.stats['images_found']}")
        
        if dry_run:
            self.logger.info(f"XMP files that would be moved: {self.stats['xmp_moved']}")
        else:
            self.logger.info(f"XMP files successfully moved: {self.stats['xmp_moved']}")
        
        self.logger.info(f"XMP files skipped (target exists): {self.stats['xmp_skipped']}")
        self.logger.info(f"Errors encountered: {self.stats['errors']}")
        self.logger.info("=" * 80)


def setup_logging(debug: bool = False):
    """Set up logging using ScriptLogging if available, otherwise basic logging."""
    if HAS_SCRIPT_LOGGING:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"migrate_xmp_{timestamp}",
            debug=debug
        )
    else:
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger("migrate_xmp")
    
    return logger


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate orphaned XMP sidecar files to match organized image structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script helps migrate XMP sidecar files after images have been organized.

It finds XMP files in the source directory and moves them to the target directory
to match the location of their corresponding image files.

Examples:
  %(prog)s /old/image/location /new/organized/location --dry-run
  %(prog)s --source /source/dir --target /target/dir
  %(prog)s /source /target --debug
        """
    )
    
    # Positional arguments
    parser.add_argument('source', nargs='?',
                       help='Source directory containing orphaned XMP files')
    parser.add_argument('target', nargs='?', 
                       help='Target directory containing organized images')
    
    # Named arguments  
    parser.add_argument('--source', dest='source_named',
                       help='Source directory containing orphaned XMP files')
    parser.add_argument('--target', dest='target_named',
                       help='Target directory containing organized images')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually moving files')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    # Resolve arguments
    source = args.source or args.source_named
    target = args.target or args.target_named
    
    if not source:
        parser.error("Source directory is required")
    if not target:
        parser.error("Target directory is required")
    
    try:
        # Setup logging
        logger = setup_logging(args.debug)
        
        logger.info("Starting XMP migration")
        logger.info(f"Source directory: {source}")
        logger.info(f"Target directory: {target}")
        logger.info(f"Dry run mode: {args.dry_run}")
        
        # Create migrator and run
        migrator = XMPMigrator(logger)
        migrator.run_migration(Path(source), Path(target), args.dry_run)
        
        # Print summary
        migrator.print_summary(args.dry_run)
        
        if migrator.stats['errors'] > 0:
            logger.warning("Migration completed with errors")
            return 1
        
        logger.info("XMP migration completed successfully")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())