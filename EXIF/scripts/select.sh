#!/bin/bash

# Usage: select.sh [source] [target] [files] [folders] [depth] [perfolder] [--clean]
#        or with named args: --source DIR --target DIR --files N --folders N --depth N --perfolder N --clean

usage() {
  echo "Usage: $0 [source] [target] [--files N] [--folders N] [--depth N] [--perfolder N] [--clean] [--debug]"
  echo "       or: $0 --source DIR [--target DIR] [--files N] [--folders N] [--depth N] [--perfolder N] [--clean] [--debug]"
  echo "  source     Root source folder (required)"
  echo "  target     Root target folder (default: /mnt/photo_drive/Test-input)"
  echo "  --files      Max number of files (default: 10)"
  echo "  --folders    Max number of subfolders (default: 3)"
  echo "  --depth      Max depth of subfolders (default: 2)"
  echo "  --perfolder  Max number of image files per subfolder (default: 2, sidecars not counted)"
  echo "  --clean    If provided, delete everything from target first"
  echo "  --debug    Enable debug output"
  exit 1
}

# Defaults
TARGET="/mnt/photo_drive/Test-input"
FILES=10
FOLDERS=3
DEPTH=2
CLEAN=0
PERFOLDER=2
DEBUG=0

declare -A PERFOLDER_COUNT

# Parse args (positional or named)
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --source)
      SOURCE="$2"; shift 2;;
    --target)
      TARGET="$2"; shift 2;;
    --files)
      FILES="$2"; shift 2;;
    --folders)
      FOLDERS="$2"; shift 2;;
    --depth)
      DEPTH="$2"; shift 2;;
    --clean)
      CLEAN=1; shift;;
    --perfolder)
      PERFOLDER="$2"; shift 2;;
    --debug)
      DEBUG=1; shift;;
    -h|--help)
      usage;;
    --)
      shift; break;;
    -*)
      echo "Error: Unknown argument: $1" >&2
      usage
      ;;
    *)
      POSITIONAL+=("$1")
      shift;;
  esac
  
done

