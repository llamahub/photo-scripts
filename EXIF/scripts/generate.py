#!/usr/bin/env python3
"""
Test Image Generation Script - Simple CLI interface for ImageGenerator

Generates test images from CSV data with EXIF metadata for testing photo
organization functionality.

CSV format expected:
- Root Path: Base directory path
- Parent Folder: Immediate parent directory
- Filename: Image filename (without extension)
- Source Ext: File extension
- Image Width: Width in pixels
- Image Height: Height in pixels
- Actual Format: Image format (JPEG, PNG, TIFF, HEIC)
- DateTimeOriginal: EXIF date in YYYY:MM:DD HH:MM:SS format
- ExifIFD:DateTimeOriginal: Alternative EXIF date
- XMP-photoshop:DateCreated: XMP date in YYYY-MM-DD format
"""

import argparse
import sys
from pathlib import Path

# Add project source paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

try:
    from exif import ImageGenerator
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate test images from CSV data with EXIF metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CSV Format Requirements:
  The CSV file should contain columns for image specifications:
  - Root Path: Base directory path for organization
  - Parent Folder: Immediate parent directory name
  - Filename: Image filename without extension
  - Source Ext: File extension (jpg, png, tiff, heic)
  - Image Width: Width in pixels (optional, default 100)
  - Image Height: Height in pixels (optional, default 100)
  - Actual Format: Image format for PIL creation
  - DateTimeOriginal: EXIF date (YYYY:MM:DD HH:MM:SS)
  - ExifIFD:DateTimeOriginal: Alternative EXIF date
  - XMP-photoshop:DateCreated: XMP creation date

Examples:
  %(prog)s /path/to/data.csv /path/to/output
  %(prog)s --csv /path/to/data.csv --output /path/to/output --sample 10
  %(prog)s /path/to/data.csv /path/to/output --limit 50 --debug
        """
    )
    
    # Positional arguments
    parser.add_argument('csv_file', nargs='?', 
                       help='CSV file containing image specifications')
    parser.add_argument('output_dir', nargs='?', 
                       help='Output directory for generated images')
    
    # Named arguments
    parser.add_argument('--csv', dest='csv_named', 
                       help='CSV file containing image specifications (required)')
    parser.add_argument('--output', dest='output_named', 
                       help='Output directory for generated images (required)')
    
    # Generation options
    parser.add_argument('--sample', type=int, metavar='N',
                       help='Generate only first N images as a sample')
    parser.add_argument('--limit', type=int, metavar='N',
                       help='Maximum number of images to generate')
    parser.add_argument('--no-exiftool', action='store_true',
                       help='Skip EXIF metadata setting (faster generation)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output with detailed logging')
    
    args = parser.parse_args()
    
    # Determine CSV file and output directory
    csv_file = args.csv_named or args.csv_file
    output_dir = args.output_named or args.output_dir
    
    if not csv_file:
        parser.error("CSV file is required")
    if not output_dir:
        parser.error("output directory is required")
    
    # Validate CSV file exists
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        return 1
    
    try:
        # Create ImageGenerator instance
        generator = ImageGenerator(
            csv_path=csv_path,
            output_dir=output_dir,
            debug=args.debug,
            use_exiftool=not args.no_exiftool
        )
        
        # Determine generation parameters
        if args.sample and args.limit:
            print("Warning: Both --sample and --limit specified, using --sample", 
                  file=sys.stderr)
            limit = None
            sample_size = args.sample
        elif args.sample:
            limit = None
            sample_size = args.sample
        elif args.limit:
            limit = args.limit
            sample_size = None
        else:
            limit = None
            sample_size = None
        
        # Run image generation
        success = generator.run(limit=limit, sample_size=sample_size)
        
        if success:
            # Print final statistics
            stats = generator.get_stats()
            print(f"\n🎉 Image generation completed successfully!")
            print(f"📊 Generated {stats['generated']} images from {stats['total_rows']} specifications")
            if stats['errors'] > 0:
                print(f"⚠️  {stats['errors']} generation errors occurred")
            if stats['exif_set'] > 0:
                print(f"🏷️  EXIF metadata set for {stats['exif_set']} images")
            print(f"📁 Output directory: {Path(output_dir).resolve()}")
            return 0
        else:
            print(f"❌ Image generation failed or had low success rate", file=sys.stderr)
            return 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())