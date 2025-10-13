#!/usr/bin/env python3
"""
Space utility script for analyzing disk space usage.

This script shows disk space usage and availability for directories,
with optional tree view to show space usage of subdirectories.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import os
import shutil

# Standard COMMON import pattern
common_src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    import logging
    ScriptLogging = None


class SpaceAnalyzer:
    """Handles space analysis operations for directories."""
    
    def __init__(self, source_path: Path, logger):
        self.source_path = Path(source_path)
        self.logger = logger
        self.stats = {
            'total_size': 0,
            'directories_analyzed': 0,
            'files_analyzed': 0,
            'errors': 0
        }
    
    def format_bytes(self, bytes_value: int) -> str:
        """Convert bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if bytes_value < 1024.0:
                if unit == 'B':
                    return f"{bytes_value:,.0f} {unit}"
                else:
                    return f"{bytes_value:,.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:,.1f} EB"
    
    def get_directory_size(self, path: Path) -> int:
        """Calculate total size of directory and all its contents."""
        total_size = 0
        try:
            for item in path.rglob('*'):
                try:
                    if item.is_file():
                        total_size += item.stat().st_size
                        self.stats['files_analyzed'] += 1
                    elif item.is_dir():
                        self.stats['directories_analyzed'] += 1
                except (OSError, PermissionError) as e:
                    self.logger.debug(f"Cannot access {item}: {e}")
                    self.stats['errors'] += 1
        except (OSError, PermissionError) as e:
            self.logger.error(f"Cannot access directory {path}: {e}")
            self.stats['errors'] += 1
        
        return total_size
    
    def get_disk_usage(self, path: Path) -> tuple:
        """Get disk usage statistics for the filesystem containing the path."""
        try:
            usage = shutil.disk_usage(path)
            return usage.total, usage.used, usage.free
        except OSError as e:
            self.logger.error(f"Cannot get disk usage for {path}: {e}")
            return 0, 0, 0
    
    def analyze_basic_space(self) -> None:
        """Analyze and display basic space information."""
        self.logger.info(f"Analyzing space usage for: {self.source_path}")
        
        # Get directory size
        directory_size = self.get_directory_size(self.source_path)
        self.stats['total_size'] = directory_size
        
        # Get filesystem usage
        total_disk, used_disk, free_disk = self.get_disk_usage(self.source_path)
        
        # Display results
        self.logger.info("=" * 60)
        self.logger.info("SPACE ANALYSIS SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Directory: {self.source_path}")
        self.logger.info(f"Directory size: {self.format_bytes(directory_size)}")
        
        if total_disk > 0:
            self.logger.info("-" * 40)
            self.logger.info("FILESYSTEM INFORMATION")
            self.logger.info("-" * 40)
            self.logger.info(f"Total disk space: {self.format_bytes(total_disk)}")
            self.logger.info(f"Used disk space: {self.format_bytes(used_disk)}")
            self.logger.info(f"Available space: {self.format_bytes(free_disk)}")
            
            # Calculate percentages
            used_percent = (used_disk / total_disk) * 100
            free_percent = (free_disk / total_disk) * 100
            directory_percent = (directory_size / total_disk) * 100
            
            self.logger.info(f"Used: {used_percent:.1f}%")
            self.logger.info(f"Available: {free_percent:.1f}%")
            self.logger.info(f"This directory: {directory_percent:.2f}% of total disk")
        
        self.logger.info("=" * 60)
    
    def get_subdirectory_sizes(self, path: Path, max_depth: int, current_depth: int = 1) -> list:
        """Get sizes of subdirectories up to specified depth."""
        subdirs = []
        
        if current_depth > max_depth:
            return subdirs
        
        try:
            # Get immediate subdirectories
            for item in path.iterdir():
                if item.is_dir():
                    try:
                        # Calculate size of this subdirectory
                        size = self.get_directory_size(item)
                        
                        subdir_info = {
                            'path': item,
                            'size': size,
                            'depth': current_depth,
                            'subdirs': []
                        }
                        
                        # Recursively get subdirectories if we haven't reached max depth
                        if current_depth < max_depth:
                            subdir_info['subdirs'] = self.get_subdirectory_sizes(
                                item, max_depth, current_depth + 1
                            )
                        
                        subdirs.append(subdir_info)
                        
                    except (OSError, PermissionError) as e:
                        self.logger.debug(f"Cannot access subdirectory {item}: {e}")
                        self.stats['errors'] += 1
                        
        except (OSError, PermissionError) as e:
            self.logger.error(f"Cannot list directory {path}: {e}")
            self.stats['errors'] += 1
        
        # Sort by size (largest first)
        subdirs.sort(key=lambda x: x['size'], reverse=True)
        return subdirs
    
    def print_tree_view(self, subdirs: list, indent: str = "", current_level: int = 1) -> None:
        """Print tree view of subdirectories with sizes."""
        for i, subdir in enumerate(subdirs):
            # Create visual tree structure
            is_last = i == len(subdirs) - 1
            
            if indent == "":
                # Root level directories
                tree_char = "├── " if not is_last else "└── "
                next_indent = "│   " if not is_last else "    "
            else:
                tree_char = "├── " if not is_last else "└── "
                next_indent = indent + ("│   " if not is_last else "    ")
            
            size_str = self.format_bytes(subdir['size'])
            
            # Single line format: directory name and size
            self.logger.info(f"{indent}{tree_char}{subdir['path'].name}/ ({size_str})")
            
            # Print subdirectories with increased indentation
            if subdir['subdirs']:
                self.print_tree_view(subdir['subdirs'], next_indent, current_level + 1)
    
    def analyze_tree_space(self, levels: int) -> None:
        """Analyze and display tree view of space usage."""
        self.logger.info(f"Analyzing directory tree (depth: {levels}) for: {self.source_path}")
        
        # Get root directory size first
        root_size = self.get_directory_size(self.source_path)
        self.stats['total_size'] = root_size
        
        # Get subdirectory information
        subdirs = self.get_subdirectory_sizes(self.source_path, levels)
        
        # Display results
        self.logger.info("=" * 60)
        self.logger.info(f"DIRECTORY TREE ANALYSIS (Depth: {levels})")
        self.logger.info("=" * 60)
        self.logger.info(f"Root: {self.source_path.name}/")
        self.logger.info(f"    Total Size: {self.format_bytes(root_size)}")
        
        if subdirs:
            self.logger.info("")
            self.logger.info("Subdirectories (sorted by size):")
            self.logger.info("-" * 40)
            self.print_tree_view(subdirs)
        else:
            self.logger.info("No accessible subdirectories found")
        
        self.logger.info("=" * 60)
    
    def print_summary(self) -> None:
        """Print analysis summary statistics."""
        self.logger.info("ANALYSIS STATISTICS")
        self.logger.info("-" * 30)
        self.logger.info(f"Total size analyzed: {self.format_bytes(self.stats['total_size'])}")
        self.logger.info(f"Directories analyzed: {self.stats['directories_analyzed']:,}")
        self.logger.info(f"Files analyzed: {self.stats['files_analyzed']:,}")
        if self.stats['errors'] > 0:
            self.logger.warning(f"Access errors: {self.stats['errors']}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze disk space usage for directories with optional tree view",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/folder                    # Basic space analysis
  %(prog)s --source /path/to/folder          # Using named argument
  %(prog)s /path/to/folder --tree            # Show tree view (1 level default)
  %(prog)s /path/to/folder --tree --levels 2 # Show tree view with 2 levels
        """
    )
    
    # Positional argument (also available as named)
    parser.add_argument('source', nargs='?',
                       help='Path to source directory to analyze')
    
    # Named arguments
    parser.add_argument('--source', dest='source_named',
                       help='Path to source directory to analyze')
    parser.add_argument('--tree', action='store_true',
                       help='Show tree view of subdirectory space usage')
    parser.add_argument('--levels', type=int, default=1,
                       help='Number of directory levels to show in tree view (default: 1)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    # Resolve source: positional takes precedence over named
    if args.source:
        final_source = args.source
    elif args.source_named:
        final_source = args.source_named
    else:
        parser.error("Source directory is required (provide as positional argument or --source)")
    
    # Create a new namespace with resolved values
    final_args = argparse.Namespace()
    final_args.source = Path(final_source)
    final_args.tree = args.tree
    final_args.levels = args.levels
    final_args.debug = args.debug
    
    return final_args


def main():
    """Main function for the space script."""
    args = parse_arguments()
    
    # Standard logging setup
    if ScriptLogging:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"space_{timestamp}",
            debug=args.debug
        )
    else:
        logging.basicConfig(
            level=logging.DEBUG if args.debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger("space")
    
    # Validate source directory
    if not args.source.exists():
        logger.error(f"Source directory does not exist: {args.source}")
        return 1
    
    if not args.source.is_dir():
        logger.error(f"Source path is not a directory: {args.source}")
        return 1
    
    # Validate levels argument
    if args.levels < 1:
        logger.error("Levels must be 1 or greater")
        return 1
    
    # Start analysis
    logger.info("Starting space analysis")
    logger.info(f"Source directory: {args.source}")
    
    if args.tree:
        logger.info(f"Tree view enabled (levels: {args.levels})")
    
    analyzer = SpaceAnalyzer(args.source, logger)
    
    try:
        if args.tree:
            analyzer.analyze_tree_space(args.levels)
        else:
            analyzer.analyze_basic_space()
        
        # Print summary statistics
        analyzer.print_summary()
        
        if analyzer.stats['errors'] > 0:
            logger.warning("Analysis completed with some access errors")
            return 1
        
        logger.info("Space analysis completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Analysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())