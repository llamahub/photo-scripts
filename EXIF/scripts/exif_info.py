#!/usr/bin/env python3
"""
================================================================================
=== [exif_info] - Extract EXIF information from images
================================================================================
"""

import sys
import os
import csv

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
SCRIPT_NAME = 'exif_info'
SCRIPT_INFO = {
    'name': SCRIPT_NAME,
    'description': 'Extract EXIF information from images',
    'examples': [
        'input.jpg',
        '--input input.jpg --output output.csv--dry-run',
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
        'help': 'Output csv file to create'
    },
    'source_dir': {
        'flag': '--source',
        'help': 'Source directory containing images'
    },
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
    # Require either a single input file (positional `input` or `--input`) OR
    # a source directory (`--source`), but not both. Output file is required.
    input_val = getattr(args, 'input_file', None) or getattr(args, 'input', None)
    # COMMON argument parser may store the '--source' flag under either 'source' or 'source_dir'
    source_val = getattr(args, 'source_dir', None) or getattr(args, 'source', None)
    output_val = getattr(args, 'output_file', None) or getattr(args, 'output', None)

    # Enforce mutual exclusivity: one of input or source must be provided
    if not input_val and not source_val:
        parser.error('Either an input file (positional or --input) or --source must be provided')

    if input_val and source_val:
        parser.error('Provide only one of input file (positional or --input) OR --source, not both')

    # If output not provided, default to .log/exif_info_{timestamp}.csv
    if not output_val:
        from datetime import datetime
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Ensure .log directory exists
        log_dir = os.path.join(os.path.dirname(__file__), '..', '.log')
        log_dir = os.path.normpath(log_dir)
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            # if directory creation fails, fall back to current dir
            log_dir = os.path.join(os.path.dirname(__file__), '.log')

        output_val = os.path.join(log_dir, f'exif_info_{now_ts}.csv')

    # Build resolved args dict (start from all parsed args and normalize keys)
    resolved_args = dict(vars(args))
    # Normalize keys expected by display/other helpers
    resolved_args['input_file'] = input_val
    resolved_args['source_dir'] = source_val
    resolved_args['source'] = source_val
    resolved_args['output_file'] = output_val
    resolved_args['output'] = output_val
    
    # Setup logging with consistent pattern
    # Use script name without extension for proper log file naming
    logger = parser.setup_logging(resolved_args, SCRIPT_NAME)

    # Display configuration
    config_map = {
        'input_file': 'Input image file',
        'output_file': 'Output file',
        'source_dir': 'Source directory containing images'
    }
    parser.display_configuration(resolved_args, config_map)
    
    try:
        
        logger.info("Starting EXIF image processing")
        logger.info(f"Processing: {resolved_args['input_file']} → {resolved_args['output_file']}")

        # Ensure local EXIF analyzer module is importable
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        try:
            from exif.image_analyzer import ImageAnalyzer
        except Exception as e:
            logger.error(f"Failed to import ImageAnalyzer: {e}")
            raise

        results = []

        # If a single input file was specified, analyze that file
        if resolved_args.get('input_file'):
            input_path = resolved_args['input_file']
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")

            logger.info(f"Analyzing single image: {input_path}")
            analyzer = ImageAnalyzer(output_path=resolved_args['output_file'])

            # Use the public analyzer helper that returns the compact summary
            single_result = analyzer.analyze_single_summary(input_path)
            results = [single_result]

            if resolved_args.get('dry_run'):
                logger.info(f"Dry run: would write 1 analysis row to {resolved_args['output_file']}")
            else:
                # Write a compact CSV using the keys from the analyzer summary (preserve order)
                out_path = resolved_args['output_file']
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                try:
                    with open(out_path, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=list(single_result.keys()))
                        writer.writeheader()
                        # Convert any list values (tags) to comma-separated strings for CSV
                        row = {k: (','.join(v) if isinstance(v, list) else v) for k, v in single_result.items()}
                        writer.writerow(row)

                    logger.info(f"Wrote analysis CSV: {out_path}")
                except Exception as e:
                    logger.error(f"Failed to write CSV {out_path}: {e}")
                    raise

        else:
            # Otherwise analyze a source directory and produce the same compact
            # schema as single-file mode by using analyze_single_summary for
            # each discovered image. This favors consistency over batch
            # performance; if you want batch-mode speed we can re-use
            # _batch_extract_exif and assemble the same fields from the map.
            folder = resolved_args.get('source_dir')
            if not folder or not os.path.exists(folder):
                raise FileNotFoundError(f"Source directory not found: {folder}")

            logger.info(f"Analyzing folder: {folder}")
            analyzer = ImageAnalyzer(folder_path=folder, output_path=resolved_args['output_file'])

            # Discover images
            image_list = analyzer._find_image_files_fast(folder)

            if resolved_args.get('dry_run'):
                logger.info(f"Dry run: found {len(image_list)} images under {folder}")
            else:
                results = []
                total = len(image_list)
                for idx, img_path in enumerate(image_list, start=1):
                    try:
                        summary = analyzer.analyze_single_summary(img_path)
                        results.append(summary)
                    except Exception as e:
                        logger.error(f"Error analyzing {img_path}: {e}")
                        results.append({"filepath": img_path, "error": str(e)})

                    # Progress logging every 50 files
                    if idx % 50 == 0 or idx == total:
                        logger.info(f"Processed {idx}/{total} images...")

                # Write compact CSV using keys from the first result
                out_path = resolved_args['output_file']
                if results:
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    headers = list(results[0].keys())
                    with open(out_path, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=headers)
                        writer.writeheader()
                        for r in results:
                            row = {k: (','.join(v) if isinstance(v, list) else r.get(k, '')) for k, v in r.items()}
                            # Ensure order/keys from headers
                            writer.writerow({h: row.get(h, '') for h in headers})

                    logger.info(f"Wrote analysis CSV: {out_path}")
                else:
                    logger.info("No images found to analyze; no CSV written")

        # Print statistics if available
        try:
            if results:
                analyzer.print_statistics(results)
        except Exception:
            # Non-fatal: statistics are optional
            pass
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
