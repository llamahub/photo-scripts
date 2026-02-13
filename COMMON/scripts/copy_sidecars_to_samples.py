#!/usr/bin/env python3
"""
Copy sidecar files for sample images from main library to sample library.
Finds .xmp, .json, .unknown, .possible, and other sidecar files.
"""

import sys
from pathlib import Path
import shutil

def find_and_copy_sidecars(main_library, sample_library):
    """Find and copy sidecar files for all sample images."""
    
    main_library = Path(main_library)
    sample_library = Path(sample_library)
    
    # Sidecar extensions to look for
    sidecar_extensions = {'.xmp', '.json', '.unknown', '.possible', '.json.unknown', 
                         '.json.possible', '.xmp.unknown', '.xmp.possible', '.heic_original'}
    
    # Get all files in sample library
    sample_files = []
    for file_path in sample_library.rglob('*'):
        if file_path.is_file():
            sample_files.append(file_path)
    
    print(f"Scanning {len(sample_files)} files in sample library for corresponding sidecars...")
    print()
    
    found_sidecars = []
    copied_sidecars = []
    errors = []
    
    for i, sample_file in enumerate(sample_files):
        if (i + 1) % 100 == 0:
            print(f"  Checked {i + 1}/{len(sample_files)} files...")
        
        # Get relative path from sample library root
        rel_path = sample_file.relative_to(sample_library)
        
        # Find corresponding location in main library
        main_file = main_library / rel_path
        
        if not main_file.exists():
            continue
        
        # Get the directory and base name
        main_dir = main_file.parent
        base_name = main_file.stem
        
        # Look for sidecars with same base name
        for potential_sidecar in main_dir.glob(f"{base_name}.*"):
            if potential_sidecar == main_file:
                continue  # Skip the main file itself
            
            # Check if it's a sidecar extension
            ext = potential_sidecar.suffix.lower()
            # Also check for compound extensions like .json.unknown
            compound_ext = ''.join(potential_sidecar.suffixes).lower()
            
            is_sidecar = (ext in sidecar_extensions or 
                         compound_ext in sidecar_extensions or
                         any(compound_ext.endswith(se) for se in sidecar_extensions))
            
            if is_sidecar:
                found_sidecars.append((potential_sidecar, rel_path.parent))
                
                # Copy the sidecar
                target_sidecar = sample_library / rel_path.parent / potential_sidecar.name
                
                if target_sidecar.exists():
                    continue  # Already exists
                
                try:
                    # Ensure target directory exists
                    target_sidecar.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(potential_sidecar, target_sidecar)
                    copied_sidecars.append(potential_sidecar.name)
                except Exception as e:
                    errors.append(f"Error copying {potential_sidecar.name}: {e}")
    
    # Summary by extension
    extension_counts = {}
    for sidecar, _ in found_sidecars:
        ext = ''.join(sidecar.suffixes).lower()
        extension_counts[ext] = extension_counts.get(ext, 0) + 1
    
    print(f"\n{'='*70}")
    print("SIDECAR COPY SUMMARY")
    print(f"{'='*70}")
    print(f"Sample files checked:    {len(sample_files):>6}")
    print(f"Sidecars found:          {len(found_sidecars):>6}")
    print(f"Sidecars copied:         {len(copied_sidecars):>6}")
    print(f"Errors:                  {len(errors):>6}")
    
    if extension_counts:
        print(f"\nSidecars by type:")
        for ext, count in sorted(extension_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {ext:20s} {count:>6}")
    
    if errors:
        print(f"\nErrors:")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    
    print(f"{'='*70}")
    
    return len(copied_sidecars), errors

if __name__ == "__main__":
    main_library = "/mnt/photo_drive/santee-images"
    sample_library = "/mnt/photo_drive/santee-samples"
    
    copied, errors = find_and_copy_sidecars(main_library, sample_library)
    sys.exit(0 if len(errors) == 0 else 1)
