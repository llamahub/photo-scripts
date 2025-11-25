# VPD Repair Script

## Overview

The `repair.py` script automatically repairs VideoProc Vlogger project files (.vpd) by finding and fixing missing media file references. It's particularly useful when:

- Files have been moved to different directories
- Files have been converted between formats (e.g., HEIC → JPG)
- Projects have been relocated to different computers
- Media files have been reorganized into new folder structures

## Features

✅ **Automatic File Discovery**: Searches project directory tree for missing files  
✅ **Format Conversion Handling**: Finds files even if extension changed (HEIC → JPG)  
✅ **Backup Protection**: Creates backup before modifying (recommended)  
✅ **Dry Run Mode**: Preview changes without modifying files  
✅ **Comprehensive Logging**: Detailed logs of all repair operations  
✅ **Multi-Media Support**: Handles images, video, and audio files  

## Quick Start

### Basic Usage

Repair a project file (creates backup automatically):
```bash
. run repair project.vpd --backup
```

### Preview Changes (Dry Run)

See what would be fixed without making changes:
```bash
. run repair project.vpd --dry-run
```

### Specify Search Directory

Search for files in a specific directory:
```bash
. run repair project.vpd --search-root /path/to/media
```

### Save to Different File

Create a repaired copy instead of modifying original:
```bash
. run repair project.vpd --output repaired.vpd
```

## Usage Patterns

### Pattern 1: Safe Repair with Backup
```bash
# Repairs the project and creates project.vpd.backup
. run repair project.vpd --backup
```

### Pattern 2: Test First, Then Repair
```bash
# Step 1: Preview what will be fixed
. run repair project.vpd --dry-run --verbose

# Step 2: If satisfied, run the actual repair
. run repair project.vpd --backup
```

### Pattern 3: Custom Search Location
```bash
# Search for missing files in a specific directory tree
. run repair project.vpd --search-root /Users/john/Movies/Media --backup
```

### Pattern 4: Create Repaired Copy
```bash
# Creates a new repaired file, leaves original untouched
. run repair project.vpd --output project_fixed.vpd
```

## Command Line Arguments

### Required Arguments

| Argument | Description |
|----------|-------------|
| `input_file` | Path to the .vpd or .dvp project file to repair |
| `--input FILE` | Alternative way to specify input file |

### Optional Arguments

| Argument | Description |
|----------|-------------|
| `--search-root DIR` | Root directory to search for missing files (default: parent of project) |
| `--output FILE` | Output file path (default: overwrites input) |
| `--backup` | Create backup before modifying (recommended) |
| `--no-backup` | Skip backup creation (not recommended) |
| `--dry-run` | Show what would be done without making changes |
| `--verbose, -v` | Enable detailed debug output |
| `--quiet, -q` | Suppress non-error output |

## How It Works

### 1. Load Project
- Reads and parses the .vpd JSON file
- Extracts all media resource references from:
  - Image list (scapegoat section)
  - Audio list (subitems)
  - Video list (scapegoat section)

### 2. Verify Files
- Checks each referenced file path
- Identifies which files exist and which are missing
- Reports summary of file status

### 3. Search for Missing Files
- For each missing file, searches the project directory tree
- First tries exact filename match
- If not found, tries stem match (different extension)
- Example: `photo.heic` will match `photo.jpg`

### 4. Update Paths
- Updates the VPD file with corrected file paths
- Preserves all other project data (edits, effects, timeline)
- Maintains resource UUIDs and links

### 5. Save Results
- Creates backup if requested
- Saves repaired project file
- Logs all changes made

## Output Examples

### Healthy Project
```
✅ Project is healthy - all 127 files found
```

### Successful Repair
```
✅ Repaired 3 of 3 missing files
📦 Backup saved: project.vpd.backup
💾 Saved to: project.vpd
```

### Partial Repair
```
⚠️  Repaired 8 of 10 missing files
   Could not find:
   - old_photo.jpg (image)
   - soundtrack.mp3 (audio)
```

### Dry Run
```
🔍 [DRY RUN] Would fix 5 of 5 missing files
   photo1.jpg → samples/media/photo1.jpg
   photo2.heic → samples/media/photo2.jpg
   music.mp3 → samples/audio/music.mp3
```

