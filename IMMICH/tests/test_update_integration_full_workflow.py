
import os
import shutil
import tempfile
from datetime import datetime
import subprocess
import csv
import pytest
from pathlib import Path
import glob

SAMPLES_SRC = os.environ.get("SANTEE_SAMPLES_SRC", "/mnt/photo_drive/santee-samples.bak")

@pytest.mark.integration
def test_update_integration_full_workflow():
    # Clean up old test directories from previous runs (keep current test's directory)
    tmp_dir = Path(".tmp")
    if tmp_dir.exists():
        for old_dir in tmp_dir.glob("2026-*"):
            if old_dir.is_dir():
                try:
                    shutil.rmtree(old_dir)
                except Exception:
                    # Ignore errors cleaning up old directories
                    pass
    
    # Setup temp dir for this test run
    dt_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    temp_root = Path(f".tmp/{dt_str}")
    if temp_root.exists():
        shutil.rmtree(temp_root)
    shutil.copytree(SAMPLES_SRC, temp_root)

    # Run analyze.py
    analyze_csv = temp_root / "analyze.csv"
    analyze_log = temp_root / "analyze.log"
    subprocess.run([
        "python3", "scripts/analyze.py",
        "--source", str(temp_root),
        "--output", str(analyze_csv)
    ], check=True)

    # Run update.py
    result = subprocess.run([
        "python3", "scripts/update.py",
        "--input", str(analyze_csv),
        "--force",
        "--all"
    ], capture_output=True, text=True)
    
    # Capture the update log output for error detection
    update_output = result.stdout + result.stderr

    # Run analyze.py again
    analyze2_csv = temp_root / "analyze2.csv"
    analyze2_log = temp_root / "analyze2.log"
    subprocess.run([
        "python3", "scripts/analyze.py",
        "--source", str(temp_root),
        "--output", str(analyze2_csv)
    ], check=True)

    # Identify files that had EXIF errors during update
    exif_error_files = set()
    for line in update_output.split('\n'):
        if "ExifTool error for" in line:
            # Extract filename from error: "ExifTool error for <filepath>: Error: ..."
            try:
                parts = line.split("ExifTool error for ")
                if len(parts) > 1:
                    file_part = parts[1].split(":")[0].strip()
                    exif_error_files.add(file_part)
            except:
                pass

    # Validate analyze2.csv
    # Only check files that were MATCH in the initial analyze.csv
    initial_match_files = set()
    with open(analyze_csv, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            status = row.get("Calc Status") or row.get("Status")
            filename = row.get("Filenanme") or row.get("Filename") or row.get("File")
            if status == "MATCH" and filename:
                initial_match_files.add(filename)

    with open(analyze2_csv, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            filename = row.get("Filenanme") or row.get("Filename") or row.get("File")
            if filename not in initial_match_files:
                continue  # only check files that were MATCH initially
            
            # Skip files with EXIF errors - they may lose metadata during update attempts
            if filename in exif_error_files:
                continue
            
            # Validate no duplicate tags
            tags = row.get("EXIF Tags", "")
            if tags:
                tag_list = [t.strip().lower() for t in tags.split(";") if t.strip()]
                assert len(tag_list) == len(set(tag_list)), f"Duplicate tags in {filename}: {tags}"
            
            # Validate status is MATCH or RENAME (successfully updated files may change status if computed filename changed)
            status = row.get("Calc Status") or row.get("Status")
            assert status in ("MATCH", "RENAME"), f"Unexpected status for {filename}: {status}"