# Only allow up to 2 positional arguments (source and target)
if [[ ${#POSITIONAL[@]} -gt 2 ]]; then
  echo "Error: Too many positional arguments: ${POSITIONAL[@]:2}" >&2
  usage
fi

# Always assign positional args first
if [[ ${#POSITIONAL[@]} -ge 1 ]]; then SOURCE="${POSITIONAL[0]}"; fi
if [[ ${#POSITIONAL[@]} -ge 2 ]]; then TARGET="${POSITIONAL[1]}"; fi

# If unknown args remain, error
if [[ ${#POSITIONAL[@]} -gt 2 ]]; then
  echo "Error: Unknown argument: ${POSITIONAL[2]}" >&2
  usage
fi

if [[ -z "$SOURCE" ]]; then
  echo "Error: source folder is required" >&2
  usage
fi

if [[ ! -d "$SOURCE" ]]; then
  echo "Error: source folder '$SOURCE' does not exist" >&2
  exit 2
fi

LOGDIR=".log"
mkdir -p "$LOGDIR"
LOG_FILE="${LOGDIR}/select_log_$(date +%Y%m%d_%H%M%S).log"

{
  echo "================================================================================"
  echo " [select.sh] Select a random sample of image files from source" 
  echo "================================================================================"
  echo "SOURCE=${SOURCE}"
  echo "TARGET=${TARGET}"
  echo "FILES=${FILES}"
  echo "FOLDERS=${FOLDERS}"
  echo "DEPTH=${DEPTH}"
  echo "PERFOLDER=${PERFOLDER}"
  if [[ $CLEAN -eq 1 ]]; then
    echo "CLEAN mode enabled"
  fi
  if [[ $DEBUG -eq 1 ]]; then
    echo "DEBUG mode enabled"
  fi
} | tee "$LOG_FILE"

if [[ $CLEAN -eq 1 ]]; then
  msg="Cleaning target folder: $TARGET"
  echo "$msg" | tee -a "$LOG_FILE"
  rm -rf "$TARGET"/*
fi
mkdir -p "$TARGET"

# Only consider image files for selection
IMAGE_EXTS="jpg jpeg png bmp tif tiff heic"
find_images() {
  find "$1" -maxdepth "$2" -type f \( \
    -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.bmp' -o -iname '*.tif' -o -iname '*.tiff' -o -iname '*.heic' \
  \)
}

# Find up to FOLDERS subfolders (up to DEPTH) with at least one file, then randomly select FILES files from them
mapfile -t SUBFOLDERS < <(find "$SOURCE" -mindepth 1 -maxdepth "$DEPTH" -type d | shuf | head -n "$FOLDERS")
SELECTED_FILES=()
for folder in "${SUBFOLDERS[@]}"; do
  mapfile -t FILES_IN_FOLDER < <(find_images "$folder" 1 | shuf)
  count=0
  for img in "${FILES_IN_FOLDER[@]}"; do
    # Determine relative subfolder path for target
    rel_path="${img#$SOURCE/}"
    subfolder="$(dirname "$rel_path")"
    key="$subfolder"
    # Count how many files already selected for this subfolder
    n=${PERFOLDER_COUNT["$key"]:-0}
    if (( n < PERFOLDER )); then
      SELECTED_FILES+=("$img")
      PERFOLDER_COUNT["$key"]=$((n+1))
      ((count++))
      if [[ ${#SELECTED_FILES[@]} -ge $FILES ]]; then
        break 2
      fi
    fi
  done
  # If global file limit reached, break
  if [[ ${#SELECTED_FILES[@]} -ge $FILES ]]; then
    break
  fi
done
# If not enough, fill from root, avoiding duplicates
if [[ ${#SELECTED_FILES[@]} -lt $FILES ]]; then
  mapfile -t ROOT_FILES < <(find_images "$SOURCE" 1 | shuf)
  for root_file in "${ROOT_FILES[@]}"; do
    # Only add if not already selected
    skip=0
    for sel in "${SELECTED_FILES[@]}"; do
      if [[ "$root_file" == "$sel" ]]; then
        skip=1
        break
      fi
    done
    if [[ $skip -eq 0 ]]; then
      SELECTED_FILES+=("$root_file")
      if [[ ${#SELECTED_FILES[@]} -ge $FILES ]]; then
        break
      fi
    fi
  done
fi
# Final fill: if still not enough, fill from all images in the source tree (up to DEPTH), avoiding duplicates
if [[ ${#SELECTED_FILES[@]} -lt $FILES ]]; then
  mapfile -t ALL_IMAGES < <(find_images "$SOURCE" "$DEPTH" | shuf)
  for img in "${ALL_IMAGES[@]}"; do
    skip=0
    for sel in "${SELECTED_FILES[@]}"; do
      if [[ "$img" == "$sel" ]]; then
        skip=1
        break
      fi
    done
    if [[ $skip -eq 0 ]]; then
      SELECTED_FILES+=("$img")
      if [[ ${#SELECTED_FILES[@]} -ge $FILES ]]; then
        break
      fi
    fi
  done
fi
# Deduplicate SELECTED_FILES (in case of any accidental duplicates)
if [[ ${#SELECTED_FILES[@]} -gt 0 ]]; then
  declare -A seen
  deduped=()
  for f in "${SELECTED_FILES[@]}"; do
    if [[ -n "$f" && -z "${seen[$f]}" ]]; then
      deduped+=("$f")
      seen[$f]=1
    fi
  done
  SELECTED_FILES=("${deduped[@]}")
fi
# Limit to max files
SELECTED_FILES=("${SELECTED_FILES[@]:0:$FILES}")

# Copy files, preserving relative paths, and copy sidecars if present
for file in "${SELECTED_FILES[@]}"; do
  [[ -z "$file" ]] && continue
  rel_path="${file#$SOURCE/}"
  dest_dir="$TARGET/$(dirname "$rel_path")"
  mkdir -p "$dest_dir"
  cp -p "$file" "$dest_dir/"
  if [[ $DEBUG -eq 1 ]]; then
    echo "Copied '$file' to '$dest_dir/'" | tee -a "$LOG_FILE"
  else
    echo "Copied '$file' to '$dest_dir/'" >> "$LOG_FILE"
  fi
  # Copy sidecar if exists (same base name, .xmp or .json or .yml)
  for ext in xmp yml; do
    sidecar="${file%.*}.$ext"
    if [[ -f "$sidecar" ]]; then
      cp -p "$sidecar" "$dest_dir/"
      if [[ $DEBUG -eq 1 ]]; then
        echo "Copied sidecar '$sidecar' to '$dest_dir/'" | tee -a "$LOG_FILE"
      else
        echo "Copied sidecar '$sidecar' to '$dest_dir/'" >> "$LOG_FILE"
      fi
    fi
  done
  # Copy any .json file where the base name of the image is part of the sidecar name (Google Takeout style)
  base_noext="$(basename "${file%.*}")"
  dir_name="$(dirname "$file")"
  for json_sidecar in "$dir_name"/*.json; do
    if [[ -f "$json_sidecar" && "$json_sidecar" == *"$base_noext"* ]]; then
      cp -p "$json_sidecar" "$dest_dir/"
      if [[ $DEBUG -eq 1 ]]; then
        echo "Copied sidecar '$json_sidecar' to '$dest_dir/'" | tee -a "$LOG_FILE"
      else
        echo "Copied sidecar '$json_sidecar' to '$dest_dir/'" >> "$LOG_FILE"
      fi
    fi
  done
done

echo "Copied ${#SELECTED_FILES[@]} files to $TARGET" | tee -a "$LOG_FILE"
