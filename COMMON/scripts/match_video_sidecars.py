#!/usr/bin/env python3
"""
Search for video file matches in a separate video library for orphaned sidecars.
"""

import os
import sys
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

# Video extensions
VIDEO_EXTENSIONS = {
    '.mov', '.mp4', '.avi', '.m4v', '.mpg', '.mpeg', '.wmv', '.mkv', '.flv', '.webm', '.3gp'
}


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
    
    # Remove video extension if present in sidecar name
    for vid_ext in VIDEO_EXTENSIONS:
        if stem.lower().endswith(vid_ext):
            stem = stem[:-len(vid_ext)]
            break
    
    # Remove image extension if present (in case it was converted)
    for img_ext in ['.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff', '.gif', '.bmp']:
        if stem.lower().endswith(img_ext):
            stem = stem[:-len(img_ext)]
            break
    
    return stem


def has_video_extension_in_name(filename):
    """Check if filename contains a video extension."""
    name_lower = filename.lower()
    for ext in VIDEO_EXTENSIONS:
        if ext in name_lower:
            return True
    return False


def calculate_match_confidence(sidecar_name, video_name):
    """Calculate confidence score (0-100) that a sidecar matches a video."""
    confidence = 0
    reasons = []
    
    # Normalize names
    sidecar_stem = normalize_sidecar_name(sidecar_name)
    video_stem = Path(video_name).stem
    
    # Exact match (after normalization)
    if sidecar_stem.lower() == video_stem.lower():
        confidence = 100
        reasons.append("exact_match")
        return confidence, reasons
    
    # Check if sidecar name is substring of video name or vice versa
    if sidecar_stem.lower() in video_stem.lower() or video_stem.lower() in sidecar_stem.lower():
        confidence += 60
        reasons.append("substring")
    
    # Use sequence matching for similarity
    similarity = SequenceMatcher(None, sidecar_stem.lower(), video_stem.lower()).ratio()
    if similarity > 0.7:
        confidence += int(similarity * 40)
        reasons.append(f"sim:{similarity:.2f}")
    
    return max(0, min(100, confidence)), reasons


def build_video_index(video_library_path):
    """Build an index of all videos in the library."""
    print("Building video index...")
    library = Path(video_library_path)
    
    if not library.exists():
        print(f"Warning: Video library not found: {video_library_path}")
        return {}, {}
    
    # Index by filename stem for fast lookup
    name_index = {}
    all_videos = []
    
    total_videos = 0
    
    for root, dirs, files in os.walk(library):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for filename in files:
            if filename.startswith('.'):
                continue
            
            ext = Path(filename).suffix.lower()
            if ext not in VIDEO_EXTENSIONS:
                continue
            
            total_videos += 1
            
            full_path = Path(root) / filename
            rel_path = full_path.relative_to(library)
            
            video_info = {
                'filename': filename,
                'folder': str(Path(root).relative_to(library)),
                'full_path': str(full_path)
            }
            
            # Index by filename stem
            stem = Path(filename).stem.lower()
            name_index[stem] = video_info
            all_videos.append(video_info)
            
            if total_videos % 1000 == 0:
                print(f"  Indexed {total_videos:,} videos...")
    
    print(f"  Total videos indexed: {total_videos:,}")
    
    return name_index, all_videos


