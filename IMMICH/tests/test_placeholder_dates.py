#!/usr/bin/env python3
"""
Test for placeholder date fix in ImageUpdater.

Tests the complete workflow:
1. Analyze: Files in YYYY-00 folders with placeholder dates
2. Mark: Select all files for update  
3. Update: Apply EXIF updates (which should recalculate paths)
4. Analyze: Verify all files now show MATCH status in correct folders

These 9 files simulate the real-world scenario where files with unknown 
month/day were stored in YYYY-00-00 folders, then had their EXIF dates 
updated to real values. The fix ensures the files get moved to the 
correct YYYY-MM folders after EXIF update.
"""

import csv
import sys
from pathlib import Path
import subprocess
import tempfile
from typing import List, Dict


def run_analyze(fixture_dir: str) -> str:
    """Run analyze on fixture directory, return CSV path."""
    print("  Running analyze...")
    result = subprocess.run(
        ["python3", "-m", "scripts.analyze", fixture_dir],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Analyze failed: {result.stderr}")
    
    # Find the most recent CSV file created
    log_dir = Path(__file__).parent.parent / ".log"
    csv_files = sorted(log_dir.glob("analyze_*.csv"))
    if not csv_files:
        raise RuntimeError("No analyze CSV files found")
    
    return str(csv_files[-1])


def mark_selected(csv_file: str, output_file: str) -> None:
    """Mark all rows as selected in CSV."""
    print(f"  Marking all files as selected...")
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    for row in rows:
        row['Select'] = 'yes'
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"  ✓ Marked {len(rows)} files")


def run_update(csv_file: str) -> None:
    """Run update script on CSV file."""
    print("  Running update...")
    result = subprocess.run(
        ["python3", "-m", "scripts.update", csv_file],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    if result.returncode != 0:
        print(f"Update stderr: {result.stderr}")
    
    # Count files processed
    lines = result.stdout.split('\n')
    audit_lines = [l for l in lines if 'AUDIT file=' in l]
    print(f"  ✓ Updated {len(audit_lines)} files")


def check_results(csv_file: str, expected_count: int) -> bool:
    """Check analyze results."""
    print(f"  Checking results...")
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    status_counts: Dict[str, int] = {}
    for row in rows:
        status = row['Calc Status'].strip()
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"    Status distribution:")
    for status, count in sorted(status_counts.items()):
        print(f"      {status}: {count}")
    
    # Check if all our test files are MATCH
    match_count = status_counts.get('MATCH', 0)
    if match_count >= expected_count:
        print(f"    ✓ All {expected_count} test files are MATCH")
        return True
    else:
        move_count = status_counts.get('MOVE', 0)
        print(f"    ✗ {move_count} files still MOVE (expected 0)")
        
        # Show which files are MOVE
        if move_count > 0:
            print(f"\n    Files still marked MOVE:")
            for row in rows:
                if row['Calc Status'].strip() == 'MOVE':
                    fname = Path(row['Filenanme']).name
                    print(f"      - {fname}")
        
        return False


def main():
    """Run the complete test workflow."""
    fixture_dir = Path(__file__).parent / "fixtures" / "placeholder_dates"
    if not fixture_dir.exists():
        print(f"✗ Test fixture not found at {fixture_dir}")
        return False
    
    print("\n" + "=" * 80)
    print("TEST: Placeholder Date Fix (ImageUpdater path recalculation)")
    print("=" * 80)
    print(f"\nFixture: {fixture_dir}")
    print(f"Test files: 9 images with placeholder dates in YYYY-00 folders\n")
    
    try:
        # STEP 1: Analyze
        print("STEP 1: Initial analyze...")
        csv_before = run_analyze(str(fixture_dir))
        print(f"  ✓ {Path(csv_before).name}")
        
        # STEP 2: Mark selected
        print("\nSTEP 2: Mark files for update...")
        csv_selected = csv_before.replace('.csv', '_selected.csv')
        mark_selected(csv_before, csv_selected)
        
        # STEP 3: Update
        print("\nSTEP 3: Update EXIF and recalculate paths...")
        run_update(csv_selected)
        
        # STEP 4: Analyze again
        print("\nSTEP 4: Final analyze...")
        csv_after = run_analyze(str(fixture_dir))
        print(f"  ✓ {Path(csv_after).name}")
        
        # STEP 5: Check results
        print("\nSTEP 5: Verify all files marked MATCH...")
        all_match = check_results(csv_after, expected_count=9)
        
        print("\n" + "=" * 80)
        if all_match:
            print("✓ TEST PASSED")
            print("  All 9 placeholder-date files were correctly moved to YYYY-MM folders")
            print("=" * 80 + "\n")
            return True
        else:
            print("✗ TEST FAILED")
            print("  Some files still show MOVE status after update")
            print("  Path recalculation logic may not be working correctly")
            print("=" * 80 + "\n")
            return False
            
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}")
        print("=" * 80 + "\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
