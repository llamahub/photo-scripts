# Sample Script Evolution

This document traces the evolution of the sample.py script from bash to Python, highlighting key architectural decisions.

## Original Bash Script (select.sh)

The original bash script provided basic image sampling functionality:
- Random file selection from directory trees
- Basic folder structure preservation
- Limited error handling
- Shell-based file operations

## Python Conversion Goals

1. **Enhanced Functionality**: Multi-stage sampling algorithm
2. **Better Error Handling**: Comprehensive error catching and reporting
3. **Logging Integration**: Professional logging with file and console output
4. **Sidecar Support**: Automatic detection and copying of metadata files
5. **Testing Coverage**: Comprehensive unit test suite
6. **Type Safety**: Full type hints and validation

## Implementation Evolution

### Phase 1: Basic Conversion
- Direct translation of bash logic to Python
- `pathlib.Path` for cross-platform file handling
- `argparse` for command-line interface
- Basic functionality preservation

### Phase 2: Algorithm Enhancement
Multi-stage sampling strategy:
1. **Stage 1**: Sample from subfolders (respects `max_folders`, `max_per_folder`)
2. **Stage 2**: Fill from root directory if needed
3. **Stage 3**: Fill from entire tree if still needed

```python
def select_files(self) -> List[Path]:
    """Select image files using the multi-stage sampling strategy."""
    selected_files = []
    seen_files: Set[Path] = set()
    
    # Stage 1: Sample from subfolders
    subfolders = self.get_subfolders(self.source, self.max_depth)
    random.shuffle(subfolders)
    selected_subfolders = subfolders[:self.max_folders]
    
    # ... implementation continues
```

### Phase 3: Sidecar Detection
Intelligent metadata file detection:
- Standard sidecars: `.xmp`, `.yml`, `.yaml`
- Google Takeout JSON files
- Custom naming patterns

```python
def find_sidecars(self, image_path: Path) -> List[Path]:
    """Find sidecar files associated with an image."""
    sidecars = []
    image_stem = image_path.stem
    image_dir = image_path.parent
    
    # Standard sidecars (same base name)
    for ext in self.SIDECAR_EXTENSIONS:
        sidecar = image_dir / f"{image_stem}{ext}"
        if sidecar.exists():
            sidecars.append(sidecar)
    
    # Google Takeout style JSON files
    for json_file in image_dir.glob("*.json"):
        if image_stem in json_file.stem:
            sidecars.append(json_file)
```

### Phase 4: Logging Integration
Evolution from custom logging to COMMON framework:

#### Custom Implementation (Phase 4a)
```python
def log(self, message: str, to_console: bool = True):
    """Log message to file and optionally to console."""
    with open(self.log_file, 'a', encoding='utf-8') as f:
        f.write(f"{message}\n")
    if to_console or self.debug:
        print(message)
```

#### Manual COMMON-style (Phase 4b)
```python
def _setup_logger(self, name: str, log_file: Path, debug: bool = False) -> Logger:
    """Setup logger with file and console handlers in COMMON style."""
    logger = logging.getLogger(name)
    # ... manual handler setup
```

#### COMMON ScriptLogging (Phase 4c - Final)
```python
if ScriptLogging:
    self.logger = ScriptLogging.get_script_logger(
        name=f"sample_{timestamp}",
        log_dir=self.log_dir,
        debug=debug
    )
else:
    self.logger = self._setup_logger_fallback(name, debug)
```

## Testing Evolution

Comprehensive test suite development:

### Test Structure
```python
class TestImageSampler:
    """Test cases for the ImageSampler class."""
    
    def test_init(self, temp_dirs):
        """Test ImageSampler initialization."""
    
    def test_is_image_file(self):
        """Test image file detection."""
    
    def test_find_images(self, temp_dirs):
        """Test image discovery functionality."""
    
    def test_select_files(self, temp_dirs):
        """Test file selection algorithm."""
    
    def test_copy_file_with_metadata(self, temp_dirs):
        """Test file copying with sidecars."""
    
    def test_logging(self, temp_dirs):
        """Test logging functionality."""

class TestMainFunction:
    """Test cases for the main function and argument parsing."""
```

### Coverage Achievement
- 21 comprehensive tests
- 96%+ code coverage
- Edge case handling
- Mock-based isolation
- Temporary directory fixtures

## Key Design Decisions

### Class-Based Architecture
```python
class ImageSampler:
    """Handles sampling and copying of image files with their sidecars."""
    
    # Configuration constants
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.heic'}
    SIDECAR_EXTENSIONS = {'.xmp', '.yml', '.yaml'}
    
    def __init__(self, source: Path, target: Path, **kwargs):
        # Instance configuration
    
    def run(self):
        # Main execution flow
```

**Rationale**: Encapsulation, testability, state management

### Multi-Stage Sampling Algorithm
**Problem**: Simple random sampling doesn't respect folder distribution preferences
**Solution**: Staged approach with configurable limits per stage

### Comprehensive Error Handling
```python
try:
    # File operations
except PermissionError as e:
    self.logger.warning(f"Permission denied accessing {directory}: {e}")
except Exception as e:
    self.logger.error(f"Error copying {source_file}: {e}")
```

### Type Safety
Full type hints throughout:
```python
def select_files(self) -> List[Path]:
def find_sidecars(self, image_path: Path) -> List[Path]:
def copy_file_with_metadata(self, source_file: Path) -> None:
```

## Integration with Framework

### Import Pattern
```python
# Import COMMON logging
common_src_path = Path(__file__).parent.parent.parent / 'COMMON' / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    ScriptLogging = None
```

### Fallback Strategy
Graceful degradation when COMMON is unavailable:
```python
if ScriptLogging:
    # Use full COMMON functionality
else:
    # Use simplified fallback
```

### Task Integration
Script is available through the shared task system:
- `inv r -n sample -a '--help'`
- `invoke run --script sample --args '--help'`
- Direct execution

## Performance Characteristics

### File System Operations
- Efficient `os.walk()` for directory traversal
- `pathlib.Path` for cross-platform compatibility
- Lazy evaluation where possible

### Memory Usage
- Generator patterns for large file lists
- Minimal memory footprint for metadata
- Efficient random sampling

### Execution Time
- O(n) directory traversal
- O(k) file copying where k = selected files
- Minimal overhead for logging

## Future Enhancements

### Potential Improvements
1. **Parallel Processing**: Multi-threaded file copying
2. **Progress Reporting**: Real-time progress for large operations
3. **Configuration Files**: YAML/TOML configuration support
4. **Plugin System**: Extensible sidecar detection
5. **Database Integration**: Track sampling history

### Architectural Considerations
- Maintain backward compatibility
- Preserve test coverage
- Follow COMMON framework patterns
- Ensure cross-platform support

## Lessons Learned

### Development Process
1. **Incremental Development**: Small, testable changes
2. **Test-Driven**: Write tests alongside features
3. **Framework Integration**: Leverage shared infrastructure
4. **Documentation**: Comprehensive inline documentation

### Technical Insights
1. **Error Handling**: Graceful degradation is crucial
2. **Logging**: Structured logging pays dividends
3. **Type Safety**: Type hints catch errors early
4. **Testing**: Comprehensive tests enable confident refactoring

### Framework Benefits
1. **Consistency**: Shared patterns across scripts
2. **Maintainability**: Single source of truth for common code
3. **Developer Experience**: Simple, predictable APIs
4. **Extensibility**: Easy to add new functionality

This evolution demonstrates how a simple bash script can grow into a robust, well-tested Python application while benefiting from shared framework infrastructure.