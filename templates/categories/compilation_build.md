### Category: Compilation and Build Systems

Tasks involving building software from source, resolving dependencies, cross-compilation, and fixing build system issues.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Traditional Build:*
- Build legacy software from source (handle outdated dependencies, deprecated APIs)
- Cross-compile for different architectures (MIPS, ARM, RISC-V, WebAssembly)
- Fix broken build configurations (Makefile, CMake, Cargo, Meson)
- Resolve dependency conflicts and version mismatches
- Build software without optional dependencies (e.g., GUI-less builds, no X11)
- Compile verified/certified compilers or formal verification tools (CompCert, Coq)
- Fix native extension build issues (Cython with NumPy version conflicts)
- Create reproducible builds for complex projects
- Port software to new platforms or compilers
- Build with code coverage instrumentation (gcov, lcov)

*Container Build (Static Analysis):*
- Analyze and optimize Dockerfiles (reduce layers, minimize image size)
- Fix Dockerfile syntax errors and best practice violations
- Validate docker-compose.yml configurations
- Analyze container image layers (given as tar archives)
- Fix multi-stage build configurations
- Optimize build cache usage in Dockerfiles
- Validate Kubernetes YAML manifests and Helm charts
- Fix OCI image specification issues

**Skills & Tools** (tag suggestions for your task):
- Core: `compilation`, `build-tools`, `dependency`, `container-build`
- Build systems: `make`, `cmake`, `cargo`, `meson`, `bazel`, `configure`
- Compilers: `gcc`, `clang`, `cross-compilation`, `ocaml`
- Package managers: `apt`, `pip`, `npm`, `ocamlfind`, `opam`
- Container: `dockerfile`, `docker-compose`, `kubernetes`, `helm`

**Possible Input Data** (be creative with environment files!):
- Source tarballs from package archives (Debian, PyPI, crates.io)
- Broken Makefiles or CMakeLists.txt to fix
- Cross-compilation toolchain configurations
- Dependency specification files (requirements.txt, Cargo.toml, setup.py)
- Legacy source code with outdated APIs (C89, Python 2)
- Build logs showing errors to diagnose
- Patch files to apply during build
- Cython/C extension source files (.pyx, .c)
- OCaml/Coq source code requiring specific toolchains
- Dockerfiles with issues to analyze and fix
- docker-compose.yml files with configuration errors
- Container image layer tar archives for analysis
- Kubernetes YAML manifests with validation errors
- Helm chart templates with issues

**Verification Approaches**:
- Check binary exists and is executable
- Verify no forbidden dependencies (e.g., `ldd` shows no X11, no libGL)
- Test basic functionality of built software
- Check build uses correct source (e.g., from Debian repos, not upstream)
- Verify cross-compiled binary runs on target architecture/emulator
- Check gcov coverage files are generated
- Dockerfile passes linting (hadolint)
- docker-compose.yml is valid YAML and passes schema validation
- Kubernetes manifests pass kubectl validation
- Container image analysis shows expected layers/size

**Remember**: Build tasks test understanding of compilation pipelines, dependency management, and container configuration. For container-related tasks, focus on static analysis (Dockerfile/YAML fixing) rather than running Docker, since tasks execute inside containers.

**Important for Container Tasks**: Since tasks run inside containers, avoid tasks requiring Docker daemon access. Instead, focus on:
- Analyzing/fixing Dockerfiles as text files
- Validating docker-compose.yml syntax and configuration
- Analyzing pre-exported container image tars
- Fixing Kubernetes/Helm configurations
