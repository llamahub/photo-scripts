#!/usr/bin/env python3
"""
Tree utility script for capturing directory structure to a log file.

This script generates a tree view of a directory structure and saves it to a
timestamped log file. Additional arguments are passed through to the tree
command, allowing full control over tree output formatting and filtering.

Usage:
  tree.py /path/to/folder
  tree.py /path/to/folder -L 3 -I '__pycache__|*.pyc'
  tree.py /path/to/folder --charset ascii
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Add src to path for COMMON modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import COMMON framework modules
try:
    from common.logging import ScriptLogging
    from common.argument_parser import (
        ScriptArgumentParser,
        create_standard_arguments,
        merge_arguments
    )
except ImportError as e:
    ScriptLogging = None
    print(f"Warning: COMMON modules not available: {e}")
    sys.exit(1)

# Script metadata
SCRIPT_INFO = {
    'name': 'Tree Utility Script',
    'description': '''Capture directory tree structure to timestamped log file

Generates a tree view of directory structure and saves output to:
  .log/tree_{YYYY-MM-DD_HH-MM-SS}.txt

Additional arguments are passed directly to tree command for formatting,
filtering, and depth control.''',
    'examples': [
        '/path/to/folder',
        '/path/to/folder -L 3',
        '/path/to/folder -I "__pycache__|*.pyc"',
        '/path/to/folder -h --dirsfirst --charset ascii'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'target': {
        'positional': True,
        'help': 'Path to target folder for tree view'
    },
    'tree_args': {
        'flag': '--args',
        'help': 'Additional arguments to pass to tree command (e.g., "-L 3 -I \'__pycache__\'")'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


class TreeCapture:
    """Handles tree generation and file capture."""
    
    def __init__(self, target_path: Path, logger):
        self.target_path = Path(target_path)
        self.logger = logger
        self.log_dir = Path('.log')
        self.log_dir.mkdir(exist_ok=True)
    
    def generate_timestamp(self) -> str:
        """Generate timestamp for log filename."""
        return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    def run_tree(self, additional_args: str = None) -> tuple:
        """
        Run tree command and capture output.
        
        Args:
            additional_args: Additional arguments to pass to tree command
            
        Returns:
            Tuple of (success: bool, output: str, error: str)
        """
        # Build tree command
        cmd = ['tree', str(self.target_path)]
        
        # Parse additional arguments if provided
        if additional_args:
            # Split arguments while respecting quoted strings
            import shlex
            try:
                additional_args_list = shlex.split(additional_args)
                cmd.extend(additional_args_list)
            except ValueError as e:
                return False, "", f"Invalid argument syntax: {e}"
        
        self.logger.debug(f"Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except FileNotFoundError:
            return False, "", "tree command not found. Install with: apt-get install tree"
        except subprocess.TimeoutExpired:
            return False, "", "tree command timed out after 60 seconds"
        except Exception as e:
            return False, "", f"Error running tree: {e}"
    
    def save_to_file(self, output: str) -> Path:
        """Save tree output to timestamped file."""
        timestamp = self.generate_timestamp()
        log_file = self.log_dir / f'tree_{timestamp}.txt'
        
        try:
            with open(log_file, 'w') as f:
                f.write(output)
            self.logger.info(f"Tree output saved to: {log_file}")
            return log_file
        except Exception as e:
            self.logger.error(f"Failed to save output to {log_file}: {e}")
            raise
    
    def capture_tree(self, additional_args: str = None) -> Path:
        """Capture tree and save to file."""
        self.logger.info(f"Generating tree for: {self.target_path}")
        
        # Run tree command
        success, output, error = self.run_tree(additional_args)
        
        if not success:
            self.logger.error(f"tree command failed: {error}")
            raise RuntimeError(f"tree command failed: {error}")
        
        # Save output to file
        log_file = self.save_to_file(output)
        
        return log_file


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
        'target_path': ['target']
    })
    
    # Setup logging with standard handlers
    import logging
    log_dir = Path('.log')
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'tree.log'

    logger = logging.getLogger('tree')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Console handler for stdout (INFO and above)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.addFilter(lambda record: record.levelno == logging.INFO)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # Console handler for stderr (WARNING and above)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    # File handler for all logs (DEBUG and above)
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Display configuration
    config_map = {
        'target_path': 'Target directory',
        'tree_args': 'Tree options'
    }
    parser.display_configuration(resolved_args, config_map)
    
    try:
        # Convert to Path object and validate
        target_path = Path(resolved_args['target_path'])
        
        logger.info("Starting tree capture")
        logger.info(f"Target directory: {target_path}")
        
        # Validate target directory
        if not target_path.exists():
            logger.error(f"Target directory does not exist: {target_path}")
            return 1
        
        if not target_path.is_dir():
            logger.error(f"Target path is not a directory: {target_path}")
            return 1
        
        # Initialize tree capturer
        tree_capture = TreeCapture(target_path, logger)
        
        # Get tree options if provided
        tree_args = resolved_args.get('tree_args', None)
        if tree_args:
            logger.info(f"Using tree options: {tree_args}")
        
        # Capture tree
        output_file = tree_capture.capture_tree(tree_args)
        
        logger.info("Tree capture completed successfully")
        
        if not resolved_args.get('quiet'):
            print(f"✅ Tree output saved to: {output_file}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Tree capture interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during tree capture: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
