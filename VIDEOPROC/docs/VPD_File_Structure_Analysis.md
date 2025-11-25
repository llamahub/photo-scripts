# VideoProc Vlogger (.vpd) File Structure Analysis

## Document Purpose
This document provides a comprehensive analysis of the VideoProc Vlogger project file format (.vpd) to facilitate the creation of repair and reorganization scripts for missing or corrupted media files.

---

## File Format Overview
- **Format**: JSON
- **Extension**: `.vpd`
- **Encoding**: UTF-8
- **Structure**: Hierarchical JSON with five main sections

---

## Major Components

### 1. Timeline Section (`timeline`)
**Purpose**: Defines the project's timeline structure, tracks, and media blocks

#### Key Properties:
- `title`: "MainTimeline"
- `type`: "MainTimeline"
- `status`: Integer status code
- `subitems`: Array of track objects
- `tstart`: Timeline start time (milliseconds)
- `tduration`: Timeline total duration
- `context`: Total content duration in timeline

#### Track Types:
1. **MainVideoTrack** - Primary video/image track
   - Contains `ImageFileBlock` or `VideoFileBlock` objects
   - Each block has:
     - `title`: Display name (often filename without extension)
     - `uuid`: Unique identifier for this timeline instance
     - `resid`: UUID linking to resource in scapegoat section
     - `restype`: "MediaFileResource"
     - `tstart`: Start position on timeline (milliseconds)
     - `tduration`: Duration of block on timeline
     - `attribute`: Extensive editing properties

2. **OverlayTrack** - Overlay video/image elements
3. **VideoEffectTrack** - Video effects layer
4. **AudioTrack** - Audio clips and music
5. **SubtitleTrack** - Text/subtitle overlays

#### Block Attributes:
Each media block contains extensive editing information:
- **VideoAttribute**: 
  - `VideoCropper`: Crop and zoom keyframe animation
  - `VideoTransformer`: Position, scale, rotation
  - `BaseTransform`: Basic transforms (flip, rotation)
  - `ColorEditor`: Color grading (temperature, tint, exposure, HSL)
  - `ChromaKey`: Green screen keying
  - `VideoLUT`: LUT color grading
  - `Sharpen`: Sharpening settings
  - `Denoise`: Noise reduction
  - `VignetteEditor`: Vignette effects
  - `Compositing`: Blending modes and opacity
  
- **AudioAttribute**: Audio editing properties (if applicable)
- **SpeedAttribute**: Playback speed modifications

---

### 2. Project Info Section (`projinfo`)
**Purpose**: Project metadata and playback settings

#### Key Properties:
```json
{
  "name": "ProjectName",
  "projectfile": "/full/path/to/project.vpd",
  "savetime": {
    "year": 2025,
    "month": 11,
    "day": 22,
    "hour": 14,
    "minute": 32,
    "second": 1
  },
  "player": {
    "version": 0,
    "frameRateNum": 60,
    "frameRateDen": 1,
    "resolutionW": 1920,
    "resolutionH": 1080,
    "clearR": 0.0,
    "clearG": 0.0,
    "clearB": 0.0,
    "clearA": 1.0,
    "showRefline": true,
    "lockRefline": false,
    "refLines": [],
    "volume": 1.0
  }
}
```

**Note**: The `projectfile` path should be updated if project is moved.

---

### 3. Resource Lists Section

Three separate resource list sections for different media types:

#### a) Video List (`videolist`)
- Contains video file resources
- Structure: `{ "title": "video", "type": "ResourceLists", "status": 0, "subitems": [] }`

#### b) Audio List (`audiolist`)
- Contains audio file resources (music, sound effects)
- Direct entries with full file paths

**Example**:
```json
{
  "title": "audio_filename",
  "type": "MediaFileResource",
  "status": 0,
  "uuid": "UNIQUE_HASH_ID",
  "path": "/full/path/to/audio.mp3",
  "duration": 239.72571428571428
}
```

#### c) Image List (`imagelist`)
- Most complex resource list
- Contains individual image links and grouped resource lists
- Uses both direct links and nested ResourceList groups

