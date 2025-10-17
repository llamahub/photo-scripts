#!/usr/bin/env python3
"""
Process dupGuru duplicate detection CSV files.

This script analyzes dupGuru CSV output and fills in missing Action/Comments columns
based on user preferences for duplicate photo management.

Decision Rules:
1. Prefer older files if they're in valid date folders (manually corrected dates)
2. Prefer organized format filenames (YYYY-MM-DD_HHMM_PERSON_DIMxDIM_original.ext)
3. Avoid invalid folder structures (0000-00, NPTSI-Z, "Photos from YYYY", "New Folder")
4. For scanned photos: prefer original scans in _Scans folders over later copies
5. For size differences >50KB: prefer larger file (better quality)
6. For size differences ≤50KB: prefer organized format (just metadata differences)
7. Ensure every group keeps at least one file (safety check)
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# Import from our exif module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class DupGuruProcessor:
    """Process dupGuru CSV files and apply duplicate resolution rules."""
    
    # File size threshold for quality vs metadata differences
    SIZE_THRESHOLD_KB = 50
    
    def __init__(self, input_file, output_file=None, verbose=False):
        """
        Initialize processor.
        
        Args:
            input_file: Path to dupGuru CSV file
            output_file: Path for processed output (auto-generated if None)
            verbose: Enable verbose logging
        """
        self.input_file = input_file
        self.output_file = output_file or self._generate_output_filename()
        self.verbose = verbose
        
        # Statistics tracking
        self.stats = {
            'total_groups': 0,
            'filled_pairs': 0,
            'size_based_decisions': 0,
            'rule_based_decisions': 0,
            'manual_review_needed': 0,
            'safety_fixes': 0
        }
        
        # Decision reason tracking
        self.decision_reasons = Counter()

    def _generate_output_filename(self):
        """Generate output filename based on input filename."""
        input_path = Path(self.input_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Remove existing timestamp or suffix patterns
        base_name = input_path.stem
        base_name = re.sub(r'_\d{8}_\d{4}$', '', base_name)
        base_name = re.sub(r'_actions$', '', base_name)
        base_name = re.sub(r'_filled$', '', base_name)
        base_name = re.sub(r'_fixed$', '', base_name)
        
        return input_path.parent / f"{base_name}_processed_{timestamp}.csv"

    def _log(self, message, level="INFO"):
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[{level}] {message}")

    def extract_date_from_filename(self, filename):
        """Extract date from filename in YYYY-MM-DD format."""
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
        if match:
            try:
                return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                return None
        return None

    def extract_date_from_folder(self, folder_path):
        """Extract date from folder path and determine if it's valid."""
        folder_parts = folder_path.replace('\\', '/').split('/')
        
        for part in folder_parts:
            # Check for YYYY-MM-DD pattern
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', part)
            if match:
                try:
                    date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                    return date, True
                except ValueError:
                    continue
            
            # Check for YYYY-MM pattern
            match = re.search(r'(\d{4})-(\d{2})', part)
            if match:
                try:
                    date = datetime(int(match.group(1)), int(match.group(2)), 1)
                    return date, True
                except ValueError:
                    continue
        
        return None, False

    def is_organized_filename(self, filename):
        """Check if filename follows organize.py target format."""
        pattern = r'\d{4}-\d{2}-\d{2}_\d{4}_[A-Z]+_\d+x\d+_.*\.(jpg|jpeg|png|gif)$'
        return bool(re.match(pattern, filename, re.IGNORECASE))

    def is_invalid_folder(self, folder_path):
        """Check if folder path contains invalid patterns."""
        folder_lower = folder_path.lower()
        invalid_patterns = [
            '0000-00',
            'nptsi',
            'new folder',
            'photos from 20',
        ]
        return any(pattern in folder_lower for pattern in invalid_patterns)

    def is_scanned_file(self, folder_path, filename):
        """Check if this is a scanned file in a _Scans folder."""
        return '_scans' in folder_path.lower()

    def analyze_duplicate_pair(self, file1, file2):
        """Analyze a pair of duplicate files and determine which to keep."""
        
        # Extract key information
        f1_date = self.extract_date_from_filename(file1['Filename'])
        f2_date = self.extract_date_from_filename(file2['Filename'])
        
        f1_folder_date, f1_valid_folder = self.extract_date_from_folder(file1['Folder'])
        f2_folder_date, f2_valid_folder = self.extract_date_from_folder(file2['Folder'])
        
        f1_organized = self.is_organized_filename(file1['Filename'])
        f2_organized = self.is_organized_filename(file2['Filename'])
        
        f1_invalid_folder = self.is_invalid_folder(file1['Folder'])
        f2_invalid_folder = self.is_invalid_folder(file2['Folder'])
        
        f1_scanned = self.is_scanned_file(file1['Folder'], file1['Filename'])
        f2_scanned = self.is_scanned_file(file2['Folder'], file2['Filename'])
        
        f1_size = int(file1['Size (KB)'])
        f2_size = int(file2['Size (KB)'])
        size_diff = abs(f1_size - f2_size)
        
        # Decision logic (order matters - first match wins)
        decisions = []
        
        # Rule 1: Invalid folder structures (highest priority)
        if f1_invalid_folder and not f2_invalid_folder:
            decisions.append(('file2', 'File 1 in invalid folder structure'))
        elif f2_invalid_folder and not f1_invalid_folder:
            decisions.append(('file1', 'File 2 in invalid folder structure'))
        
        # Rule 2: Prefer older files in valid folders (manually corrected dates)
        if f1_date and f2_date and f1_valid_folder and f2_valid_folder:
            if f1_date < f2_date:
                decisions.append(('file1', 'Older file with valid folder structure'))
            elif f2_date < f1_date:
                decisions.append(('file2', 'Older file with valid folder structure'))
        
        # Rule 3: Scanned photos - prefer original scans
        if f1_scanned and not f2_scanned:
            decisions.append(('file1', 'Original scanned file'))
        elif f2_scanned and not f1_scanned:
            decisions.append(('file2', 'Original scanned file'))
        
        # Rule 4: Organized filename format
        if f1_organized and not f2_organized:
            decisions.append(('file1', 'Organized filename format'))
        elif f2_organized and not f1_organized:
            decisions.append(('file2', 'Organized filename format'))
        
        # Rule 5: File size considerations
        if size_diff > self.SIZE_THRESHOLD_KB:  # Significant quality difference
            if f1_size > f2_size:
                decisions.append(('file1', f'Larger file size ({f1_size}KB vs {f2_size}KB, {size_diff}KB difference)'))
            else:
                decisions.append(('file2', f'Larger file size ({f2_size}KB vs {f1_size}KB, {size_diff}KB difference)'))
        
        # Rule 6: Valid folder structure as tiebreaker
        if f1_valid_folder and not f2_valid_folder:
            decisions.append(('file1', 'Valid folder date structure'))
        elif f2_valid_folder and not f1_valid_folder:
            decisions.append(('file2', 'Valid folder date structure'))
        
        # Return the most important decision
        if decisions:
            keep_file, reason = decisions[0]  # First decision has highest priority
            
            # Track decision type for statistics
            if 'size' in reason.lower():
                self.stats['size_based_decisions'] += 1
            else:
                self.stats['rule_based_decisions'] += 1
            
            self.decision_reasons[reason] += 1
            
            if keep_file == 'file1':
                return 'Keep', 'Delete', reason, f'Not keeping: {reason.lower()}'
            else:
                return 'Delete', 'Keep', f'Not keeping: {reason.lower()}', reason
        
        # If no clear decision, need manual review
        self.stats['manual_review_needed'] += 1
        return '', '', 'Manual review needed', 'Manual review needed'

    def calculate_best_file_score(self, row):
        """Calculate a score for a file to determine the best one to keep."""
        score = 0
        
        # Prefer organized filenames
        if self.is_organized_filename(row['Filename']):
            score += 10
        
        # Avoid invalid folders
        if self.is_invalid_folder(row['Folder']):
            score -= 5
        
        # Prefer larger files (quality bonus)
        try:
            size_kb = int(row['Size (KB)'])
            score += size_kb / 100
        except (ValueError, TypeError):
            pass
        
        # Prefer files with valid date folders
        _, valid_folder = self.extract_date_from_folder(row['Folder'])
        if valid_folder:
            score += 5
        
        # Prefer scanned originals
        if self.is_scanned_file(row['Folder'], row['Filename']):
            score += 3
        
        return score

    def ensure_group_safety(self, groups):
        """Ensure every group has at least one 'Keep' decision."""
        safety_fixes = 0
        
        for group_id, group_rows in groups.items():
            actions = [row['Action'].strip() for row in group_rows]
            
            # Check if group needs fixing
            has_keep = 'Keep' in actions
            all_empty = all(action == '' for action in actions)
            
            if not has_keep and not all_empty:
                self._log(f"Safety fix needed for Group {group_id}: {actions}", "WARN")
                safety_fixes += 1
                
                # Find the best file to keep
                best_idx = 0
                best_score = -1
                
                for i, row in enumerate(group_rows):
                    score = self.calculate_best_file_score(row)
                    if score > best_score:
                        best_score = score
                        best_idx = i
                
                # Set the best file to Keep, others to Delete
                for i, row in enumerate(group_rows):
                    if i == best_idx:
                        row['Action'] = 'Keep'
                        if not row['Comments'].strip():
                            row['Comments'] = 'Auto-selected to prevent losing all copies (safety)'
                    else:
                        if row['Action'].strip() not in ['Delete']:
                            row['Action'] = 'Delete'
                            if not row['Comments'].strip():
                                row['Comments'] = 'Not best option in group'
        
        self.stats['safety_fixes'] = safety_fixes
        if safety_fixes > 0:
            self._log(f"Applied {safety_fixes} safety fixes", "INFO")

    def has_existing_actions(self, filepath):
        """Check if CSV file has existing Action/Comments columns with data."""
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                
                # Check if Action/Comments columns exist
                has_action = 'Action' in fieldnames
                has_comments = 'Comments' in fieldnames
                
                if not (has_action and has_comments):
                    return False
                
                # Check if any rows have non-empty actions
                for row in reader:
                    if row.get('Action', '').strip() or row.get('Comments', '').strip():
                        return True
                
                return False
                
        except Exception as e:
            self._log(f"Error checking existing actions: {e}", "ERROR")
            return False

    def process_csv(self):
        """Process the dupGuru CSV file."""
        self._log(f"Processing dupGuru CSV: {self.input_file}")
        
        # Validate input file
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        # Check if file already has actions
        has_existing = self.has_existing_actions(self.input_file)
        if has_existing:
            self._log("File already has Action/Comments data - will preserve existing decisions")
        
        # Read all data
        all_rows = []
        fieldnames = None
        
        try:
            with open(self.input_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames) if reader.fieldnames else []
                
                # Ensure Action and Comments columns exist
                if 'Action' not in fieldnames:
                    fieldnames.append('Action')
                if 'Comments' not in fieldnames:
                    fieldnames.append('Comments')
                
                for row in reader:
                    # Initialize missing columns
                    if 'Action' not in row:
                        row['Action'] = ''
                    if 'Comments' not in row:
                        row['Comments'] = ''
                    all_rows.append(row)
                    
        except Exception as e:
            raise RuntimeError(f"Error reading CSV file: {e}")
        
        if not all_rows:
            raise RuntimeError("No data found in CSV file")
        
        # Group by Group ID
        groups = defaultdict(list)
        for row in all_rows:
            groups[row['Group ID']].append(row)
        
        self.stats['total_groups'] = len(groups)
        self._log(f"Found {len(groups)} duplicate groups")
        
        # Process each group
        for group_id, group_rows in groups.items():
            if len(group_rows) != 2:
                self._log(f"Skipping group {group_id} with {len(group_rows)} files (expected 2)", "WARN")
                continue
            
            file1, file2 = group_rows
            
            # Only fill if both Action fields are empty (preserve existing decisions)
            if not file1['Action'].strip() and not file2['Action'].strip():
                action1, action2, comment1, comment2 = self.analyze_duplicate_pair(file1, file2)
                file1['Action'] = action1
                file1['Comments'] = comment1
                file2['Action'] = action2
                file2['Comments'] = comment2
                self.stats['filled_pairs'] += 1
        
        # Safety check - ensure every group keeps at least one file
        self.ensure_group_safety(groups)
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        
        # Write processed data
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in all_rows:
                    writer.writerow(row)
        except Exception as e:
            raise RuntimeError(f"Error writing output file: {e}")
        
        self._log(f"Output saved to: {self.output_file}")

    def print_statistics(self):
        """Print processing statistics."""
        print(f"DupGuru Processing Results:")
        print(f"  Total groups: {self.stats['total_groups']}")
        print(f"  Pairs processed: {self.stats['filled_pairs']}")
        print(f"  Rule-based decisions: {self.stats['rule_based_decisions']}")
        print(f"  Size-based decisions: {self.stats['size_based_decisions']}")
        print(f"  Manual review needed: {self.stats['manual_review_needed']}")
        print(f"  Safety fixes applied: {self.stats['safety_fixes']}")
        print()
        
        if self.decision_reasons:
            print("Top decision reasons:")
            for reason, count in self.decision_reasons.most_common(10):
                print(f"  {count:4d}: {reason}")

    def verify_safety(self):
        """Verify that no groups will lose all photos."""
        groups_without_keep = 0
        
        try:
            with open(self.output_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                group_actions = defaultdict(list)
                
                for row in reader:
                    group_actions[row['Group ID']].append(row['Action'].strip())
                
                for group_id, actions in group_actions.items():
                    has_keep = 'Keep' in actions
                    all_empty = all(action == '' for action in actions)
                    
                    if not has_keep and not all_empty:
                        groups_without_keep += 1
                        self._log(f"Group {group_id} has no Keep action: {actions}", "ERROR")
                
        except Exception as e:
            self._log(f"Error verifying safety: {e}", "ERROR")
            return False
        
        if groups_without_keep == 0:
            print("✅ Safety verification passed: All groups will keep at least one photo")
            return True
        else:
            print(f"❌ Safety verification failed: {groups_without_keep} groups would lose all photos")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process dupGuru duplicate detection CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dupguru.py duplicates.csv
  python dupguru.py duplicates.csv --output processed_duplicates.csv
  python dupguru.py duplicates.csv --verbose
  python dupguru.py duplicates.csv --no-stats --quiet

Decision Rules (in priority order):
  1. Avoid invalid folder structures (0000-00, NPTSI-Z, etc.)
  2. Prefer older files in valid date folders (manual corrections)
  3. Prefer original scanned files over later copies
  4. Prefer organized filename format (YYYY-MM-DD_HHMM_PERSON_DIMxDIM_*)
  5. Prefer larger files if size difference > 50KB (quality)
  6. Prefer files in valid folder structures as tiebreaker
        """
    )
    
    parser.add_argument("input", help="Input dupGuru CSV file")
    parser.add_argument("--output", "-o", help="Output CSV file (auto-generated if not specified)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--no-stats", action="store_true", help="Don't print statistics")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress all output except errors")
    parser.add_argument("--size-threshold", type=int, default=50, 
                       help="File size difference threshold in KB (default: 50)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # Set verbosity
    verbose = args.verbose and not args.quiet
    
    try:
        # Create processor
        processor = DupGuruProcessor(
            input_file=args.input,
            output_file=args.output,
            verbose=verbose
        )
        
        # Set size threshold if specified
        if args.size_threshold != 50:
            processor.SIZE_THRESHOLD_KB = args.size_threshold
            if verbose:
                print(f"Using size threshold: {args.size_threshold}KB")
        
        if not args.quiet:
            print(f"Processing dupGuru CSV: {args.input}")
            print(f"Output file: {processor.output_file}")
            print()
        
        # Process the file
        processor.process_csv()
        
        # Verify safety
        safety_ok = processor.verify_safety()
        
        # Print statistics
        if not args.no_stats and not args.quiet:
            print()
            processor.print_statistics()
        
        if not safety_ok:
            sys.exit(1)
            
        if not args.quiet:
            print(f"\n✅ Processing complete: {processor.output_file}")
        
    except KeyboardInterrupt:
        print("\n❌ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()