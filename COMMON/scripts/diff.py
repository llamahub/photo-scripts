#!/usr/bin/env python3
"""
================================================================================
=== [Directory Comparison Script] - Compare directories and generate reports
================================================================================

This script compares two directories and their subdirectories, providing:
- Directory structure differences
- File count statistics
- Detailed diff output saved to log files

The comparison generates comprehensive reports showing structural differences,
unique directories, and statistics for both source and target directories.
"""

import sys
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

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
    'name': 'Directory Comparison Script',
    'description': '''Compare two directories and generate detailed difference reports

Compares directory structures, counts files and directories, and generates
comprehensive reports showing:
- Directory structure differences
- File count statistics
- Unique directories in each location
- Detailed diff output''',
    'examples': [
        '/path/to/source /path/to/target',
        '--source /path/to/source --target /path/to/target',
        '/path/to/source /path/to/target --debug'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'source': {
        'positional': True,
        'help': 'Source directory to compare'
    },
    'target': {
        'positional': True,
        'help': 'Target directory to compare'
    },
    'debug': {
        'flag': '--debug',
        'action': 'store_true',
        'help': 'Enable debug output (alias for --verbose)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


class DirectoryComparator:
    """Handles directory comparison operations."""
    
    def __init__(self, source: Path, target: Path, logger):
        self.source = Path(source)
        self.target = Path(target)
        self.logger = logger
        self.stats = {
            'source_directories': 0,
            'source_files': 0,
            'target_directories': 0,
            'target_files': 0,
            'unique_to_source': 0,
            'unique_to_target': 0,
            'common_directories': 0,
            'errors': 0
        }
        self.temp_files = []
    
    def cleanup_temp_files(self):
        """Clean up temporary files created during comparison."""
        self.logger.debug("Cleaning up temporary files")
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    self.logger.debug(f"Removed temporary file: {temp_file}")
            except Exception as e:
                self.logger.warning(f"Failed to remove temporary file {temp_file}: {e}")
        self.temp_files = []
    
    def _create_directory_listing(self, directory: Path) -> Path:
        """Create a sorted listing of directories for comparison."""
        self.logger.debug(f"Creating directory listing for {directory}")
        
        temp_file = Path(tempfile.mktemp(suffix='.txt'))
        self.temp_files.append(temp_file)
        
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                for item in sorted(directory.rglob('*')):
                    if item.is_dir():
                        # Use relative path for comparison
                        relative_path = item.relative_to(directory)
                        f.write(f"{relative_path}/\n")
            
            self.logger.debug(f"Directory listing created: {temp_file}")
            return temp_file
            
        except Exception as e:
            error_msg = f"Failed to create directory listing for {directory}: {e}"
            self.logger.error(error_msg)
            self.stats['errors'] += 1
            raise
    
    def _count_items(self, directory: Path, item_type: str) -> int:
        """Count directories or files in a directory tree."""
        count = 0
        try:
            if item_type == 'directories':
                for item in directory.rglob('*'):
                    if item.is_dir():
                        count += 1
            elif item_type == 'files':
                for item in directory.rglob('*'):
                    if item.is_file():
                        count += 1
        except Exception as e:
            self.logger.warning(f"Error counting {item_type} in {directory}: {e}")
            self.stats['errors'] += 1
        
        return count
    
    def perform_comparison(self) -> str:
        """Perform the directory comparison and return detailed report."""
        try:
            self.logger.info("Starting directory structure comparison")
            
            # Update statistics with accurate counts
            self.stats['source_directories'] = self._count_items(
                self.source, 'directories')
            self.stats['source_files'] = self._count_items(self.source, 'files')
            self.stats['target_directories'] = self._count_items(
                self.target, 'directories')
            self.stats['target_files'] = self._count_items(self.target, 'files')
            
            src_dirs = self.stats['source_directories']
            src_files = self.stats['source_files']
            tgt_dirs = self.stats['target_directories']
            tgt_files = self.stats['target_files']
            
            self.logger.info(f"Source: {src_dirs} dirs, {src_files} files")
            self.logger.info(f"Target: {tgt_dirs} dirs, {tgt_files} files")
            
            # Create directory listings for comparison
            source_listing = self._create_directory_listing(self.source)
            target_listing = self._create_directory_listing(self.target)
            
            # Use diff to compare directory structures
            diff_cmd = ['diff', '-u', str(source_listing), str(target_listing)]
            self.logger.debug(f"Running diff command: {' '.join(diff_cmd)}")
            
            diff_result = subprocess.run(
                diff_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            # Count unique directories using diff
            unique_cmd = [
                'diff', '--old-line-format=%L', '--new-line-format=',
                '--unchanged-line-format=', str(source_listing), str(target_listing)
            ]
            unique_result = subprocess.run(
                unique_cmd, capture_output=True, text=True, encoding='utf-8')
            lines = [line for line in unique_result.stdout.split('\n')
                     if line.strip()]
            unique_to_source = len(lines)
            
            unique_cmd = [
                'diff', '--old-line-format=', '--new-line-format=%L',
                '--unchanged-line-format=', str(source_listing), str(target_listing)
            ]
            unique_result = subprocess.run(
                unique_cmd, capture_output=True, text=True, encoding='utf-8')
            lines = [line for line in unique_result.stdout.split('\n')
                     if line.strip()]
            unique_to_target = len(lines)
            
            self.stats['unique_to_source'] = unique_to_source
            self.stats['unique_to_target'] = unique_to_target
            
            min_dirs = min(self.stats['source_directories'],
                           self.stats['target_directories'])
            max_unique = max(unique_to_source, unique_to_target)
            self.stats['common_directories'] = min_dirs - max_unique
            
            # Generate comprehensive report
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            report = []
            report.append("=" * 70)
            report.append("DIRECTORY STRUCTURE COMPARISON REPORT")
            report.append(f"Generated: {timestamp}")
            report.append("=" * 70)
            report.append("")
            report.append(f"Source directory: {self.source}")
            report.append(f"Target directory: {self.target}")
            report.append("")
            
            # Statistics section
            report.append("--- DIRECTORY STATISTICS ---")
            report.append(f"{self.source.name}:")
            report.append(f"  Directories: {self.stats['source_directories']:,}")
            report.append(f"  Files: {self.stats['source_files']:,}")
            report.append("")
            report.append(f"{self.target.name}:")
            report.append(f"  Directories: {self.stats['target_directories']:,}")
            report.append(f"  Files: {self.stats['target_files']:,}")
            report.append("")
            
            # Difference summary
            dir_diff = self.stats['target_directories'] - self.stats['source_directories']
            file_diff = self.stats['target_files'] - self.stats['source_files']
            report.append("--- DIFFERENCE SUMMARY ---")
            report.append(f"Directory difference: {dir_diff:+,} ({self.target.name} vs {self.source.name})")
            report.append(f"File difference: {file_diff:+,} ({self.target.name} vs {self.source.name})")
            report.append("")
            report.append(f"Directories unique to {self.source.name}: {unique_to_source:,}")
            report.append(f"Directories unique to {self.target.name}: {unique_to_target:,}")
            report.append("")
            
            # Structure differences section
            report.append("--- STRUCTURE DIFFERENCES ---")
            if unique_to_source > 0:
                report.append(f"Directories in {self.source.name} but NOT in {self.target.name}:")
                # Parse unified diff format: lines starting with '-' are only in source
                unique_lines = [line[1:].strip() for line in diff_result.stdout.split('\n') 
                              if line.startswith('-') and not line.startswith('---') and line.strip()]
                for line in unique_lines[:20]:  # Limit to first 20 for readability
                    report.append(f"  {line}")
                if len(unique_lines) > 20:
                    report.append(f"  ... and {len(unique_lines) - 20} more")
                report.append("")
            
            if unique_to_target > 0:
                report.append(f"Directories in {self.target.name} but NOT in {self.source.name}:")
                # Parse unified diff format: lines starting with '+' are only in target
                unique_lines = [line[1:].strip() for line in diff_result.stdout.split('\n') 
                              if line.startswith('+') and not line.startswith('+++') and line.strip()]
                for line in unique_lines[:20]:  # Limit to first 20 for readability
                    report.append(f"  {line}")
                if len(unique_lines) > 20:
                    report.append(f"  ... and {len(unique_lines) - 20} more")
                report.append("")
            
            if unique_to_source == 0 and unique_to_target == 0:
                report.append("No structural differences found - directories have identical structure")
                report.append("")
            
            # Detailed diff section
            report.append("--- DETAILED DIRECTORY DIFF ---")
            if diff_result.stdout:
                report.append(diff_result.stdout)
            else:
                report.append("No differences in directory structure")
            
            report.append("")
            report.append("=" * 70)
            report.append("END OF COMPARISON REPORT")
            report.append("=" * 70)
            
            return '\n'.join(report)
            
        except Exception as e:
            self.logger.error(f"Error during comparison: {e}")
            self.stats['errors'] += 1
            return f"Error: Failed to perform directory comparison: {e}"
    
    def print_summary(self) -> None:
        """Print comparison summary statistics."""
        self.logger.info("=" * 60)
        self.logger.info("COMPARISON SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"{self.source.name}: {self.stats['source_directories']:,} dirs, {self.stats['source_files']:,} files")
        self.logger.info(f"{self.target.name}: {self.stats['target_directories']:,} dirs, {self.stats['target_files']:,} files")
        
        dir_diff = self.stats['target_directories'] - self.stats['source_directories']
        file_diff = self.stats['target_files'] - self.stats['source_files']
        
        self.logger.info(f"Difference: {dir_diff:+,} dirs, {file_diff:+,} files")
        self.logger.info(f"Unique to {self.source.name}: {self.stats['unique_to_source']:,} directories")
        self.logger.info(f"Unique to {self.target.name}: {self.stats['unique_to_target']:,} directories")
        
        if self.stats['errors'] > 0:
            self.logger.warning(f"Errors encountered: {self.stats['errors']}")
        
        self.logger.info("=" * 60)


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
        'source_directory': ['source_file', 'source'],
        'target_directory': ['target_file', 'target']
    })
    
    # Setup logging with consistent pattern
    debug_mode = resolved_args.get('verbose') or resolved_args.get('debug')
    logger = parser.setup_logging(resolved_args, "diff_script")
    
    # Display configuration with diff-specific labels
    config_map = {
        'source_directory': 'Source directory',
        'target_directory': 'Target directory'
    }
    parser.display_configuration(resolved_args, config_map)
    
    try:
        # Convert to Path objects
        source_path = Path(resolved_args['source_directory'])
        target_path = Path(resolved_args['target_directory'])
        
        logger.info("Starting directory comparison")
        logger.info(f"Source directory: {source_path}")
        logger.info(f"Target directory: {target_path}")
        
        # Validate directories
        for dir_path, name in [(source_path, "Source"), (target_path, "Target")]:
            if not dir_path.exists():
                error_msg = f"{name} directory does not exist: {dir_path}"
                logger.error(error_msg)
                if not resolved_args.get('quiet'):
                    print(f"❌ Error: {error_msg}")
                return 1
            
            if not dir_path.is_dir():
                error_msg = f"{name} path is not a directory: {dir_path}"
                logger.error(error_msg)
                if not resolved_args.get('quiet'):
                    print(f"❌ Error: {error_msg}")
                return 1
        
        # Check if directories are the same
        if source_path.resolve() == target_path.resolve():
            error_msg = "Cannot compare a directory with itself"
            logger.error(error_msg)
            if not resolved_args.get('quiet'):
                print(f"❌ Error: {error_msg}")
            return 1
        
        # Initialize comparator and perform comparison
        comparator = DirectoryComparator(source_path, target_path, logger)
        
        # Perform the comparison
        detailed_report = comparator.perform_comparison()
        
        # Print summary statistics
        comparator.print_summary()
        
        # Save detailed report to log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = Path(f"diff_report_{timestamp}.log")
        
        logger.info(f"Saving detailed report to: {log_file}")
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(detailed_report)
        
        logger.info("Directory comparison completed successfully")
        
        if not resolved_args.get('quiet'):
            print("✅ Directory comparison completed successfully")
            print(f"Detailed report saved to: {log_file}")
            
            # Print summary stats
            stats = comparator.stats
            print(f"\nSummary:")
            print(f"  {source_path.name}: {stats['source_directories']:,} dirs, {stats['source_files']:,} files")
            print(f"  {target_path.name}: {stats['target_directories']:,} dirs, {stats['target_files']:,} files")
            
            dir_diff = stats['target_directories'] - stats['source_directories']
            file_diff = stats['target_files'] - stats['source_files']
            print(f"  Difference: {dir_diff:+,} dirs, {file_diff:+,} files")
            
            if stats['unique_to_source'] > 0 or stats['unique_to_target'] > 0:
                print(f"  Unique to {source_path.name}: {stats['unique_to_source']:,} directories")
                print(f"  Unique to {target_path.name}: {stats['unique_to_target']:,} directories")
        
        # Cleanup temporary files
        comparator.cleanup_temp_files()
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Comparison interrupted by user")
        if 'comparator' in locals():
            comparator.cleanup_temp_files()
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during comparison: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        if 'comparator' in locals():
            comparator.cleanup_temp_files()
        return 1


if __name__ == '__main__':
    sys.exit(main())