#!/usr/bin/env python3
"""
Directory comparison utility script.

This script compares two directories and their subdirectories, providing:
- Directory structure differences
- File count statistics
- Detailed diff output saved to log files
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import subprocess
import tempfile
import os

# Standard COMMON import pattern
common_src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    import logging
    ScriptLogging = None


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
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                self.logger.debug(f"Could not clean up temp file {temp_file}: {e}")
    
    def count_items(self, directory: Path) -> tuple:
        """Count directories and files in a given directory."""
        dir_count = 0
        file_count = 0
        
        try:
            for item in directory.rglob('*'):
                try:
                    if item.is_dir():
                        dir_count += 1
                    elif item.is_file():
                        file_count += 1
                except (OSError, PermissionError) as e:
                    self.logger.debug(f"Cannot access {item}: {e}")
                    self.stats['errors'] += 1
        except (OSError, PermissionError) as e:
            self.logger.error(f"Cannot access directory {directory}: {e}")
            self.stats['errors'] += 1
        
        return dir_count, file_count
    
    def generate_directory_list(self, directory: Path) -> Path:
        """Generate a sorted list of directories and save to temp file."""
        try:
            # Create temporary file for directory list
            temp_fd, temp_path = tempfile.mkstemp(suffix='.txt', prefix=f'diff_{directory.name}_')
            temp_file = Path(temp_path)
            self.temp_files.append(temp_file)
            os.close(temp_fd)  # Close the file descriptor
            
            # Use find command to get directory structure
            cmd = ['find', str(directory), '-type', 'd']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Sort the directories
            directories = sorted(result.stdout.strip().split('\n'))
            
            # Write to temp file
            with open(temp_file, 'w') as f:
                f.write('\n'.join(directories))
            
            self.logger.debug(f"Generated directory list for {directory.name}: {len(directories)} directories")
            return temp_file
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to generate directory list for {directory}: {e}")
            self.stats['errors'] += 1
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error generating directory list for {directory}: {e}")
            self.stats['errors'] += 1
            return None
    
    def perform_comparison(self) -> str:
        """Perform the directory comparison and return detailed results."""
        self.logger.info("Starting directory comparison analysis")
        
        # Count items in both directories
        self.logger.info(f"Analyzing {self.source}...")
        self.stats['source_directories'], self.stats['source_files'] = self.count_items(self.source)
        
        self.logger.info(f"Analyzing {self.target}...")
        self.stats['target_directories'], self.stats['target_files'] = self.count_items(self.target)
        
        # Generate directory structure lists
        self.logger.info("Generating directory structure lists...")
        source_list = self.generate_directory_list(self.source)
        target_list = self.generate_directory_list(self.target)
        
        if not source_list or not target_list:
            return "Error: Could not generate directory lists for comparison"
        
        # Perform diff comparison
        self.logger.info("Performing structure comparison...")
        try:
            diff_cmd = ['diff', '-u', str(source_list), str(target_list)]
            diff_result = subprocess.run(diff_cmd, capture_output=True, text=True)
            
            # Get unique directories
            unique_cmd = ['diff', '--suppress-common-lines', str(source_list), str(target_list)]
            unique_result = subprocess.run(unique_cmd, capture_output=True, text=True)
            
            # Count unique directories
            if unique_result.stdout:
                unique_to_source = len([line for line in unique_result.stdout.split('\n') if line.startswith('<')])
                unique_to_target = len([line for line in unique_result.stdout.split('\n') if line.startswith('>')])
            else:
                unique_to_source = unique_to_target = 0
            
            self.stats['unique_to_source'] = unique_to_source
            self.stats['unique_to_target'] = unique_to_target
            self.stats['common_directories'] = min(self.stats['source_directories'], self.stats['target_directories']) - max(unique_to_source, unique_to_target)
            
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
                unique_lines = [line[2:].strip() for line in unique_result.stdout.split('\n') 
                              if line.startswith('< ') and line.strip()]
                for line in unique_lines[:20]:  # Limit to first 20 for readability
                    report.append(f"  {line}")
                if len(unique_lines) > 20:
                    report.append(f"  ... and {len(unique_lines) - 20} more")
                report.append("")
            
            if unique_to_target > 0:
                report.append(f"Directories in {self.target.name} but NOT in {self.source.name}:")
                unique_lines = [line[2:].strip() for line in unique_result.stdout.split('\n') 
                              if line.startswith('> ') and line.strip()]
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


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare two directories and generate detailed difference reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/source /path/to/target                    # Compare two directories
  %(prog)s --source /path/to/source --target /path/to/target  # Using named arguments
  %(prog)s /path/to/source /path/to/target --debug            # With debug output
        """
    )
    
    # Positional arguments
    parser.add_argument('source', nargs='?',
                       help='Source directory to compare')
    parser.add_argument('target', nargs='?',
                       help='Target directory to compare')
    
    # Named arguments (alternative to positional)
    parser.add_argument('--source', dest='source_named',
                       help='Source directory to compare')
    parser.add_argument('--target', dest='target_named',
                       help='Target directory to compare')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    # Resolve directories: positional takes precedence over named
    if args.source and args.target:
        final_source = args.source
        final_target = args.target
    elif args.source_named and args.target_named:
        final_source = args.source_named
        final_target = args.target_named
    elif args.source and args.target_named:
        final_source = args.source
        final_target = args.target_named
    elif args.source_named and args.target:
        final_source = args.source_named
        final_target = args.target
    else:
        parser.error("Two directories are required for comparison")
    
    # Create a new namespace with resolved values
    final_args = argparse.Namespace()
    final_args.source = Path(final_source)
    final_args.target = Path(final_target)
    final_args.debug = args.debug
    
    return final_args


def main():
    """Main function for the diff script."""
    args = parse_arguments()
    
    # Standard logging setup
    if ScriptLogging:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"diff_{timestamp}",
            debug=args.debug
        )
    else:
        logging.basicConfig(
            level=logging.DEBUG if args.debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger("diff")
    
    # Validate directories
    for dir_path, name in [(args.source, "Source"), (args.target, "Target")]:
        if not dir_path.exists():
            logger.error(f"{name} directory does not exist: {dir_path}")
            return 1
        
        if not dir_path.is_dir():
            logger.error(f"{name} path is not a directory: {dir_path}")
            return 1
    
    # Check if directories are the same
    if args.source.resolve() == args.target.resolve():
        logger.error("Cannot compare a directory with itself")
        return 1
    
    # Start comparison
    logger.info("Starting directory comparison")
    logger.info(f"Source directory: {args.source}")
    logger.info(f"Target directory: {args.target}")
    
    comparator = DirectoryComparator(args.source, args.target, logger)
    
    try:
        # Perform the comparison
        detailed_report = comparator.perform_comparison()
        
        # Print console summary
        comparator.print_summary()
        
        # Save detailed report to log file
        log_dir = Path(".log")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f"diff_{timestamp}.txt"
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(detailed_report)
            
            logger.info(f"Detailed comparison report saved to: {log_file}")
            logger.info(f"Report size: {log_file.stat().st_size:,} bytes")
            
        except Exception as e:
            logger.error(f"Failed to save detailed report: {e}")
            return 1
        
        # Clean up temporary files
        comparator.cleanup_temp_files()
        
        if comparator.stats['errors'] > 0:
            logger.warning("Comparison completed with some errors")
            return 1
        
        logger.info("Directory comparison completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Comparison interrupted by user")
        comparator.cleanup_temp_files()
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during comparison: {e}")
        comparator.cleanup_temp_files()
        return 1


if __name__ == '__main__':
    sys.exit(main())