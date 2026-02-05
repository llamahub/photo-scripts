#!/usr/bin/env python3
"""
================================================================================
=== [Example Script] - Template demonstrating consistent argument parsing
================================================================================

This is a template script that demonstrates the consistent structure and argument
parsing pattern that all COMMON scripts should follow. It uses the shared
ScriptArgumentParser from the COMMON framework for consistent CLI interfaces.

Key features:
- Uses ScriptArgumentParser for standardized argument handling
- Single source of truth for argument definitions
- Automatic help text generation
- Integration with COMMON ScriptLogging
- Template patterns for all future COMMON script development

Follow this exact structure for all COMMON scripts to ensure consistency.
"""

import sys
import os

# Add src to path for COMMON modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import COMMON framework modules
from common.logging import ScriptLogging
from common.argument_parser import (
    ScriptArgumentParser,
    create_standard_arguments,
    merge_arguments
)

# Script metadata
SCRIPT_INFO = {
    'name': 'Example Script',
    'description': 'Template demonstrating consistent argument parsing',
    'examples': [
        'input.csv output.csv',
        '--input input.csv --output output.csv --dry-run',
        'input.csv output.csv --source /src --target /dst --verbose'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'input': {
        'flag': '--input',
        'positional': True,
        'help': 'Input file to process'
    },
    'output': {
        'flag': '--output',
        'positional': True,
        'help': 'Output file to create'
    },
    'source': {
        'flag': '--source',
        'help': 'Source directory for processing'
    },
    'target': {
        'flag': '--target',
        'help': 'Target directory for output'
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
        'input': ['input', 'input_file'],
        'output': ['output', 'output_file']
    })
    
    # Setup logging with consistent pattern
    # Use script name without extension for proper log file naming
    logger = parser.setup_logging(resolved_args, "example_script")
    
    # Display configuration
    parser.display_configuration(resolved_args)
    
    try:
        # Initialize business logic processor
        # processor = ExampleProcessor(
        #     input_file=resolved_args['input'],
        #     output_file=resolved_args['output'],
        #     source=resolved_args.get('source'),
        #     target=resolved_args.get('target'),
        #     dry_run=resolved_args.get('dry_run', False),
        #     verbose=resolved_args.get('verbose', False)
        # )
        
        logger.info("Starting example script processing")
        logger.debug("This is a debug message")
        
        # Main processing would happen here
        # results = processor.process()
        
        logger.info("Example script completed successfully")
        
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