**Structure**:
```json
{
  "title": "image",
  "type": "ResourceLists",
  "status": 0,
  "subitems": [
    // Direct links to resources
    {
      "type": "link",
      "resid": "HASH_ID_FROM_SCAPEGOAT",
      "uuid": "INSTANCE_UUID"
    },
    // Grouped resources (e.g., imported from folders)
    {
      "title": "folder_name",
      "type": "ResourceList",
      "status": 0,
      "subitems": [
        {
          "type": "link",
          "resid": "HASH_ID",
          "uuid": "INSTANCE_UUID"
        }
      ],
      "orientation": 2  // Image orientation code
    }
  ],
  "scapegoat": [ /* Actual file definitions */ ]
}
```

---

### 4. Scapegoat Section (Resource Definitions)
**Purpose**: Contains actual file path definitions and metadata for all media resources

Located within each resource list (videolist, audiolist, imagelist) as the `scapegoat` array.

**Structure**:
```json
{
  "title": "filename_or_display_name",
  "type": "MediaFileResource",
  "status": 0,          // 0 = active, 4096 = possibly unused/reference
  "uuid": "UNIQUE_HASH", // MD5-like hash used as resource ID
  "path": "/absolute/path/to/file.ext",
  "duration": 0.04       // Duration in seconds (0.0 for images, actual for video/audio)
}
```

**Critical**: This is where file paths must be updated for repair scripts.

---

### 5. Subtitle List Section (`subtitlelist`)
- Contains subtitle/text resources
- Usually empty or minimal in typical projects

---

## UUID System

### Two Types of UUIDs:

1. **Resource UUID** (in scapegoat section)
   - Format: 32-character hexadecimal hash (MD5-like)
   - Example: `"8B3DF940F26B065CB67321254910507F"`
   - Purpose: Unique identifier for the actual media file
   - Used in: `resid` field in timeline blocks

2. **Instance UUID** (in timeline blocks)
   - Format: Standard UUID with hyphens
   - Example: `"7BF9F98D-0E70-48B7-A62A-D83218D2D991"`
   - Purpose: Unique identifier for each use of a resource on timeline
   - Same resource can be used multiple times with different instance UUIDs

### Linking System:
```
Timeline Block (uuid) 
    → resid links to → 
        Scapegoat Resource (uuid) 
            → contains → 
                File path
```

---

## File Path Patterns

### Common Path Issues:

1. **Relative vs Absolute Paths**
   - All paths are absolute
   - Format: `/Users/username/Movies/Project/subfolder/file.ext`

2. **Folder Organization Patterns**:
   - Root folder: `/Images/filename.ext`
   - Subfolders: `/Images/selected-01/filename.ext`
   - Nested: `/Images/selected-02/selected-03/filename.ext`
   - External: `/Images/Immich/filename.ext`

3. **File Extension Variations**:
   - Images: `.jpg`, `.heic`, `.png`
   - Video: `.mp4`, `.mov`
   - Audio: `.mp3`, `.wav`, `.m4a`

---

## Status Codes

### Observed Status Values:
- `0` = Active resource, used in timeline
- `4096` = Resource loaded but possibly not actively used in timeline
- Other values may indicate different states

**Note**: Resources with status `4096` may be in project library but not on timeline.

---

## Error Detection & File Resolution

### When Files Are Missing:

VideoProc Vlogger displays errors like:
```
Failed loading /full/path/to/file.ext
Failed loading resource RESOURCE-UUID
Failed loading
```

### Common Causes:
1. **File moved to different folder**
   - Original: `/Images/selected-01/file.jpg`
   - Actual: `/Images/file.jpg`

2. **File format conversion**
   - Original: `file.heic`
   - Actual: `file.jpg`

3. **File renamed**
   - Original: `IMG_1234.jpg`
   - Actual: `2025-01-01_IMG_1234.jpg`

4. **Project moved to different computer/path**
   - Original: `/Users/john/Movies/Project/`
   - New: `/Users/jane/Videos/Project/`

---

## Repair Script Strategy

### Step 1: Parse the VPD File
```python
import json

with open('project.vpd', 'r') as f:
    vpd_data = json.load(f)
```

