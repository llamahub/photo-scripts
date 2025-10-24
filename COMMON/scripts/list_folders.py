#!/usr/bin/env python3
"""
================================================================================
=== [List Folders Script] - Generate CSV report of folder contents
================================================================================

Scans a source directory recursively and generates a CSV report containing:
- Full path of each subfolder
- Total file count in each folder
- Count of files by extension for each folder

The CSV output includes dynamic columns based on the file extensions found.
Useful for analyzing directory structures and file type distributions.

Example output columns:
Folder, Files, .jpg, .png, .txt, .pdf, etc.

Output file defaults to ./.log/list_folders_{timestamp}.csv
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import csv
from collections import defaultdict

# Add COMMON to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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
    'name': 'List Folders Script',
    'description': '''Generate CSV report of folder contents

Recursively scans source directory and creates CSV report with:
• Full path of each subfolder
• Total file count per folder
• File count by extension per folder

Dynamic columns created based on file extensions found.
Perfect for analyzing directory structure and file distributions.''',
    'examples': [
        '/path/to/source',
        '--source /path/to/source --output report.csv',
        '/path/to/source --output ./reports/folder_analysis.csv'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'source': {
        'positional': True,
        'help': 'Source directory to scan for folders and files'
    },
    'output': {
        'flag': '--output',
        'help': 'Output CSV file path (default: ./.log/list_folders_{timestamp}.csv)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


class FolderLister:
    """Scans directories and generates CSV reports of folder contents by file type."""
    
    def __init__(self, source_dir, output_path=None, logger=None):
        self.source_dir = Path(source_dir)
        self.output_path = output_path
        self.logger = logger or (lambda x: print(x))
        
        # Statistics and data collection
        self.folder_data = {}  # {folder_path: {ext: count, ...}}
        self.all_extensions = set()
        self.stats = {
            'folders_scanned': 0,
            'files_processed': 0,
            'extensions_found': 0,
            'errors': 0
        }
        
        # Generate default output path if not provided
        if not self.output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_dir = Path('./.log')
            log_dir.mkdir(exist_ok=True)
            self.output_path = log_dir / f'list_folders_{timestamp}.csv'
        else:
            self.output_path = Path(self.output_path)
    
    def scan_folder(self, folder_path):
        """Scan a single folder and count files by extension."""
        folder_path = Path(folder_path)
        
        if not folder_path.is_dir():
            return
        
        file_counts = defaultdict(int)
        total_files = 0
        
        try:
            # Count files directly in this folder (not recursive for each folder)
            for item in folder_path.iterdir():
                if item.is_file():
                    total_files += 1
                    ext = item.suffix.lower()
                    if ext:
                        file_counts[ext] += 1
                        self.all_extensions.add(ext)
                    else:
                        # Files without extension
                        file_counts['[no ext]'] += 1
                        self.all_extensions.add('[no ext]')
                    
                    self.stats['files_processed'] += 1
            
            # Store the data for this folder
            self.folder_data[str(folder_path)] = {
                'total_files': total_files,
                'extensions': dict(file_counts)
            }
            
            self.stats['folders_scanned'] += 1
            
            if self.logger:
                self.logger.debug(
                    f"Scanned {folder_path}: {total_files} files, "
                    f"{len(file_counts)} extensions"
                )
                
        except PermissionError as e:
            if self.logger:
                self.logger.warning(f"Permission denied accessing {folder_path}: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error scanning {folder_path}: {e}")
            self.stats['errors'] += 1
    
    def scan_recursively(self, directory):
        """Recursively scan directory and all subdirectories."""
        try:
            # First scan this directory itself
            self.scan_folder(directory)
            
            # Then scan all subdirectories
            for item in directory.iterdir():
                if item.is_dir():
                    self.scan_recursively(item)
                    
        except PermissionError as e:
            if self.logger:
                self.logger.warning(f"Permission denied accessing {directory}: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error scanning directory {directory}: {e}")
            self.stats['errors'] += 1
    
    def generate_csv(self):
        """Generate CSV file with folder data."""
        try:
            # Create output directory if it doesn't exist
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Sort extensions for consistent column order
            sorted_extensions = sorted(self.all_extensions)
            self.stats['extensions_found'] = len(sorted_extensions)
            
            # Create CSV headers
            headers = ['Folder', 'Files'] + sorted_extensions
            
            if self.logger:
                self.logger.info(
                    f"Writing CSV with {len(headers)} columns to {self.output_path}"
                )
            
            with open(self.output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(headers)
                
                # Write data rows
                for folder_path in sorted(self.folder_data.keys()):
                    data = self.folder_data[folder_path]
                    row = [folder_path, data['total_files']]
                    
                    # Add counts for each extension
                    for ext in sorted_extensions:
                        count = data['extensions'].get(ext, 0)
                        row.append(count)
                    
                    writer.writerow(row)
            
            if self.logger:
                self.logger.info(
                    f"CSV report generated successfully: {self.output_path}"
                )
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error generating CSV file: {e}")
            self.stats['errors'] += 1
            raise
    
    def run(self):
        """Main execution method."""
        if not self.source_dir.exists():
            raise ValueError(f"Source directory does not exist: {self.source_dir}")
        
        if not self.source_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {self.source_dir}")
        
        if self.logger:
            self.logger.info("Starting folder listing process")
            self.logger.info(f"Source: {self.source_dir}")
            self.logger.info(f"Output: {self.output_path}")
        
        # Scan all folders
        self.scan_recursively(self.source_dir)
        
        # Generate CSV report
        self.generate_csv()
        
        if self.logger:
            self.logger.info("Folder listing process completed")
    
    def get_stats(self):
        """Return processing statistics."""
        return self.stats.copy()


def main():
    """Main entry point with consistent argument parsing and structure."""
    
    # Create argument parser
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    
    # Print standardized header
    parser.print_header()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate and resolve required arguments
    try:
        resolved_args = parser.validate_required_args(args, {
            'source_dir': ['source_file', 'source']
        })
    except SystemExit:
        # Handle missing arguments
        source = getattr(args, 'source_file', None) or getattr(args, 'source', None)
        
        if not source:
            print("source directory is required", file=sys.stderr)
            sys.exit(1)
    
    # Setup logging with consistent pattern

    logger = parser.setup_logging(resolved_args, "list_folders")
    
    # Display configuration
    config_map = {
        'source_dir': 'Source directory'
    }
    parser.display_configuration(resolved_args, config_map)
    
    # Additional configuration display
    output_path = resolved_args.get('output')
    if not resolved_args.get('quiet'):
        if output_path:
            print(f"Output file: {output_path}")
        else:
            print("Output file: ./.log/list_folders_{timestamp}.csv (auto-generated)")
        print()
    
    try:
        # Initialize FolderLister with resolved arguments
        logger.info("Initializing FolderLister")
        logger.info(f"Source: {resolved_args['source_dir']}")
        logger.info(f"Output: {output_path or 'auto-generated'}")
        
        lister = FolderLister(
            source_dir=resolved_args['source_dir'],
            output_path=output_path,
            logger=logger
        )
        
        logger.info("Starting folder listing process")
        
        # Show startup message to stdout
        if not resolved_args.get('quiet'):
            print(f"🚀 Starting folder scan of {resolved_args['source_dir']}")
        
        # Run the listing process
        lister.run()
        
        # Get and log final statistics
        stats = lister.get_stats()
        logger.info("Folder listing completed successfully")
        logger.info(f"Folders scanned: {stats.get('folders_scanned', 0)}")
        logger.info(f"Files processed: {stats.get('files_processed', 0)}")
        logger.info(f"Extensions found: {stats.get('extensions_found', 0)}")
        logger.info(f"Errors encountered: {stats.get('errors', 0)}")
        
        # Show clean summary
        if not resolved_args.get('quiet'):
            print()
            print("=" * 60)
            print("✅ FOLDER LISTING COMPLETE")
            print("=" * 60)
            print("📊 Summary:")
            print(f"   • Folders scanned: {stats.get('folders_scanned', 0)}")
            print(f"   • Files processed: {stats.get('files_processed', 0)}")
            print(f"   • Extensions found: {stats.get('extensions_found', 0)}")
            if stats.get('errors', 0) > 0:
                print(
                    f"   ⚠️  Errors: {stats.get('errors', 0)} "
                    "(check log for details)"
                )
            print(f"📄 CSV Report: {lister.output_path}")
            # Find the log file path from file handlers
            log_file = "N/A"
            for handler in logger.handlers:
                if hasattr(handler, 'baseFilename'):
                    log_file = handler.baseFilename
                    break
            print(f"📋 Detailed log: {log_file}")
            print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during folder listing: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())