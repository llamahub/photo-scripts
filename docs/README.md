# Photo Scripts Documentation

Complete documentation for the Photo Scripts monorepo - a Python framework for photo processing tools with shared infrastructure.

## 📋 Quick Navigation

| Section | Description | Links |
|---------|-------------|--------|
| **Getting Started** | Setup guides and installation | [Setup Guide](setup/SETUP_GUIDE.md) • [Troubleshooting](setup/SETUP_TROUBLESHOOTING.md) |
| **COMMON Framework** | Shared infrastructure documentation | [COMMON Docs](../COMMON/docs/) |
| **EXIF Tools** | Photo processing and metadata tools | [EXIF Docs](../EXIF/docs/) |
| **Development** | Project history and development notes | [Development History](development/DEVELOPMENT_HISTORY.md) |

## 🏗️ Documentation Structure

```
docs/
├── README.md                    # This overview (you are here)
├── setup/                       # Installation and setup guides
│   ├── SETUP_GUIDE.md          # Main installation guide
│   └── SETUP_TROUBLESHOOTING.md # Common issues and solutions
└── development/                 # Development documentation
    └── DEVELOPMENT_HISTORY.md   # Project evolution and decisions

COMMON/docs/                     # COMMON framework documentation
├── README.md                   # COMMON framework overview
└── ARCHITECTURE.md             # Technical architecture details

EXIF/docs/                      # EXIF project documentation  
├── README.md                   # EXIF project overview
├── TESTING_STRATEGY.md         # Testing approach and coverage
├── TEST_COVERAGE.md            # Detailed test coverage reports
├── guides/                     # User and developer guides
│   ├── WORKFLOW_GUIDE.md       # End-to-end workflow documentation
│   └── PERFORMANCE_OPTIMIZATION_GUIDE.md # Performance tuning
└── analysis/                   # Technical analysis documents
    ├── ANALYZE_REFACTORING_SUMMARY.md # Code refactoring analysis
    ├── ANALYZER_COMPARISON.md   # Tool comparison studies
    └── OPTIONAL_TARGET_ENHANCEMENT.md # Enhancement proposals
```

## 🚀 Getting Started

### New Users
1. **[Setup Guide](setup/SETUP_GUIDE.md)** - Complete installation instructions
2. **[EXIF Quick Start](../EXIF/docs/README.md#quick-start)** - Basic usage examples
3. **[COMMON Framework](../COMMON/docs/README.md)** - Understanding the shared infrastructure

### Developers
1. **[COMMON Architecture](../COMMON/docs/ARCHITECTURE.md)** - Framework technical details
2. **[Testing Strategy](../EXIF/docs/TESTING_STRATEGY.md)** - Testing approach and patterns
3. **[Development History](development/DEVELOPMENT_HISTORY.md)** - Project context and decisions

### Troubleshooting
- **[Setup Issues](setup/SETUP_TROUBLESHOOTING.md)** - Common installation problems
- **[Performance Guide](../EXIF/docs/guides/PERFORMANCE_OPTIMIZATION_GUIDE.md)** - Performance tuning
- **[Workflow Guide](../EXIF/docs/guides/WORKFLOW_GUIDE.md)** - End-to-end usage patterns

## 📚 Documentation Categories

### **Setup & Installation**
Complete guides for getting the system running across different environments.

- **Setup Guide**: Step-by-step installation for dev containers and local development
- **Troubleshooting**: Solutions for common installation and runtime issues

### **Framework Documentation** 
Technical documentation for the shared COMMON framework.

- **Architecture**: Logging system, task framework, script runner, configuration management
- **Patterns**: Standard import patterns, error handling, testing methodologies

### **EXIF Tools Documentation**
Comprehensive documentation for the photo processing tools.

- **User Guides**: Workflow documentation and performance optimization
- **Developer Guides**: Testing strategy, code coverage, refactoring analysis
- **Technical Analysis**: Enhancement proposals and tool comparisons

### **Development Resources**
Resources for contributors and maintainers.

- **Development History**: Context for architectural decisions and project evolution
- **Testing Documentation**: Comprehensive testing strategy and coverage reports

## 🔗 Cross-References

### Common Tasks
- **Environment Setup**: [Setup Guide](setup/SETUP_GUIDE.md) → [COMMON Framework](../COMMON/docs/README.md)
- **Script Development**: [COMMON Architecture](../COMMON/docs/ARCHITECTURE.md) → [Testing Strategy](../EXIF/docs/TESTING_STRATEGY.md)
- **Photo Processing**: [EXIF Overview](../EXIF/docs/README.md) → [Workflow Guide](../EXIF/docs/guides/WORKFLOW_GUIDE.md)

### Technical Deep Dives
- **Framework Understanding**: [Architecture](../COMMON/docs/ARCHITECTURE.md) → [Development History](development/DEVELOPMENT_HISTORY.md)
- **Testing Approach**: [Testing Strategy](../EXIF/docs/TESTING_STRATEGY.md) → [Test Coverage](../EXIF/docs/TEST_COVERAGE.md)
- **Performance Tuning**: [Performance Guide](../EXIF/docs/guides/PERFORMANCE_OPTIMIZATION_GUIDE.md) → [Analysis Reports](../EXIF/docs/analysis/)

## 📝 Contributing to Documentation

When adding new documentation:

1. **Choose the Right Location**:
   - Root `docs/`: Project-wide documentation
   - `COMMON/docs/`: Framework-specific documentation  
   - `EXIF/docs/`: Tool-specific documentation

2. **Follow Naming Conventions**:
   - Use `UPPER_CASE.md` for major documents
   - Use descriptive names that indicate scope and purpose
   - Group related documents in subdirectories

3. **Update Navigation**:
   - Add links to this overview README
   - Update relevant project README files
   - Maintain cross-references between related documents

4. **Maintain Consistency**:
   - Use established documentation patterns
   - Include proper headers and navigation
   - Provide context and cross-links

---

*For questions about documentation organization or to suggest improvements, refer to the [Development History](development/DEVELOPMENT_HISTORY.md) for context on architectural decisions.*