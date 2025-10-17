#!/usr/bin/env python3
"""
================================================================================
=== [Example Script] - Template demonstrating consistent argument parsing
================================================================================

This is a template script that demonstrates the consistent structure and argument
parsing pattern that all EXIF scripts should follow. It uses the shared
ScriptArgumentParser from the COMMON framework for consistent CLI interfaces.

Key features:
- Uses ScriptArgumentParser for standardized argument handling
- Single source of truth for argument definitions
- Automatic help text generation
- Integration with COMMON ScriptLogging
- Template patterns for all future EXIF script development

Follow this exact structure for all EXIF scripts to ensure consistency.
"""

import sys
import os

# Add COMMON to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))

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

# Script metadata
SCRIPT_INFO = {
    'name': 'EXIF Example Script',
    'description': 'Template demonstrating consistent argument parsing for EXIF scripts',
    'examples': [
        'input.jpg output.jpg',
        '--input input.jpg --output output.jpg --dry-run',
        'input.jpg output.jpg --source /photos --target /processed --verbose'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'input': {
        'positional': True,
        'help': 'Input image file to process'
    },
    'output': {
        'positional': True,
        'help': 'Output file to create'
    },
    'source_dir': {
        'flag': '--source',
        'help': 'Source directory containing images'
    },
    'target_dir': {
        'flag': '--target',
        'help': 'Target directory for processed images'
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
        'input_file': ['input_file', 'input'],
        'output_file': ['output_file', 'output']
    })
    
    # Setup logging with consistent pattern
    logger = parser.setup_logging(resolved_args, "exif_example_script")
    
    # Display configuration with EXIF-specific labels
    config_map = {
        'input_file': 'Input image file',
        'output_file': 'Output file',
        'source_dir': 'Source directory containing images',
        'target_dir': 'Target directory for processed images'
    }
    parser.display_configuration(resolved_args, config_map)
    
    try:
        # Initialize business logic processor
        # from exif.image_processor import ImageProcessor
        # processor = ImageProcessor(
        #     input_file=resolved_args['input_file'],
        #     output_file=resolved_args['output_file'],
        #     source_dir=resolved_args.get('source_dir'),
        #     target_dir=resolved_args.get('target_dir'),
        #     dry_run=resolved_args.get('dry_run', False),
        #     verbose=resolved_args.get('verbose', False)
        # )
        
        logger.info("Starting EXIF image processing")
        logger.info(f"Processing: {resolved_args['input_file']} → {resolved_args['output_file']}")
        
        # Example audit-level logging for file operations (INFO level)
        if resolved_args.get('source_dir'):
            logger.info(f"Scanning source directory: {resolved_args['source_dir']}")
            # Simulate finding files
            logger.info("Found 127 image files for processing")
            logger.info("Found 15 duplicate candidates based on filename patterns")
        
        # Example file operations that would be logged at INFO level
        logger.info("Analyzing EXIF data for duplicate detection")
        logger.debug("Loading EXIF parser with GPS and timestamp support")  # DEBUG: implementation detail
        
        # Simulate processing files
        example_files = [
            ("/photos/IMG_001.jpg", "/processed/2023/01/vacation_001.jpg"),
            ("/photos/IMG_001_copy.jpg", None),  # duplicate to delete
            ("/photos/IMG_002.jpg", "/processed/2023/01/vacation_002.jpg")
        ]
        
        for src_file, dst_file in example_files:
            if dst_file:
                # INFO: Critical file operations for audit trail
                if resolved_args.get('dry_run'):
                    logger.info(f"[DRY RUN] Would move: {src_file} → {dst_file}")
                else:
                    logger.info(f"Moving file: {src_file} → {dst_file}")
                
                # DEBUG: Performance and technical details
                logger.debug("File size: 2.4MB, EXIF date: 2023-01-15 14:30:22")
                logger.debug("Created target directory structure")
            else:
                # INFO: Deletion operations for audit trail
                if resolved_args.get('dry_run'):
                    logger.info(f"[DRY RUN] Would delete duplicate: {src_file}")
                else:
                    logger.info(f"Deleted duplicate file: {src_file}")
                
                # DEBUG: Duplicate detection details
                logger.debug("Duplicate detected: same hash as IMG_001.jpg")
        
        # INFO: Summary for audit trail
        processed_count = len([f for f in example_files if f[1]])
        deleted_count = len([f for f in example_files if not f[1]])
        logger.info(f"Processing complete: {processed_count} files moved, {deleted_count} duplicates removed")
        
        if resolved_args.get('target_dir'):
            logger.info(f"All files organized in target directory: {resolved_args['target_dir']}")
        
        logger.info("EXIF image processing completed successfully")
        
        if not resolved_args.get('quiet'):
            print("✅ Processing completed successfully")
            # print(f"Results: {results}")
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