### Step 2: Extract All File Paths
```python
def extract_file_paths(vpd_data):
    paths = []
    
    # Check imagelist scapegoat
    if 'imagelist' in vpd_data and 'scapegoat' in vpd_data['imagelist']:
        for resource in vpd_data['imagelist']['scapegoat']:
            paths.append({
                'type': 'image',
                'uuid': resource['uuid'],
                'path': resource['path'],
                'title': resource['title']
            })
    
    # Check audiolist subitems
    if 'audiolist' in vpd_data and 'subitems' in vpd_data['audiolist']:
        for resource in vpd_data['audiolist']['subitems']:
            paths.append({
                'type': 'audio',
                'uuid': resource['uuid'],
                'path': resource['path'],
                'title': resource['title']
            })
    
    # Check videolist scapegoat (if exists)
    if 'videolist' in vpd_data and 'scapegoat' in vpd_data['videolist']:
        for resource in vpd_data['videolist']['scapegoat']:
            paths.append({
                'type': 'video',
                'uuid': resource['uuid'],
                'path': resource['path'],
                'title': resource['title']
            })
    
    return paths
```

### Step 3: Verify File Existence
```python
import os

def verify_files(file_paths):
    missing = []
    existing = []
    
    for item in file_paths:
        if os.path.exists(item['path']):
            existing.append(item)
        else:
            missing.append(item)
    
    return existing, missing
```

### Step 4: Search for Missing Files
```python
import os
from pathlib import Path

def find_file_in_project(filename, project_root):
    """Search for file in project directory tree"""
    matches = []
    
    for root, dirs, files in os.walk(project_root):
        if filename in files:
            matches.append(os.path.join(root, filename))
    
    return matches

def find_similar_files(original_path, project_root):
    """Find files with similar names (different extension or prefix)"""
    original_name = Path(original_path).stem  # filename without extension
    matches = []
    
    for root, dirs, files in os.walk(project_root):
        for file in files:
            if original_name in file:
                matches.append(os.path.join(root, file))
    
    return matches
```

### Step 5: Update Paths in VPD
```python
def update_resource_path(vpd_data, uuid, new_path, resource_type='image'):
    """Update a resource path in the VPD data structure"""
    
    if resource_type == 'image':
        if 'imagelist' in vpd_data and 'scapegoat' in vpd_data['imagelist']:
            for resource in vpd_data['imagelist']['scapegoat']:
                if resource['uuid'] == uuid:
                    resource['path'] = new_path
                    return True
    
    elif resource_type == 'audio':
        if 'audiolist' in vpd_data and 'subitems' in vpd_data['audiolist']:
            for resource in vpd_data['audiolist']['subitems']:
                if resource['uuid'] == uuid:
                    resource['path'] = new_path
                    return True
    
    elif resource_type == 'video':
        if 'videolist' in vpd_data and 'scapegoat' in vpd_data['videolist']:
            for resource in vpd_data['videolist']['scapegoat']:
                if resource['uuid'] == uuid:
                    resource['path'] = new_path
                    return True
    
    return False
```

### Step 6: Save Updated VPD
```python
def save_vpd(vpd_data, output_path):
    """Save updated VPD file"""
    with open(output_path, 'w') as f:
        json.dump(vpd_data, f, indent=4)
```

---

## Complete Repair Script Example

