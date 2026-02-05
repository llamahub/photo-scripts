#!/usr/bin/env python3
"""
Search for matches to orphaned sidecars across the entire library.
This handles cases where images were moved to different folders based on EXIF dates.
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


def normalize_sidecar_name(sidecar_name):
    """Normalize sidecar name by removing common suffixes."""
    stem = Path(sidecar_name).stem
    
    # Remove common JSON metadata suffixes
    json_suffixes = ['.supplemental-metadata', '.supplemental', '.supplemental-metada', 
                     '.supplemental-met', '.supplem', '.metadata', '.metadat', '.metada']
    for suffix in json_suffixes:
        if stem.lower().endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    
    # Remove image extension if present in sidecar name
    for img_ext in ['.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff', '.gif', '.bmp']:
        if stem.lower().endswith(img_ext):
            stem = stem[:-len(img_ext)]
            break
    
    return stem


def calculate_match_confidence(sidecar_name, image_name):
    """Calculate confidence score (0-100) that a sidecar matches an image."""
    confidence = 0
    reasons = []
    
    # Normalize names
    sidecar_stem = normalize_sidecar_name(sidecar_name)
    image_stem = Path(image_name).stem
    
    # Exact match (after normalization)
    if sidecar_stem.lower() == image_stem.lower():
        confidence = 100
        reasons.append("exact_match")
        return confidence, reasons
    
    # Extract metadata from both
    sidecar_meta = extract_metadata_from_filename(sidecar_stem)
    image_meta = extract_metadata_from_filename(image_stem)
    
    # Check camera ID match - this is the strongest indicator
    if sidecar_meta['camera_id'] and image_meta['camera_id']:
        if sidecar_meta['camera_id'] == image_meta['camera_id']:
            confidence += 50
            reasons.append(f"camera_id: {sidecar_meta['camera_id']}")
        else:
            # Different camera IDs = very unlikely to be same image
            return 0, ["camera_id_mismatch"]
    
    # Check date match
    if sidecar_meta['date'] and image_meta['date']:
        if sidecar_meta['date'] == image_meta['date']:
            confidence += 20
            reasons.append(f"date: {sidecar_meta['date']}")
        else:
            # Different dates reduce confidence but don't eliminate
            confidence -= 10
    
    # Check time match
    if sidecar_meta['time'] and image_meta['time']:
        if sidecar_meta['time'] == image_meta['time']:
            confidence += 15
            reasons.append(f"time: {sidecar_meta['time']}")
    
    # Check dimensions match
    if sidecar_meta['dimensions'] and image_meta['dimensions']:
        if sidecar_meta['dimensions'] == image_meta['dimensions']:
            confidence += 10
            reasons.append(f"dimensions: {sidecar_meta['dimensions']}")
    
    # Check if sidecar name is substring of image name
    if sidecar_stem.lower() in image_stem.lower() or image_stem.lower() in sidecar_stem.lower():
        confidence += 10
        reasons.append("substring")
    
    # Use sequence matching for similarity
    similarity = SequenceMatcher(None, sidecar_stem.lower(), image_stem.lower()).ratio()
    if similarity > 0.6:
        confidence += int(similarity * 15)
        reasons.append(f"sim:{similarity:.2f}")
    
    return max(0, min(100, confidence)), reasons


def build_image_index(library_path):
    """Build an index of all images in the library with their metadata."""
    print("Building image index...")
    library = Path(library_path)
    
    # Index by camera ID for fast lookup
    camera_index = defaultdict(list)
    # Index by filename stem for exact matches
    name_index = {}
    
    total_images = 0
    
    for root, dirs, files in os.walk(library):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for filename in files:
            if filename.startswith('.'):
                continue
            
            ext = Path(filename).suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            
            total_images += 1
            
            full_path = Path(root) / filename
            rel_path = full_path.relative_to(library)
            
            # Extract metadata
            metadata = extract_metadata_from_filename(filename)
            
            image_info = {
                'filename': filename,
                'folder': str(Path(root).relative_to(library)),
                'full_path': str(full_path),
                'metadata': metadata
            }
            
            # Index by camera ID
            if metadata['camera_id']:
                camera_index[metadata['camera_id']].append(image_info)
            
            # Index by filename stem
            stem = Path(filename).stem.lower()
            name_index[stem] = image_info
            
            if total_images % 10000 == 0:
                print(f"  Indexed {total_images:,} images...")
    
    print(f"  Total images indexed: {total_images:,}")
    print(f"  Unique camera IDs: {len(camera_index)}")
    
    return camera_index, name_index


def find_matches_across_library(sidecar_path, camera_index, name_index, library_path):
    """Find potential matches for a sidecar file across the entire library."""
    sidecar_file = Path(sidecar_path)
    sidecar_name = sidecar_file.name
    
    # Extract metadata from sidecar
    sidecar_stem = normalize_sidecar_name(sidecar_name)
    sidecar_meta = extract_metadata_from_filename(sidecar_stem)
    
    candidates = []
    
    # Strategy 1: Check exact name match first
    if sidecar_stem.lower() in name_index:
        img_info = name_index[sidecar_stem.lower()]
        confidence, reasons = calculate_match_confidence(sidecar_name, img_info['filename'])
        if confidence > 0:
            candidates.append({
                'image': img_info['filename'],
                'folder': img_info['folder'],
                'full_path': img_info['full_path'],
                'confidence': confidence,
                'reasons': reasons,
                'match_type': 'exact_name'
            })
    
    # Strategy 2: Search by camera ID if available
    if sidecar_meta['camera_id'] and sidecar_meta['camera_id'] in camera_index:
        for img_info in camera_index[sidecar_meta['camera_id']]:
            confidence, reasons = calculate_match_confidence(sidecar_name, img_info['filename'])
            if confidence >= 50:  # Minimum threshold for cross-folder matches
                # Check if already added from exact name match
                if not any(c['full_path'] == img_info['full_path'] for c in candidates):
                    candidates.append({
                        'image': img_info['filename'],
                        'folder': img_info['folder'],
                        'full_path': img_info['full_path'],
                        'confidence': confidence,
                        'reasons': reasons,
                        'match_type': 'camera_id'
                    })
    
    # Sort by confidence
    candidates.sort(key=lambda x: x['confidence'], reverse=True)
    
    return candidates


def search_orphaned_sidecars(nomatch_file, library_path, min_confidence=80):
    """Search for matches across the library for orphaned sidecars."""
    
    if not Path(nomatch_file).exists():
        print(f"Error: File not found: {nomatch_file}")
        sys.exit(1)
    
    # Read orphaned sidecar paths
    with open(nomatch_file, 'r') as f:
        orphaned_paths = [line.strip() for line in f if line.strip()]
    
    print(f"{'='*70}")
    print(f"CROSS-FOLDER SIDECAR MATCHING")
    print(f"{'='*70}")
    print(f"Orphaned sidecars: {len(orphaned_paths):,}")
    print(f"Library: {library_path}")
    print(f"Minimum confidence: {min_confidence}%")
    print(f"{'='*70}\n")
    
    # Build image index
    camera_index, name_index = build_image_index(library_path)
    
    # Search for matches
    print(f"\nSearching for matches...")
    
    stats = {
        'total': len(orphaned_paths),
        'found_high_confidence': 0,
        'found_medium_confidence': 0,
        'found_low_confidence': 0,
        'not_found': 0
    }
    
    matches = []
    not_found = []
    
    library = Path(library_path)
    
    for i, sidecar_path in enumerate(orphaned_paths):
        if i % 1000 == 0 and i > 0:
            print(f"  Processed {i:,}/{len(orphaned_paths):,} sidecars...")
        
        sidecar_file = Path(sidecar_path)
        
        # Get original folder
        try:
            original_folder = sidecar_file.parent.relative_to(library)
        except ValueError:
            original_folder = sidecar_file.parent
        
        # Find matches
        candidates = find_matches_across_library(sidecar_path, camera_index, name_index, library_path)
        
        if candidates:
            best = candidates[0]
            
            # Only consider matches in different folders
            if str(original_folder) != best['folder']:
                match_info = {
                    'sidecar': str(sidecar_file.name),
                    'original_folder': str(original_folder),
                    'matched_image': best['image'],
                    'matched_folder': best['folder'],
                    'confidence': best['confidence'],
                    'reasons': best['reasons'],
                    'match_type': best['match_type'],
                    'sidecar_path': sidecar_path,
                    'image_path': best['full_path']
                }
                
                if best['confidence'] >= min_confidence:
                    stats['found_high_confidence'] += 1
                    match_info['category'] = 'high_confidence'
                elif best['confidence'] >= 60:
                    stats['found_medium_confidence'] += 1
                    match_info['category'] = 'medium_confidence'
                else:
                    stats['found_low_confidence'] += 1
                    match_info['category'] = 'low_confidence'
                
                matches.append(match_info)
            else:
                # Match in same folder (shouldn't happen but track it)
                stats['not_found'] += 1
        else:
            stats['not_found'] += 1
            not_found.append(sidecar_path)
    
    print(f"  Completed processing {len(orphaned_paths):,} sidecars")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(nomatch_file).parent
    
    matches_file = log_dir / f"cross_folder_matches_{timestamp}.json"
    still_orphaned_file = log_dir / f"still_orphaned_{timestamp}.txt"
    
    with open(matches_file, 'w') as f:
        json.dump(matches, f, indent=2)
    
    with open(still_orphaned_file, 'w') as f:
        for path in not_found:
            f.write(f"{path}\n")
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"RESULTS")
    print(f"{'='*70}")
    print(f"Total processed:              {stats['total']:>6,}")
    print(f"High confidence (≥{min_confidence}%):        {stats['found_high_confidence']:>6,}")
    print(f"Medium confidence (60-{min_confidence-1}%):    {stats['found_medium_confidence']:>6,}")
    print(f"Low confidence (<60%):        {stats['found_low_confidence']:>6,}")
    print(f"Still not found:              {stats['not_found']:>6,}")
    
    print(f"\n{'='*70}")
    print(f"OUTPUT FILES")
    print(f"{'='*70}")
    print(f"Matches: {matches_file}")
    print(f"Still orphaned: {still_orphaned_file}")
    
    # Show examples
    if matches:
        print(f"\n{'='*70}")
        print(f"EXAMPLE MATCHES (showing up to 15):")
        print(f"{'='*70}")
        
        # Show high confidence first
        high_conf = [m for m in matches if m['category'] == 'high_confidence']
        for match in high_conf[:10]:
            print(f"\nSidecar: {match['sidecar']}")
            print(f"  Original folder: {match['original_folder']}")
            print(f"  Matched image:   {match['matched_image']}")
            print(f"  In folder:       {match['matched_folder']}")
            print(f"  Confidence: {match['confidence']}% ({', '.join(match['reasons'])})")
        
        if stats['found_medium_confidence'] > 0:
            print(f"\n--- Medium Confidence Examples ---")
            medium_conf = [m for m in matches if m['category'] == 'medium_confidence']
            for match in medium_conf[:5]:
                print(f"\nSidecar: {match['sidecar']}")
                print(f"  Original folder: {match['original_folder']}")
                print(f"  Matched image:   {match['matched_image']}")
                print(f"  In folder:       {match['matched_folder']}")
                print(f"  Confidence: {match['confidence']}% ({', '.join(match['reasons'])})")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Search for matches to orphaned sidecars across the entire library'
    )
    parser.add_argument('nomatch_file', help='Path to nomatch file (list of orphaned sidecar paths)')
    parser.add_argument('library_path', help='Path to photo library')
    parser.add_argument(
        '--min-confidence',
        type=int,
        default=80,
        help='Minimum confidence for high-confidence category (default: 80)'
    )
    
    args = parser.parse_args()
    
    search_orphaned_sidecars(args.nomatch_file, args.library_path, args.min_confidence)
