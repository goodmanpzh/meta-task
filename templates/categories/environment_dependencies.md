### Category: Environment and Dependency Management

Tasks involving dependency resolution, version conflicts, environment configuration, and package management across different languages and platforms.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Build & Packaging:*
- Create a reproducible build environment from scratch using pyproject.toml and lockfiles
- Build a multi-language project setup with Python, Node.js, and system library dependencies
- Package a Python project with C extensions for distribution (wheel building, manylinux)
- Implement a custom dependency resolver that produces a valid lockfile from constraints

*Python Environment:*
- Resolve conflicting package versions in requirements.txt
- Migrate from requirements.txt to pyproject.toml
- Fix conda environment conflicts and channel priority issues
- Resolve numpy/scipy binary compatibility issues
- Debug import errors caused by package shadowing

*Node.js/JavaScript:*
- Fix npm/yarn/pnpm dependency conflicts
- Resolve peer dependency warnings and errors
- Debug node_modules resolution issues
- Fix package-lock.json/yarn.lock inconsistencies
- Handle native module compilation failures (node-gyp)
- Migrate between package managers while preserving lockfile

*System Libraries:*
- Resolve shared library conflicts (glibc, openssl, libssl)
- Fix LD_LIBRARY_PATH and rpath issues
- Debug symbol version conflicts (GLIBC_2.xx not found)
- Handle multiple library versions coexisting
- Fix pkg-config path issues

*Build Dependencies:*
- Separate compile-time and runtime dependencies
- Fix missing header files during compilation
- Resolve CMake/autoconf dependency detection issues
- Debug static vs dynamic linking problems

*Environment Configuration:*
- Fix PATH ordering issues
- Debug environment variable inheritance problems
- Handle .env file parsing and precedence
- Fix locale and encoding configuration (LC_ALL, LANG)
- Resolve XDG directory configuration issues

*Reproducibility:*
- Generate and verify dependency lockfiles
- Create reproducible build environments
- Debug "works on my machine" issues
- Implement dependency pinning strategies
- Verify dependency checksums and integrity

**Skills & Tools** (tag suggestions for your task):
- Core: `dependencies`, `package-management`, `environment`, `versioning`
- Python: `pip`, `virtualenv`, `conda`, `poetry`, `pyproject`
- Node: `npm`, `yarn`, `pnpm`, `node-gyp`
- System: `ldconfig`, `pkg-config`, `ldd`, `ld.so`
- Concepts: `version-resolution`, `lockfiles`, `reproducibility`

**Possible Input Data** (be creative with environment files!):
- requirements.txt/package.json with conflicting versions
- Error logs from failed installations
- Environment variable dumps
- ldd output showing missing libraries
- Lockfiles with inconsistencies
- Build logs with dependency errors
- Virtual environment configurations

**Verification Approaches**:
- All packages install without errors
- Import/require statements succeed
- No version conflict warnings
- Lockfile is consistent and valid
- Application runs correctly with resolved dependencies
- Environment is reproducible (same result on clean install)
- No deprecated package warnings (if specified)

**Remember**: Dependency and packaging tasks should test understanding of semantic versioning, build systems, and platform-specific issues. Include scenarios involving cross-platform builds, multi-language projects, or custom packaging — not just "fix conflicts"!