```python
#!/usr/bin/env python3
"""
VideoProc Vlogger Project Repair Script
Finds and fixes missing media file references in .vpd project files
"""

import json
import os
import sys
from pathlib import Path

def load_vpd(vpd_path):
    """Load VPD project file"""
    with open(vpd_path, 'r') as f:
        return json.load(f)

def save_vpd(vpd_data, output_path):
    """Save VPD project file"""
    with open(output_path, 'w') as f:
        json.dump(vpd_data, f, indent=4)

def extract_all_resources(vpd_data):
    """Extract all media resources from VPD"""
    resources = []
    
    # Images
    if 'imagelist' in vpd_data and 'scapegoat' in vpd_data['imagelist']:
        for res in vpd_data['imagelist']['scapegoat']:
            resources.append({
                'type': 'image',
                'location': 'imagelist.scapegoat',
                'uuid': res['uuid'],
                'path': res['path'],
                'title': res['title']
            })
    
    # Audio
    if 'audiolist' in vpd_data and 'subitems' in vpd_data['audiolist']:
        for res in vpd_data['audiolist']['subitems']:
            resources.append({
                'type': 'audio',
                'location': 'audiolist.subitems',
                'uuid': res['uuid'],
                'path': res['path'],
                'title': res['title']
            })
    
    # Video
    if 'videolist' in vpd_data and 'scapegoat' in vpd_data['videolist']:
        for res in vpd_data['videolist']['scapegoat']:
            resources.append({
                'type': 'video',
                'location': 'videolist.scapegoat',
                'uuid': res['uuid'],
                'path': res['path'],
                'title': res['title']
            })
    
    return resources

def verify_resources(resources):
    """Check which resources exist"""
    missing = []
    existing = []
    
    for res in resources:
        if os.path.exists(res['path']):
            existing.append(res)
        else:
            missing.append(res)
    
    return existing, missing

def search_for_file(filename, search_root):
    """Search for file in directory tree"""
    matches = []
    
    # Try exact filename match
    for root, dirs, files in os.walk(search_root):
        if filename in files:
            matches.append(os.path.join(root, filename))
    
    # Try stem match (different extensions)
    if not matches:
        stem = Path(filename).stem
        for root, dirs, files in os.walk(search_root):
            for file in files:
                if Path(file).stem == stem:
                    matches.append(os.path.join(root, file))
    
    return matches

def update_resource_path(vpd_data, resource, new_path):
    """Update resource path in VPD structure"""
    location = resource['location']
    uuid = resource['uuid']
    
    if location == 'imagelist.scapegoat':
        for res in vpd_data['imagelist']['scapegoat']:
            if res['uuid'] == uuid:
                res['path'] = new_path
                return True
                
    elif location == 'audiolist.subitems':
        for res in vpd_data['audiolist']['subitems']:
            if res['uuid'] == uuid:
                res['path'] = new_path
                return True
                
    elif location == 'videolist.scapegoat':
        for res in vpd_data['videolist']['scapegoat']:
            if res['uuid'] == uuid:
                res['path'] = new_path
                return True
    
    return False

def repair_project(vpd_path, search_root=None, output_path=None):
    """Main repair function"""
    
    # Default search to project parent directory
    if search_root is None:
        search_root = Path(vpd_path).parent.parent
    
    # Default output to original file (backup recommended)
    if output_path is None:
        output_path = vpd_path
    
    print(f"Loading project: {vpd_path}")
    vpd_data = load_vpd(vpd_path)
    
    print("Extracting resources...")
    resources = extract_all_resources(vpd_data)
    print(f"Found {len(resources)} total resources")
    
    print("Verifying file existence...")
    existing, missing = verify_resources(resources)
    print(f"Existing: {len(existing)}, Missing: {len(missing)}")
    
    if not missing:
        print("No missing files! Project is healthy.")
        return
    
    print(f"\nSearching for {len(missing)} missing files in {search_root}...")
    
    fixed = 0
    unfixed = []
    
    for res in missing:
        filename = Path(res['path']).name
        print(f"  Searching for: {filename}")
        
        matches = search_for_file(filename, search_root)
        
        if matches:
            if len(matches) == 1:
                new_path = matches[0]
                print(f"    ✓ Found: {new_path}")
                if update_resource_path(vpd_data, res, new_path):
                    fixed += 1
            else:
                print(f"    ! Multiple matches found:")
                for i, match in enumerate(matches, 1):
                    print(f"      {i}. {match}")
                # Use first match (could add user prompt here)
                new_path = matches[0]
                print(f"    Using: {new_path}")
                if update_resource_path(vpd_data, res, new_path):
                    fixed += 1
        else:
            print(f"    ✗ Not found")
            unfixed.append(res)
    
    print(f"\nRepair summary:")
    print(f"  Fixed: {fixed}")
    print(f"  Unfixed: {len(unfixed)}")
    
    if fixed > 0:
        print(f"\nSaving updated project to: {output_path}")
        save_vpd(vpd_data, output_path)
        print("✓ Project saved successfully")
    
    if unfixed:
        print("\nUnfixed resources:")
        for res in unfixed:
            print(f"  - {res['title']} ({res['type']})")
            print(f"    Original path: {res['path']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python repair_vpd.py <project.vpd> [search_root] [output.vpd]")
        sys.exit(1)
    
    vpd_path = sys.argv[1]
    search_root = sys.argv[2] if len(sys.argv) > 2 else None
    output_path = sys.argv[3] if len(sys.argv) > 3 else vpd_path
    
    repair_project(vpd_path, search_root, output_path)
```