## Common Scenarios

### Scenario 1: Files Moved to Subfolder
**Problem**: All photos were in `/Images/` but moved to `/Images/selected/`

**Solution**:
```bash
. run repair project.vpd --backup
```
The script automatically searches subdirectories and finds the files.

### Scenario 2: HEIC Converted to JPG
**Problem**: iPhone photos converted from HEIC to JPG format

**Solution**:
```bash
. run repair project.vpd --backup
```
The script finds JPG files even when VPD references HEIC.

### Scenario 3: Project Moved to New Computer
**Problem**: Paths reference old computer's directory structure

**Solution**:
```bash
# Specify where media files are now located
. run repair project.vpd --search-root /Users/newuser/Movies --backup
```

### Scenario 4: Media Scattered Across Folders
**Problem**: Files in multiple unrelated directories

**Solution**:
```bash
# First organize files into one location, then repair
mkdir organized_media
mv /path/to/scattered/files/* organized_media/
. run repair project.vpd --search-root organized_media --backup
```

## Best Practices

### ✅ DO:
- **Always create backups** before modifying VPD files
- **Test with --dry-run** first to preview changes
- **Close VideoProc Vlogger** before running repair
- **Keep media files organized** in project subdirectories
- **Use verbose mode** (`-v`) when troubleshooting

### ❌ DON'T:
- Don't edit VPD files while VideoProc Vlogger is open
- Don't skip backups on important projects
- Don't delete backup files until verifying repair worked
- Don't move files after repair without re-running script

## Troubleshooting

### Issue: "No files could be repaired"
**Cause**: Files not in search path or too different from original names

**Solution**: 
- Use `--search-root` to specify correct directory
- Check that file basenames match (stem before extension)
- Use `--verbose` to see search details

### Issue: "Invalid JSON in VPD file"
**Cause**: VPD file is corrupted or manually edited incorrectly

**Solution**: 
- Restore from backup if available
- Validate JSON syntax with `python3 -m json.tool project.vpd`
- Check for missing commas, brackets, or quotes

### Issue: "Multiple matches found"
**Cause**: Multiple files with same name in different locations

**Solution**: 
- Script uses first match (logged in verbose mode)
- Manually specify which file to use by organizing files first
- Or accept first match and verify in VideoProc Vlogger

## Log Files

All operations are logged to `.log/repair_YYYYMMDD_HHMMSS.log`

View recent repair logs:
```bash
ls -lt .log/repair_*.log | head
```

Check specific repair operation:
```bash
cat .log/repair_20251122_143022.log
```

## Integration with Other Scripts

The repair script integrates with other VIDEOPROC workflow:

```bash
# 1. Organize media files first (if needed)
. run organize_media project.vpd organized/

# 2. Repair project with new paths
. run repair project.vpd --search-root organized/ --backup

# 3. Verify project health
. run repair project.vpd
```

## Technical Details

### VPD File Structure
The script understands VideoProc Vlogger's internal structure:
- **imagelist.scapegoat**: Image resource definitions
- **audiolist.subitems**: Audio resource definitions  
- **videolist.scapegoat**: Video resource definitions
- **UUID system**: Links between timeline and resources

### Search Algorithm
1. Exact filename match (case-insensitive)
2. Stem match (same name, different extension)
3. Returns all matches, uses first by default

### File Format Support
- **Images**: .jpg, .jpeg, .png, .heic, .tiff, .bmp
- **Video**: .mp4, .mov, .avi, .mkv
- **Audio**: .mp3, .wav, .m4a, .aac

## See Also

- [VPD_File_Structure_Analysis.md](../VPD_File_Structure_Analysis.md) - Detailed file format documentation
- [example_script.py](../scripts/example_script.py) - Script template and patterns
- [COMMON Framework](../../COMMON/docs/README.md) - Shared utilities documentation

## Support

For issues or questions:
1. Check log files in `.log/` directory
2. Run with `--verbose` for detailed output
3. Review [VPD_File_Structure_Analysis.md](../VPD_File_Structure_Analysis.md)
4. Check VideoProc Vlogger project opens correctly after repair