def search_video_sidecars(orphaned_file, video_library_path):
    """Search for video matches in video library for orphaned sidecars."""
    
    if not Path(orphaned_file).exists():
        print(f"Error: File not found: {orphaned_file}")
        sys.exit(1)
    
    # Read orphaned sidecar paths
    with open(orphaned_file, 'r') as f:
        orphaned_paths = [line.strip() for line in f if line.strip()]
    
    # Filter for video-related sidecars
    video_sidecars = []
    for path in orphaned_paths:
        filename = Path(path).name
        if has_video_extension_in_name(filename):
            video_sidecars.append(path)
    
    print(f"{'='*70}")
    print(f"VIDEO SIDECAR MATCHING")
    print(f"{'='*70}")
    print(f"Total orphaned sidecars: {len(orphaned_paths):,}")
    print(f"Video-related sidecars:  {len(video_sidecars):,}")
    print(f"Video library: {video_library_path}")
    print(f"{'='*70}\n")
    
    if not video_sidecars:
        print("No video-related sidecars found.")
        return
    
    # Build video index
    name_index, all_videos = build_video_index(video_library_path)
    
    if not all_videos:
        print("\nNo videos found in video library.")
        return
    
    # Search for matches
    print(f"\nSearching for video matches...")
    
    matches = []
    not_found = []
    
    for i, sidecar_path in enumerate(video_sidecars):
        if i % 100 == 0 and i > 0:
            print(f"  Processed {i}/{len(video_sidecars)} video sidecars...")
        
        sidecar_file = Path(sidecar_path)
        sidecar_name = sidecar_file.name
        
        # Normalize and try exact match first
        normalized = normalize_sidecar_name(sidecar_name)
        
        if normalized.lower() in name_index:
            video_info = name_index[normalized.lower()]
            confidence, reasons = calculate_match_confidence(sidecar_name, video_info['filename'])
            
            matches.append({
                'sidecar': sidecar_name,
                'sidecar_path': sidecar_path,
                'video': video_info['filename'],
                'video_folder': video_info['folder'],
                'video_path': video_info['full_path'],
                'confidence': confidence,
                'reasons': reasons,
                'match_type': 'exact_name'
            })
        else:
            # Try fuzzy matching against all videos
            best_match = None
            best_confidence = 0
            
            for video_info in all_videos:
                confidence, reasons = calculate_match_confidence(sidecar_name, video_info['filename'])
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        'sidecar': sidecar_name,
                        'sidecar_path': sidecar_path,
                        'video': video_info['filename'],
                        'video_folder': video_info['folder'],
                        'video_path': video_info['full_path'],
                        'confidence': confidence,
                        'reasons': reasons,
                        'match_type': 'fuzzy'
                    }
            
            if best_match and best_confidence >= 60:
                matches.append(best_match)
            else:
                not_found.append(sidecar_path)
    
    print(f"  Completed processing {len(video_sidecars)} video sidecars")
    
    # Categorize matches by confidence
    high_conf = [m for m in matches if m['confidence'] >= 80]
    medium_conf = [m for m in matches if 60 <= m['confidence'] < 80]
    
    # Save results
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(orphaned_file).parent
    
    import json
    matches_file = log_dir / f"video_sidecar_matches_{timestamp}.json"
    not_found_file = log_dir / f"video_sidecars_not_found_{timestamp}.txt"
    
    with open(matches_file, 'w') as f:
        json.dump(matches, f, indent=2)
    
    with open(not_found_file, 'w') as f:
        for path in not_found:
            f.write(f"{path}\n")
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"RESULTS")
    print(f"{'='*70}")
    print(f"Video sidecars checked:       {len(video_sidecars):>6,}")
    print(f"Matches found (≥80%):         {len(high_conf):>6,}")
    print(f"Matches found (60-79%):       {len(medium_conf):>6,}")
    print(f"Not found:                    {len(not_found):>6,}")
    
    print(f"\n{'='*70}")
    print(f"OUTPUT FILES")
    print(f"{'='*70}")
    print(f"Matches: {matches_file}")
    print(f"Not found: {not_found_file}")
    
    # Show examples
    if matches:
        print(f"\n{'='*70}")
        print(f"EXAMPLE MATCHES:")
        print(f"{'='*70}")
        
        for match in (high_conf + medium_conf)[:15]:
            print(f"\nSidecar: {match['sidecar']}")
            print(f"  Video: {match['video']}")
            print(f"  In folder: {match['video_folder']}")
            print(f"  Confidence: {match['confidence']}% ({', '.join(match['reasons'])})")
            print(f"  Sidecar path: {match['sidecar_path']}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Search for video file matches for orphaned sidecars'
    )
    parser.add_argument('orphaned_file', help='Path to still-orphaned sidecars file')
    parser.add_argument('video_library', help='Path to video library')
    
    args = parser.parse_args()
    
    search_video_sidecars(args.orphaned_file, args.video_library)