---

## Project Relocation Script

```python
#!/usr/bin/env python3
"""
Relocate VideoProc Vlogger project to new base path
"""

import json
import sys
from pathlib import Path

def relocate_project(vpd_path, old_base, new_base, output_path=None):
    """Update all file paths from old base to new base"""
    
    if output_path is None:
        output_path = vpd_path
    
    with open(vpd_path, 'r') as f:
        vpd_data = json.load(f)
    
    changes = 0
    
    # Update project file path
    if 'projinfo' in vpd_data and 'projectfile' in vpd_data['projinfo']:
        old_path = vpd_data['projinfo']['projectfile']
        if old_path.startswith(old_base):
            vpd_data['projinfo']['projectfile'] = old_path.replace(old_base, new_base)
            changes += 1
    
    # Update image paths
    if 'imagelist' in vpd_data and 'scapegoat' in vpd_data['imagelist']:
        for res in vpd_data['imagelist']['scapegoat']:
            if res['path'].startswith(old_base):
                res['path'] = res['path'].replace(old_base, new_base)
                changes += 1
    
    # Update audio paths
    if 'audiolist' in vpd_data and 'subitems' in vpd_data['audiolist']:
        for res in vpd_data['audiolist']['subitems']:
            if res['path'].startswith(old_base):
                res['path'] = res['path'].replace(old_base, new_base)
                changes += 1
    
    # Update video paths
    if 'videolist' in vpd_data and 'scapegoat' in vpd_data['videolist']:
        for res in vpd_data['videolist']['scapegoat']:
            if res['path'].startswith(old_base):
                res['path'] = res['path'].replace(old_base, new_base)
                changes += 1
    
    print(f"Updated {changes} paths")
    print(f"  Old base: {old_base}")
    print(f"  New base: {new_base}")
    
    with open(output_path, 'w') as f:
        json.dump(vpd_data, f, indent=4)
    
    print(f"Saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python relocate_vpd.py <project.vpd> <old_base_path> <new_base_path> [output.vpd]")
        print("\nExample:")
        print("  python relocate_vpd.py project.vpd '/Users/john/Movies' '/Users/jane/Videos'")
        sys.exit(1)
    
    vpd_path = sys.argv[1]
    old_base = sys.argv[2]
    new_base = sys.argv[3]
    output_path = sys.argv[4] if len(sys.argv) > 4 else vpd_path
    
    relocate_project(vpd_path, old_base, new_base, output_path)
```

---

## Media File Organization Script

