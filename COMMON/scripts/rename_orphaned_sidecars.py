#!/usr/bin/env python3
"""
Rename orphaned sidecar files to match their corresponding image files.
Uses pattern matching and confidence scoring to determine matches.
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from difflib import SequenceMatcher

# Image extensions
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.heic', '.heif', '.webp', '.cr2', '.nef', '.arw', '.dng', '.raw'
}

# Sidecar extensions
SIDECAR_EXTENSIONS = {'.xmp', '.json'}


def extract_metadata_from_filename(filename):
    """Extract date, time, dimensions, and camera info from filename."""
    stem = Path(filename).stem
    
    metadata = {
        'date': None,
        'time': None,
        'dimensions': None,
        'camera_id': None,
        'original_name': stem
    }
    
    # Extract date patterns (YYYY-MM-DD, YYYY_MM_DD, YYYYMMDD)
    date_match = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', stem)
    if date_match:
        metadata['date'] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
    
    # Extract time patterns (HHMM, HH:MM, HHMMSS)
    time_match = re.search(r'[-_](\d{4}|\d{6})(?=[-_]|$)', stem)
    if time_match:
        metadata['time'] = time_match.group(1)
    
    # Extract dimensions (WIDTHxHEIGHT)
    dim_match = re.search(r'(\d{3,5})x(\d{3,5})', stem)
    if dim_match:
        metadata['dimensions'] = f"{dim_match.group(1)}x{dim_match.group(2)}"
    
    # Extract camera ID patterns (DSC, IMG, DSCN, etc.)
    camera_match = re.search(r'(DSC|IMG|DSCN|IMGP|P\d{7}|IMG_E)_?(\d{4,5})', stem, re.IGNORECASE)
    if camera_match:
        metadata['camera_id'] = camera_match.group(0).upper()
    
    return metadata


def calculate_match_confidence(sidecar_name, image_name, sidecar_ext):
    """
    Calculate confidence score (0-100) that a sidecar matches an image.
    Higher score = more confident match.
    """
    confidence = 0
    reasons = []
    
    # Remove extensions for comparison
    sidecar_stem = Path(sidecar_name).stem
    image_stem = Path(image_name).stem
    
    # Handle .json files that might have double extensions like .JPG.supplemental-metadata.json
    if sidecar_ext == '.json':
        # Remove common JSON metadata suffixes
        json_suffixes = ['.supplemental-metadata', '.supplemental', '.supplemental-metada', '.metadata']
        for suffix in json_suffixes:
            if sidecar_stem.lower().endswith(suffix):
                sidecar_stem = sidecar_stem[:-len(suffix)]
                break
        
        # Remove image extension if present in sidecar name
        for img_ext in ['.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff']:
            if sidecar_stem.lower().endswith(img_ext):
                sidecar_stem = sidecar_stem[:-len(img_ext)]
                break
    
    # Exact match (after normalization)
    if sidecar_stem.lower() == image_stem.lower():
        confidence = 100
        reasons.append("exact_match")
        return confidence, reasons
    
    # Extract metadata from both
    sidecar_meta = extract_metadata_from_filename(sidecar_stem)
    image_meta = extract_metadata_from_filename(image_stem)
    
    # Check camera ID match
    if sidecar_meta['camera_id'] and image_meta['camera_id']:
        if sidecar_meta['camera_id'] == image_meta['camera_id']:
            confidence += 40
            reasons.append(f"camera_id_match: {sidecar_meta['camera_id']}")
        else:
            # Different camera IDs = very unlikely to be same image
            return 0, ["camera_id_mismatch"]
    
    # Check date match
    if sidecar_meta['date'] and image_meta['date']:
        if sidecar_meta['date'] == image_meta['date']:
            confidence += 30
            reasons.append(f"date_match: {sidecar_meta['date']}")
        else:
            # Different dates = unlikely to be same image (unless renamed completely)
            confidence -= 20
            reasons.append("date_mismatch")
    
    # Check time match
    if sidecar_meta['time'] and image_meta['time']:
        if sidecar_meta['time'] == image_meta['time']:
            confidence += 20
            reasons.append(f"time_match: {sidecar_meta['time']}")
    
    # Check dimensions match
    if sidecar_meta['dimensions'] and image_meta['dimensions']:
        if sidecar_meta['dimensions'] == image_meta['dimensions']:
            confidence += 10
            reasons.append(f"dimensions_match: {sidecar_meta['dimensions']}")
    
    # Check if sidecar name is substring of image name (common in renaming scenarios)
    if sidecar_stem.lower() in image_stem.lower() or image_stem.lower() in sidecar_stem.lower():
        confidence += 15
        reasons.append("substring_match")
    
    # Use sequence matching for similarity
    similarity = SequenceMatcher(None, sidecar_stem.lower(), image_stem.lower()).ratio()
    if similarity > 0.7:
        confidence += int(similarity * 20)
        reasons.append(f"similarity: {similarity:.2f}")
    
    return max(0, min(100, confidence)), reasons


def find_best_match(sidecar_file, sidecar_ext, image_files):
    """
    Find the best matching image for a sidecar file.
    Returns (best_match, confidence, reasons, all_candidates)
    """
    candidates = []
    
    for image_file in image_files:
        confidence, reasons = calculate_match_confidence(sidecar_file, image_file, sidecar_ext)
        if confidence > 0:
            candidates.append({
                'image': image_file,
                'confidence': confidence,
                'reasons': reasons
            })
    
    if not candidates:
        return None, 0, [], []
    
    # Sort by confidence (highest first)
    candidates.sort(key=lambda x: x['confidence'], reverse=True)
    
    best = candidates[0]
    
    # Check for ambiguous matches (multiple high-confidence matches)
    if len(candidates) > 1 and candidates[1]['confidence'] >= 70:
        # Multiple high-confidence matches = ambiguous
        return None, 0, ["ambiguous_multiple_matches"], candidates
    
    return best['image'], best['confidence'], best['reasons'], candidates


def analyze_and_rename_sidecars(library_path: str, min_confidence: int = 80, dry_run: bool = True, 
                                rename_low_confidence: bool = False):
    """
    Analyze and rename orphaned sidecars.
    
    Args:
        library_path: Path to photo library
        min_confidence: Minimum confidence score to perform rename (0-100)
        dry_run: If True, only simulate renames without actually changing files
        rename_low_confidence: If True, rename low confidence matches with .unknown suffix
    """
    library = Path(library_path)
    
    if not library.exists():
        print(f"Error: Library path does not exist: {library_path}")
        sys.exit(1)
    
    # Prepare log files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(__file__).parent.parent / '.log'
    log_dir.mkdir(exist_ok=True)
    
    rename_log_file = log_dir / f"sidecar_renames_{timestamp}.json"
    ambiguous_log_file = log_dir / f"sidecar_ambiguous_{timestamp}.json"
    nomatch_log_file = log_dir / f"sidecar_nomatch_{timestamp}.json"
    
    # Track statistics
    stats = {
        'total_sidecars': 0,
        'matched_confident': 0,
        'matched_low_confidence': 0,
        'ambiguous': 0,
        'no_match': 0,
        'renamed': 0,
        'errors': 0
    }
    
    renames = []
    ambiguous = []
    no_matches = []
    
    print(f"{'='*70}")
    print(f"SIDECAR RENAME ANALYSIS")
    print(f"{'='*70}")
    print(f"Library: {library_path}")
    print(f"Minimum confidence: {min_confidence}%")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE - WILL RENAME FILES'}")
    print(f"{'='*70}\n")
    
    # Walk through all directories
    for root, dirs, files in os.walk(library):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        if not files:
            continue
        
        # Collect image files and sidecars in this directory
        image_files = [f for f in files if Path(f).suffix.lower() in IMAGE_EXTENSIONS and not f.startswith('.')]
        sidecar_files = [(f, Path(f).suffix.lower()) for f in files if Path(f).suffix.lower() in SIDECAR_EXTENSIONS and not f.startswith('.')]
        
        if not sidecar_files or not image_files:
            continue
        
        # Get matched sidecars (to exclude from orphan processing)
        image_stems = {Path(img).stem.lower() for img in image_files}
        
        # Process each sidecar
        for sidecar_file, sidecar_ext in sidecar_files:
            stats['total_sidecars'] += 1
            
            sidecar_stem = Path(sidecar_file).stem
            
            # Check if already matched
            if sidecar_stem.lower() in image_stems:
                continue  # Skip matched sidecars
            
            # Special handling for JSON files with double extensions
            if sidecar_ext == '.json':
                # Try removing common suffixes
                temp_stem = sidecar_stem
                for suffix in ['.supplemental-metadata', '.supplemental', '.supplemental-metada', '.metadata']:
                    if temp_stem.lower().endswith(suffix):
                        temp_stem = temp_stem[:-len(suffix)]
                        break
                for img_ext in ['.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff']:
                    if temp_stem.lower().endswith(img_ext):
                        temp_stem = temp_stem[:-len(img_ext)]
                        break
                
                if temp_stem.lower() in image_stems:
                    continue  # Actually matches after normalization
            
            # Find best match
            best_match, confidence, reasons, candidates = find_best_match(sidecar_file, sidecar_ext, image_files)
            
            rel_path = Path(root).relative_to(library)
            
            if best_match and confidence >= min_confidence:
                # High confidence match
                stats['matched_confident'] += 1
                
                # Construct new sidecar name
                new_sidecar_name = Path(best_match).stem + sidecar_ext
                
                rename_info = {
                    'folder': str(rel_path),
                    'old_name': sidecar_file,
                    'new_name': new_sidecar_name,
                    'matched_image': best_match,
                    'confidence': confidence,
                    'reasons': reasons
                }
                renames.append(rename_info)
                
                # Perform rename if not dry run
                if not dry_run:
                    try:
                        old_path = Path(root) / sidecar_file
                        new_path = Path(root) / new_sidecar_name
                        
                        if new_path.exists():
                            stats['errors'] += 1
                            rename_info['error'] = 'destination_exists'
                        else:
                            old_path.rename(new_path)
                            stats['renamed'] += 1
                            rename_info['status'] = 'renamed'
                    except Exception as e:
                        stats['errors'] += 1
                        rename_info['error'] = str(e)
                else:
                    rename_info['status'] = 'would_rename'
                
            elif best_match and confidence > 0:
                # Low confidence match
                stats['matched_low_confidence'] += 1
                
                # For low confidence, add .unknown suffix if requested
                new_sidecar_name = Path(best_match).stem + sidecar_ext
                if rename_low_confidence:
                    new_sidecar_name += '.unknown'
                
                rename_info = {
                    'folder': str(rel_path),
                    'old_name': sidecar_file,
                    'new_name': new_sidecar_name,
                    'matched_image': best_match,
                    'confidence': confidence,
                    'reasons': reasons,
                    'status': 'low_confidence'
                }
                renames.append(rename_info)
                
                # Perform rename if requested and not dry run
                if rename_low_confidence and not dry_run:
                    try:
                        old_path = Path(root) / sidecar_file
                        new_path = Path(root) / new_sidecar_name
                        
                        if new_path.exists():
                            stats['errors'] += 1
                            rename_info['error'] = 'destination_exists'
                        else:
                            old_path.rename(new_path)
                            stats['renamed'] += 1
                            rename_info['status'] = 'renamed'
                    except Exception as e:
                        stats['errors'] += 1
                        rename_info['error'] = str(e)
                elif rename_low_confidence:
                    rename_info['status'] = 'would_rename'
                
            elif candidates:
                # Ambiguous - multiple possible matches
                stats['ambiguous'] += 1
                ambiguous.append({
                    'folder': str(rel_path),
                    'sidecar': sidecar_file,
                    'candidates': candidates[:5]  # Top 5 candidates
                })
                
            else:
                # No match found
                stats['no_match'] += 1
                no_matches.append({
                    'folder': str(rel_path),
                    'sidecar': sidecar_file,
                    'sample_images': image_files[:5]
                })
    
    # Save logs
    with open(rename_log_file, 'w') as f:
        json.dump(renames, f, indent=2)
    
    with open(ambiguous_log_file, 'w') as f:
        json.dump(ambiguous, f, indent=2)
    
    with open(nomatch_log_file, 'w') as f:
        json.dump(no_matches, f, indent=2)
    
    # Create full path list files for ambiguous and no match
    ambiguous_paths_file = log_dir / f"sidecar_ambiguous_paths_{timestamp}.txt"
    nomatch_paths_file = log_dir / f"sidecar_nomatch_paths_{timestamp}.txt"
    
    with open(ambiguous_paths_file, 'w') as f:
        for item in ambiguous:
            full_path = library / item['folder'] / item['sidecar']
            f.write(f"{full_path}\n")
    
    with open(nomatch_paths_file, 'w') as f:
        for item in no_matches:
            full_path = library / item['folder'] / item['sidecar']
            f.write(f"{full_path}\n")
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total sidecars processed:        {stats['total_sidecars']:>6,}")
    print(f"High confidence matches (≥{min_confidence}%):  {stats['matched_confident']:>6,}")
    print(f"Low confidence matches (<{min_confidence}%):   {stats['matched_low_confidence']:>6,}")
    print(f"Ambiguous (multiple matches):    {stats['ambiguous']:>6,}")
    print(f"No match found:                  {stats['no_match']:>6,}")
    
    if not dry_run:
        print(f"\nRenamed successfully:            {stats['renamed']:>6,}")
        print(f"Errors:                          {stats['errors']:>6,}")
    
    print(f"\n{'='*70}")
    print(f"LOG FILES")
    print(f"{'='*70}")
    print(f"Renames (JSON):        {rename_log_file}")
    print(f"Ambiguous (JSON):      {ambiguous_log_file}")
    print(f"Ambiguous (paths):     {ambiguous_paths_file}")
    print(f"No match (JSON):       {nomatch_log_file}")
    print(f"No match (paths):      {nomatch_paths_file}")
    
    # Show some examples
    if renames:
        print(f"\n{'='*70}")
        print(f"EXAMPLE RENAMES (showing up to 10):")
        print(f"{'='*70}")
        for rename in renames[:10]:
            print(f"\nFolder: {rename['folder']}")
            print(f"  {rename['old_name']}")
            print(f"  → {rename['new_name']}")
            print(f"  Matched image: {rename['matched_image']}")
            print(f"  Confidence: {rename['confidence']}%")
            print(f"  Reasons: {', '.join(rename['reasons'])}")
            print(f"  Status: {rename.get('status', 'unknown')}")
    
    if ambiguous:
        print(f"\n{'='*70}")
        print(f"AMBIGUOUS MATCHES (showing up to 5):")
        print(f"{'='*70}")
        for amb in ambiguous[:5]:
            print(f"\nFolder: {amb['folder']}")
            print(f"  Sidecar: {amb['sidecar']}")
            print(f"  Possible matches:")
            for cand in amb['candidates'][:3]:
                print(f"    • {cand['image']} (confidence: {cand['confidence']}%)")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Rename orphaned sidecar files to match their corresponding images'
    )
    parser.add_argument('library_path', help='Path to photo library')
    parser.add_argument(
        '--min-confidence',
        type=int,
        default=80,
        help='Minimum confidence score (0-100) to perform rename (default: 80)'
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Perform actual renames (default is dry-run mode)'
    )
    parser.add_argument(
        '--rename-low-confidence',
        action='store_true',
        help='Also rename low confidence matches with .unknown suffix'
    )
    
    args = parser.parse_args()
    
    analyze_and_rename_sidecars(
        args.library_path,
        min_confidence=args.min_confidence,
        dry_run=not args.live,
        rename_low_confidence=args.rename_low_confidence
    )
