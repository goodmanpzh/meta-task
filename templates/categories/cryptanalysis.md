### Category: Cryptanalysis and Security Challenges

Tasks involving breaking encryption, analyzing cryptographic protocols, password cracking, and implementing cryptographic attacks.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Implement differential or linear cryptanalysis attacks on block ciphers
- Crack password-protected archives or encrypted files
- Recover encryption keys from partial information or side channels
- Break weak or simplified cryptographic schemes (reduced-round ciphers)
- Analyze and exploit timing or power side-channel vulnerabilities
- Implement chosen-plaintext or known-plaintext attacks
- Reverse engineer custom/proprietary encryption algorithms
- Perform digital forensics to recover deleted secrets from disk images
- Extract model parameters through query-based attacks (model extraction)
- Break hash functions or find collisions

**Skills & Tools** (tag suggestions for your task):
- Core: `cryptography`, `security`, `mathematics`
- Attacks: `differential-cryptanalysis`, `linear-cryptanalysis`, `brute-force`
- Tools: `john`, `hashcat`, `openssl`, `python-crypto`, `7z`
- Related: `forensics`, `reverse-engineering`, `binary-analysis`

**Possible Input Data** (be creative with environment files!):
- Encrypted archives (7z, zip with weak passwords)
- Cipher implementations to analyze (Python/C with intentional weaknesses)
- Chosen-plaintext oracle access (encryption functions to query)
- Plaintext-ciphertext pairs for known-plaintext attacks
- Disk images with deleted/encrypted files for forensics
- Binary executables with embedded secrets
- Hash files to crack (shadow files, database dumps)
- Timing information for side-channel attacks
- Machine learning models to extract (black-box API access)
- Reduced-round cipher implementations

**Verification Approaches**:
- Verify recovered key/password is correct (exact match)
- Test attack succeeds within time limit (<30 seconds)
- Check decrypted content matches expected
- Verify attack works on multiple test cases
- Measure attack complexity (queries, time, data needed)

**Remember**: Cryptanalysis tasks should test mathematical reasoning, algorithm design, and security mindset. Design attacks that are feasible but require insight and creativity!
