### Category: Security and CTF Challenges

Tasks involving security challenges, cryptography, password cracking, reverse engineering, and capture-the-flag style problems.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Cryptography & Cracking:*
- Crack encrypted files (7z, zip, PDF with password)
- Cryptanalysis (break weak or custom ciphers)
- Extract secrets from binaries or memory dumps

*Web Security:*
- Bypass security filters (XSS filter evasion, WAF bypass)
- Create XSS payloads that bypass sanitization
- Analyze obfuscated code to find secrets

*Forensics & Reverse Engineering:*
- Digital forensics and data recovery from disk images
- Reverse engineer executables to extract hidden flags
- Exploit known vulnerabilities (CVE reproduction)

*System Permissions & Access Control:*
- Analyze and fix Linux file permissions (chmod, chown, ACLs)
- Debug sudo configuration issues (sudoers syntax)
- Configure and troubleshoot SELinux/AppArmor policies
- Audit file permissions for security issues (world-writable, SUID)
- Fix SSH key permissions and configuration
- Analyze PAM configuration issues
- Debug capability-based permissions (setcap/getcap)
- Implement principle of least privilege for services

**Skills & Tools** (tag suggestions for your task):
- Core: `security`, `cryptography`, `reverse-engineering`, `permissions`
- Tools: `hashcat`, `john`, `binwalk`, `ghidra`, `radare2`, `strings`, `objdump`
- Permissions: `chmod`, `chown`, `setfacl`, `getfacl`, `sudo`, `setcap`, `getcap`
- Related: `forensics`, `steganography`, `network-analysis`, `selinux`, `apparmor`
- Web: `xss`, `html-parsing`, `javascript`

**Possible Input Data** (be creative with environment files!):
- Encrypted archives (`.7z`, `.zip`, `.rar`) with weak passwords
- Custom cipher implementations with intentional weaknesses
- Binary executables (ELF/PE) with hidden flags or obfuscation
- Memory dumps (`.raw`, `.dmp`) containing secrets
- Disk images (`.img`, `.dd`) with deleted files to recover
- Network captures (`.pcap`) with credentials
- Steganography images (PNG/JPEG with hidden data)
- Weak hash files (`/etc/shadow` style)
- HTML files with XSS filters to bypass
- Obfuscated JavaScript with hidden functionality
- Certificate files (`.pem`, `.p12`) with misconfigurations
- File system snapshots with permission issues
- sudoers files with syntax errors or security issues
- SELinux/AppArmor policy files
- SSH configuration files (sshd_config, authorized_keys)
- PAM configuration files

**Verification Approaches**:
- Check extracted secret/flag matches expected value (exact string match)
- Confirm XSS payload triggers in headless browser
- Verify recovered file contents match expected
- Test that bypass payload executes JavaScript
- Validate password/key correctness
- Verify file permissions match security requirements
- sudo configuration passes visudo validation
- Services run with minimal required privileges
- No world-writable files in sensitive locations
- SUID/SGID bits only where necessary

**Remember**: Create novel security challenges that test both offensive (CTF-style) and defensive (hardening, permissions) skills. Combine techniques or explore less common attack vectors!
