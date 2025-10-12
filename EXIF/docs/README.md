# EXIF Tools Documentation

Comprehensive documentation for the EXIF photo processing and metadata tools - part of the photo-scripts monorepo.

## 📋 Quick Navigation

| Section | Description | Links |
|---------|-------------|--------|
| **Quick Start** | Basic usage and examples | [Getting Started](#-quick-start) |
| **User Guides** | End-to-end workflows and optimization | [Guides](guides/) |
| **Testing** | Testing strategy and coverage | [Testing Documentation](#-testing-documentation) |
| **Analysis** | Technical analysis and enhancements | [Analysis](analysis/) |
| **Project Overview** | Main project information | [Main README](../README.md) |

## 🚀 Quick Start

### Environment Setup
```bash
# Setup environment
./setenv --recreate
source activate.sh
inv setup
```

### Core Operations
```bash
# Organize photos by date and format
python scripts/organize.py /source/photos /target/organized --dry-run

# Generate test images from CSV data  
python scripts/generate.py test_data.csv /output/images --sample 10

# Select random photo samples
python scripts/select.py /source/photos /output/samples --files 50 --folders 5

# Analyze photo metadata
python scripts/analyze.py /source/photos --output analysis.csv

# Set image dates from CSV
python scripts/set_image_dates.py dates.csv --dry-run
```

### Using Invoke Tasks
```bash
# Run scripts via invoke (recommended)
inv run --script organize --args '/source /target --dry-run'
inv run --script generate --args 'data.csv /output --sample 10'
inv scripts  # List all available scripts
```

## 🏗️ Documentation Structure

```
EXIF/docs/
├── README.md                           # This overview (you are here)
├── TESTING_STRATEGY.md                 # Comprehensive testing approach
├── TEST_COVERAGE.md                    # Detailed coverage reports
├── guides/                             # User and developer guides
│   ├── WORKFLOW_GUIDE.md              # End-to-end usage workflows
│   └── PERFORMANCE_OPTIMIZATION_GUIDE.md # Performance tuning
└── analysis/                          # Technical analysis documents
    ├── ANALYZE_REFACTORING_SUMMARY.md # Code refactoring analysis
    ├── ANALYZER_COMPARISON.md         # Tool comparison studies
    └── OPTIONAL_TARGET_ENHANCEMENT.md # Enhancement proposals
```

## 🛠️ Available Tools

### Core Scripts

| Script | Purpose | Key Features |
|--------|---------|--------------|
| **`organize.py`** | Photo organization by date/format | Dry-run mode, EXIF date extraction, format-based folders |
| **`generate.py`** | Test image generation | CSV-driven, multiple formats, EXIF metadata injection |
| **`select.py`** | Random photo sampling | Multi-stage selection, sidecar file handling |
| **`analyze.py`** | Photo metadata analysis | Comprehensive EXIF data, CSV export, "Set Date" column |
| **`set_image_dates.py`** | Batch date correction | CSV-based, automatic extension fixing, dry-run support |

### Supporting Classes

| Class | Purpose | Location |
|-------|---------|----------|
| **`ImageData`** | EXIF metadata extraction | `src/exif/image_data.py` |
| **`PhotoOrganizer`** | Photo organization logic | `src/exif/photo_organizer.py` |
| **`ImageGenerator`** | Test image creation | `src/exif/image_generator.py` |
| **`ImageSelector`** | Photo sampling logic | `src/exif/image_selector.py` |

## 📖 User Guides

### **[Workflow Guide](guides/WORKFLOW_GUIDE.md)**
Complete end-to-end workflows for common use cases:
- Photo organization workflows
- Test data generation
- Batch processing patterns
- Integration with external tools

### **[Performance Optimization Guide](guides/PERFORMANCE_OPTIMIZATION_GUIDE.md)** 
Performance tuning and optimization strategies:
- Large dataset handling
- Memory optimization
- Processing speed improvements
- Resource management

## 🧪 Testing Documentation

### **[Testing Strategy](TESTING_STRATEGY.md)**
Comprehensive testing methodology covering:
- **90+ Tests**: Unit tests, integration tests, end-to-end validation
- **Multi-layer Approach**: Business logic, CLI interfaces, workflows
- **Test Categories**: Functionality, interface, integration testing
- **Quality Assurance**: 100% test success rate, comprehensive coverage

### **[Test Coverage](TEST_COVERAGE.md)**
Detailed test coverage analysis:
- Coverage metrics and goals
- Test execution reports
- Coverage gaps and improvements
- Continuous testing practices

## 🔍 Technical Analysis

### **[Refactoring Analysis](analysis/ANALYZE_REFACTORING_SUMMARY.md)**
Analysis of code refactoring and architectural improvements:
- Code quality improvements
- Architecture evolution
- Performance enhancements
- Technical debt reduction

### **[Tool Comparison](analysis/ANALYZER_COMPARISON.md)**
Comparative analysis of different photo processing approaches:
- Tool evaluation criteria
- Performance comparisons
- Feature analysis
- Recommendation matrix

### **[Enhancement Proposals](analysis/OPTIONAL_TARGET_ENHANCEMENT.md)**
Future enhancement proposals and technical improvements:
- Feature roadmap
- Technical enhancements
- Integration opportunities
- Implementation strategies

## 🏗️ Project Architecture

### Framework Integration
This project builds on the **COMMON framework** for:
- **Shared Infrastructure**: Logging, tasks, configuration
- **Standard Patterns**: Import patterns, error handling, testing
- **Development Tools**: Virtual environments, script runner

For framework details, see [COMMON Documentation](../../COMMON/docs/README.md).

### Project Structure
```
EXIF/
├── src/exif/                    # Core business logic
│   ├── image_data.py           # EXIF metadata processing
│   ├── photo_organizer.py      # Photo organization
│   ├── image_generator.py      # Test image generation
│   └── image_selector.py       # Photo sampling
├── scripts/                     # Executable scripts
│   ├── organize.py             # Main organization tool
│   ├── generate.py             # Image generation
│   ├── select.py               # Photo sampling
│   ├── analyze.py              # Metadata analysis
│   └── set_image_dates.py      # Date correction
├── tests/                       # Comprehensive test suite
├── docs/                       # This documentation
└── pyproject.toml              # Project configuration
```

## 📊 Key Features

### EXIF Metadata Processing
- **Comprehensive Extraction**: Date, time, camera info, GPS data
- **Format Support**: JPEG, PNG, TIFF, HEIC, MOV, and more
- **Error Handling**: Graceful handling of missing or corrupt metadata
- **ExifTool Integration**: Advanced metadata processing capabilities

### Photo Organization
- **Date-based Organization**: Automatic folder creation by date
- **Format Separation**: Organize by file type and format
- **Dry-run Mode**: Preview operations before execution
- **Statistics Tracking**: Detailed operation reporting

### Image Generation
- **CSV-driven**: Generate images from structured data
- **Multiple Formats**: Support for various image formats
- **EXIF Injection**: Embed custom metadata in generated images
- **Batch Processing**: Efficient bulk image creation

### Photo Sampling
- **Multi-stage Selection**: Sophisticated sampling algorithms
- **Sidecar Handling**: Preserves associated files (.xmp, .aae, etc.)
- **Flexible Criteria**: File count, folder limits, custom filters
- **Statistics Reporting**: Detailed selection metrics

## 🔧 Development Patterns

### Standard Script Template
All EXIF scripts follow the established COMMON framework patterns:
```python
# Standard imports and error handling
# ScriptLogging integration
# Argument parsing with argparse
# Business logic separation
# Comprehensive error handling
```

### Testing Approach
- **Business Logic Tests**: Unit tests for core classes
- **CLI Interface Tests**: Integration tests for script interfaces  
- **End-to-End Tests**: Complete workflow validation
- **Real Data Tests**: Testing with actual image files

### Code Quality
- **Type Hints**: Full type annotations
- **Documentation**: Comprehensive docstrings and comments
- **Error Handling**: Specific exceptions with proper logging
- **Performance**: Optimized for large dataset processing

## 🚀 Getting Started for Developers

### Development Environment
```bash
# Setup development environment
./setenv --recreate
source activate.sh
inv setup

# Run tests
inv test

# Check code quality
inv lint
```

### Adding New Features
1. **Follow Framework Patterns**: Use COMMON framework standards
2. **Write Tests First**: Comprehensive test coverage
3. **Document Changes**: Update relevant documentation
4. **Performance Testing**: Validate with large datasets

### Contribution Guidelines
- Follow established patterns and architecture
- Maintain comprehensive test coverage
- Update documentation for new features
- Use type hints and proper error handling

## 🔗 Related Documentation

### Framework Documentation
- **[COMMON Framework](../../COMMON/docs/README.md)**: Shared infrastructure
- **[COMMON Architecture](../../COMMON/docs/ARCHITECTURE.md)**: Technical details

### Project Documentation  
- **[Main Project README](../../docs/README.md)**: Project overview
- **[Setup Guide](../../docs/setup/SETUP_GUIDE.md)**: Installation instructions
- **[Development History](../../docs/development/DEVELOPMENT_HISTORY.md)**: Project context

### External Resources
- **ExifTool Documentation**: Advanced metadata processing
- **PIL/Pillow Documentation**: Image processing capabilities
- **Pytest Documentation**: Testing framework reference

---

*For technical implementation details, see the individual guide documents. For project-wide context, see the [main documentation](../../docs/README.md).*