### Category: Code Audit and Security Review

Tasks involving security code review, vulnerability identification, bug fixing, and secure coding practices.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Identify vulnerabilities in source code (CWE classification)
- Fix security bugs without breaking functionality
- Review and improve input validation
- Implement secure alternatives to vulnerable code
- Analyze dependencies for known vulnerabilities
- Create security filters (XSS, injection prevention)
- Audit authentication/authorization logic
- Fix memory safety issues (buffer overflow, use-after-free, memory leaks)
- Identify race conditions and concurrency bugs
- Review cryptographic implementations for weaknesses

**Skills & Tools** (tag suggestions for your task):
- Core: `security`, `coding`, `software-engineering`
- Analysis: `static-analysis`, `code-review`, `vulnerability-assessment`
- Standards: `cwe`, `owasp`, `secure-coding`
- Memory: `valgrind`, `asan`, `msan`

**Possible Input Data** (be creative with environment files!):
- Vulnerable source code (Python, C, JavaScript, Go with flaws)
- Web applications (HTML/JS with XSS, PHP with SQL injection)
- C/C++ code with memory management issues
- Configuration files (`.env`, `config.yaml` with exposed secrets)
- Dependency manifests with vulnerable packages
- API implementations with auth bypass issues
- Crypto code with timing attacks or weak randomness
- Serialization code with deserialization flaws
- Legacy code (COBOL, old PHP, CGI scripts)
- Test suites (existing tests the fix must not break)
- Vulnerability report format templates (JSONL with CWE-ID)

**Verification Approaches**:
- Check report contains correct CWE/CVE identification
- Verify vulnerability is actually fixed
- Confirm original functionality tests still pass
- Test that fix blocks the attack vector
- Valgrind/AddressSanitizer clean runs
- Static analysis tool passing

**Remember**: These are just starting points. Create realistic code audit scenarios from different languages and frameworks!