```python
#!/usr/bin/env python3
"""
Reorganize media files referenced in VPD project
Consolidates scattered files into organized structure
"""

import json
import os
import shutil
from pathlib import Path

def organize_media(vpd_path, output_dir, organize_mode='copy'):
    """
    Organize media files into structured folders
    
    organize_mode: 'copy' or 'move'
    """
    
    with open(vpd_path, 'r') as f:
        vpd_data = json.load(f)
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create organized structure
    (output_dir / 'Images').mkdir(exist_ok=True)
    (output_dir / 'Audio').mkdir(exist_ok=True)
    (output_dir / 'Video').mkdir(exist_ok=True)
    
    def process_resources(resources, location_key, media_type):
        processed = 0
        for res in resources:
            if not os.path.exists(res['path']):
                print(f"  ✗ Missing: {res['path']}")
                continue
            
            src_path = Path(res['path'])
            dest_dir = output_dir / media_type.capitalize()
            dest_path = dest_dir / src_path.name
            
            # Handle name conflicts
            counter = 1
            while dest_path.exists():
                stem = src_path.stem
                ext = src_path.suffix
                dest_path = dest_dir / f"{stem}_{counter}{ext}"
                counter += 1
            
            # Copy or move file
            if organize_mode == 'copy':
                shutil.copy2(src_path, dest_path)
            else:
                shutil.move(src_path, dest_path)
            
            # Update VPD path
            res['path'] = str(dest_path)
            processed += 1
            print(f"  ✓ {organize_mode}: {src_path.name} → {dest_path}")
        
        return processed
    
    # Process images
    if 'imagelist' in vpd_data and 'scapegoat' in vpd_data['imagelist']:
        print("Processing images...")
        count = process_resources(vpd_data['imagelist']['scapegoat'], 'imagelist.scapegoat', 'images')
        print(f"  Processed {count} images")
    
    # Process audio
    if 'audiolist' in vpd_data and 'subitems' in vpd_data['audiolist']:
        print("Processing audio...")
        count = process_resources(vpd_data['audiolist']['subitems'], 'audiolist.subitems', 'audio')
        print(f"  Processed {count} audio files")
    
    # Process video
    if 'videolist' in vpd_data and 'scapegoat' in vpd_data['videolist']:
        print("Processing video...")
        count = process_resources(vpd_data['videolist']['scapegoat'], 'videolist.scapegoat', 'video')
        print(f"  Processed {count} video files")
    
    # Save updated VPD
    output_vpd = output_dir / Path(vpd_path).name
    with open(output_vpd, 'w') as f:
        json.dump(vpd_data, f, indent=4)
    
    print(f"\nUpdated project saved to: {output_vpd}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python organize_media.py <project.vpd> <output_directory> [copy|move]")
        print("\nExample:")
        print("  python organize_media.py project.vpd ./organized copy")
        sys.exit(1)
    
    vpd_path = sys.argv[1]
    output_dir = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else 'copy'
    
    if mode not in ['copy', 'move']:
        print("Error: Mode must be 'copy' or 'move'")
        sys.exit(1)
    
    organize_media(vpd_path, output_dir, mode)
```

---

## Best Practices

### Before Editing VPD Files:
1. **Always create a backup**
   ```bash
   cp project.vpd project.vpd.backup
   ```

2. **Close VideoProc Vlogger** - Don't edit while project is open

3. **Validate JSON after editing**
   ```bash
   python -m json.tool project.vpd > /dev/null && echo "Valid JSON" || echo "Invalid JSON"
   ```

### Path Management:
1. Use absolute paths (required by VideoProc)
2. Maintain consistent folder structure
3. Keep media files within project directory when possible
4. Use descriptive filenames with dates/metadata

### Project Organization:
```
Project_Name.dvp/
├── Project_Name.vpd          # Project file
├── Project_Name.userdata     # User preferences
├── Images/                   # Image media
│   ├── file1.jpg
│   └── file2.heic
├── Video/                    # Video media
│   └── clip1.mp4
└── Audio/                    # Audio media
    └── music.mp3
```

---

## Troubleshooting Common Issues

### Issue 1: "Failed loading resource"
**Cause**: File path in scapegoat doesn't match actual location
**Fix**: Update the `path` field in the corresponding scapegoat entry

### Issue 2: Multiple resources with same filename
**Cause**: Files from different folders with identical names
**Fix**: Check UUID to identify correct resource, update specific entry

### Issue 3: Format conversion (HEIC → JPG)
**Cause**: File was converted but path still references old extension
**Fix**: Update file extension in path field

### Issue 4: Project won't open after editing
**Cause**: Invalid JSON syntax
**Fix**: Validate JSON, check for missing commas/brackets

### Issue 5: Media shows but with wrong edits
**Cause**: Wrong resource UUID linked in timeline
**Fix**: Verify `resid` in timeline block matches correct scapegoat UUID

---

## Conclusion

The VideoProc Vlogger .vpd format is a well-structured JSON format that can be programmatically repaired and reorganized. The key to successful repairs is understanding:

1. The dual UUID system (resource vs instance)
2. The scapegoat section as the source of truth for file paths
3. The linking mechanism between timeline and resources
4. Proper JSON structure and syntax

With the scripts provided above, you can:
- Detect missing files
- Search and relink files automatically
- Relocate entire projects to new paths
- Reorganize scattered media into clean structures
- Create custom repair workflows for specific needs

Always backup before modifying project files, and test repairs on copies first.
