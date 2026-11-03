### Category: Code Migration and Modernization

Tasks involving migrating code between languages, versions, or platforms while preserving functionality.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Migrate Python 2 code to Python 3 (handle unicode, print, division changes)
- Convert legacy languages to modern ones (COBOL to Python, Fortran to C)
- Port code between statistical languages (R to Python, RStan to PyStan)
- Migrate between ML frameworks (TensorFlow to PyTorch, Caffe to ONNX)
- Update code for new library versions (NumPy 1.x to 2.x, breaking API changes)
- Port shell scripts between platforms (bash to POSIX, Windows to Linux)
- Convert synchronous code to async (callbacks to async/await)
- Migrate database schemas and queries (MySQL to PostgreSQL)
- Port native extensions to pure implementations
- Update deprecated API usage to modern equivalents
- Convert between configuration formats (XML to YAML, INI to JSON)
- Migrate build systems (Makefile to CMake, setup.py to pyproject.toml)

**Skills & Tools** (tag suggestions for your task):
- Core: `migration`, `refactoring`, `compatibility`, `modernization`
- Languages: `python`, `cobol`, `fortran`, `r`, `javascript`
- Tools: `2to3`, `futurize`, `codemods`, `ast`
- Concepts: `api-compatibility`, `deprecation`, `backwards-compatibility`
- Frameworks: `pytorch`, `tensorflow`, `stan`, `numpy`

**Possible Input Data** (be creative with environment files!):
- Legacy source code (Python 2, COBOL, old R scripts)
- Old library version code requiring updates
- Test suites that must pass after migration
- API documentation for old and new versions
- Reference outputs for verification
- Configuration files in old formats
- Database schemas and sample data
- Dependency specifications (old requirements.txt)
- Build files requiring modernization
- Benchmark scripts for performance comparison

**Verification Approaches**:
- All original tests still pass after migration
- Output matches reference implementation exactly
- No deprecated warnings in migrated code
- Performance within acceptable range of original
- Static analysis clean (no legacy patterns)
- Correct handling of edge cases that differ between versions
- New APIs used correctly (not just wrapped)
- Build/install process works with modern tools

**Remember**: Migration tasks test understanding of both old and new systems. Include edge cases where behavior differs between versions. Verification should ensure both functional correctness and proper use of modern idioms!
