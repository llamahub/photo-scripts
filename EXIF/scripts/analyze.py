#!/usr/bin/env python3
"""
High-performance image organization and date consistency analysis.

This script analyzes images and videos to check date consistency between:
- Filename dates
- EXIF metadata dates
- Parent directory dates

Results are saved to CSV with detailed analysis and statistics.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

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
    from exif import ImageAnalyzer, ImageData
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)

# Script metadata
SCRIPT_INFO = {
    'name': 'Image Analysis Script',
    'description': '''High-performance image organization and date consistency analysis

Analyzes images and videos to check date consistency between:
- Filename dates
- EXIF metadata dates
- Parent directory dates

Results are saved to CSV with detailed analysis and statistics.''',
    'examples': [
        '/path/to/photos',
        '--source /path/to/photos --output analysis.csv',
        '/path/to/photos --target /organized --label "Family"',
        '/path/to/photos --sample 100 --workers 4 --verbose'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'source': {
        'positional': True,
        'help': 'Source root folder to analyze'
    },
    'target': {
        'flag': '--target',
        'help': 'Target root folder for comparison (optional - omit for faster analysis)'
    },
    'label': {
        'flag': '--label',
        'default': '',
        'help': 'Label for target filenames (optional)'
    },
    'output': {
        'flag': '--output',
        'help': 'CSV output file path (default: .log/analyze_fast_YYYY-MM-DD_HHMM.csv)'
    },
    'no_stats': {
        'flag': '--no-stats',
        'action': 'store_true',
        'help': "Don't print statistics to console"
    },
    'workers': {
        'flag': '--workers',
        'type': int,
        'help': 'Number of parallel workers (default: auto-detect)'
    },
    'batch_size': {
        'flag': '--batch-size',
        'type': int,
        'default': 100,
        'help': 'Batch size for ExifTool calls (default: 100)'
    },
    'sample': {
        'flag': '--sample',
        'type': int,
        'help': 'Analyze only a random sample of N images'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def save_custom_csv(csv_path, results):
    """Save results in the original CSV format for compatibility."""
    import csv
    
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    with open(csv_path, "w", newline="", encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header matching original format
        writer.writerow([
            "Condition", "Status", "Month Match", "Parent Date", "Filename Date", "Image Date",
            "Source Path", "Target Path", "Target Exists", "Alt Filename Date", "Set Date"
        ])
        
        # Write data rows
        for result in results:
            if 'error' in result:
                # Handle error cases
                writer.writerow([
                    "Error", "Error", "", "", "", "",
                    result['filepath'], "", "FALSE", result.get('error', ''), ""
                ])
            else:
                writer.writerow([
                    result.get('condition_desc', ''),
                    result.get('condition_category', ''),
                    result.get('month_match', ''),
                    result.get('parent_date_norm', ''),
                    result.get('filename_date_norm', ''),
                    result.get('image_date_norm', ''),
                    result.get('filepath', ''),
                    result.get('target_path', ''),
                    result.get('target_exists', 'FALSE'),
                    result.get('alt_filename_date', ''),
                    ''  # Empty "Set Date" column for user to fill in
                ])


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
        'source_folder': ['source_file', 'source']
    })
    
    # Setup logging with consistent pattern
    # Use script name without extension for proper log file naming
    logger = parser.setup_logging(resolved_args, "analyze")
    
    # Display configuration with analyze-specific labels
    config_map = {
        'source_folder': 'Source folder',
        'target': 'Target folder',
        'label': 'Label',
        'output': 'Output CSV file',
        'no_stats': 'Skip statistics',
        'workers': 'Workers',
        'batch_size': 'Batch size',
        'sample': 'Sample size'
    }
    parser.display_configuration(resolved_args, config_map)
    
    try:
        # Convert to proper paths and validate
        source_folder = resolved_args['source_folder']
        target_folder = resolved_args.get('target')
        
        logger.info("Starting image analysis")
        logger.info(f"Source folder: {source_folder}")
        
        # Validate source folder
        if not os.path.exists(source_folder):
            logger.error(f"Source folder not found: {source_folder}")
            return 1
        
        # Determine output file path
        output_file = resolved_args.get('output')
        if not output_file:
            now = datetime.now().strftime("%Y-%m-%d_%H%M")
            log_dir = Path(".log")
            log_dir.mkdir(exist_ok=True)
            output_file = str(log_dir / f"analyze_fast_{now}.csv")
        
        logger.info(f"Output file: {output_file}")
        
        if target_folder:
            logger.info(f"Target folder: {target_folder}")
        else:
            logger.info("Target folder: (skipped for faster analysis)")
            
        # Log configuration details
        workers = resolved_args.get('workers')
        batch_size = resolved_args.get('batch_size', 100)
        sample_size = resolved_args.get('sample')
        
        if workers:
            logger.info(f"Workers: {workers}")
        logger.info(f"Batch size: {batch_size}")
        if sample_size:
            logger.info(f"Sample size: {sample_size}")
        
        # Create analyzer
        logger.info("Initializing ImageAnalyzer")
        analyzer = ImageAnalyzer(
            folder_path=source_folder, 
            target_path=target_folder,
            output_path=output_file,
            label=resolved_args.get('label', ''),
            max_workers=workers,
            batch_size=batch_size
        )
        
        # Choose analysis method
        logger.info("Starting image analysis process")
        if sample_size:
            logger.info(f"Running sample analysis (n={sample_size})")
            results = analyzer.analyze_sample(sample_size=sample_size)
        else:
            logger.info("Running full analysis with progress tracking")
            results = analyzer.analyze_with_progress()
        
        # Generate target filename and target exists info for each result (only if target specified)
        if target_folder:
            logger.info("Generating target paths...")
            for i, result in enumerate(results):
                if 'error' not in result:
                    source_path = result['filepath']
                    target_path = ImageData.getTargetFilename(source_path, target_folder, resolved_args.get('label', ''))
                    target_exists = os.path.exists(target_path)
                    
                    # Add target information to result
                    result['target_path'] = target_path
                    result['target_exists'] = "TRUE" if target_exists else "FALSE"
                
                # Progress for target path generation
                if (i + 1) % 100 == 0 or i == len(results) - 1:
                    logger.info(f"Target paths: {i + 1}/{len(results)}")
        else:
            # Add empty target fields when no target specified
            for result in results:
                result['target_path'] = ""
                result['target_exists'] = ""
        
        # Save to CSV with custom format to match original
        logger.info("Saving results to CSV...")
        save_custom_csv(output_file, results)
        
        logger.info(f"Analysis complete!")
        logger.info(f"Results: {output_file}")
        logger.info(f"Analyzed: {len(results)} images")
        
        # Print statistics unless disabled
        if not resolved_args.get('no_stats', False):
            logger.info("Generating statistics...")
            analyzer.print_statistics(results)
        
        logger.info("Image analysis completed successfully")
        return 0
            
    except KeyboardInterrupt:
        logger.warning("Analysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())