"""
Tests for the Merkle-Hellman knapsack cryptanalysis challenge.
Verifies that the agent correctly broke the encryption using lattice reduction.
"""
import os
import math
import pytest


def read_integers(filepath):
    """Read a file of integers, one per line."""
    with open(filepath) as f:
        return [int(line.strip()) for line in f if line.strip()]


def read_params(filepath):
    """Read key=value parameter file."""
    params = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                k, v = line.split('=', 1)
                params[k.strip()] = v.strip()
    return params


@pytest.fixture(scope="module")
def public_key():
    return read_integers('/app/data/public_key.txt')


@pytest.fixture(scope="module")
def ciphertexts():
    return read_integers('/app/data/ciphertexts.txt')


@pytest.fixture(scope="module")
def params():
    return read_params('/app/data/params.txt')


@pytest.fixture(scope="module")
def plaintext_bits():
    """Read the agent's plaintext bits output."""
    path = '/app/plaintext_bits.txt'
    if not os.path.exists(path):
        return None
    with open(path) as f:
        lines = [line.strip() for line in f if line.strip()]
    result = []
    for line in lines:
        bits = [int(x) for x in line.split()]
        result.append(bits)
    return result


@pytest.fixture(scope="module")
def decoded_message():
    """Read the agent's decoded message output."""
    path = '/app/decoded_message.txt'
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read()


# ============================================================
# Test 1: Output files exist
# ============================================================
class TestOutputFilesExist:
    def test_plaintext_bits_file_exists(self):
        assert os.path.exists('/app/plaintext_bits.txt'), \
            "Missing /app/plaintext_bits.txt"

    def test_decoded_message_file_exists(self):
        assert os.path.exists('/app/decoded_message.txt'), \
            "Missing /app/decoded_message.txt"

    def test_solution_file_exists(self):
        assert os.path.exists('/app/solution.py'), \
            "Missing /app/solution.py"


# ============================================================
# Test 2: Plaintext bits are valid binary vectors
# ============================================================
class TestBitVectorFormat:
    def test_correct_number_of_bit_vectors(self, plaintext_bits, ciphertexts):
        assert plaintext_bits is not None, "Could not read plaintext_bits.txt"
        assert len(plaintext_bits) == len(ciphertexts), \
            f"Expected {len(ciphertexts)} bit vectors, got {len(plaintext_bits)}"

    def test_correct_dimension(self, plaintext_bits, params):
        assert plaintext_bits is not None
        n = int(params['dimension'])
        for i, bits in enumerate(plaintext_bits):
            assert len(bits) == n, \
                f"Bit vector {i} has length {len(bits)}, expected {n}"

    def test_bits_are_binary(self, plaintext_bits):
        assert plaintext_bits is not None
        for i, bits in enumerate(plaintext_bits):
            for j, b in enumerate(bits):
                assert b in (0, 1), \
                    f"Bit vector {i}, position {j}: value {b} is not 0 or 1"


# ============================================================
# Test 3: Cryptographic verification — bits match ciphertexts
# ============================================================
class TestCryptographicCorrectness:
    def test_subset_sum_matches_ciphertext(self, plaintext_bits, public_key, ciphertexts):
        """Each bit vector dotted with the public key must equal its ciphertext."""
        assert plaintext_bits is not None
        for i, (bits, ct) in enumerate(zip(plaintext_bits, ciphertexts)):
            computed = sum(b * pk for b, pk in zip(bits, public_key))
            assert computed == ct, (
                f"Ciphertext {i}: subset sum = {computed}, "
                f"expected = {ct}. The bit vector is not a valid decryption."
            )


# ============================================================
# Test 4: Decoded message is valid ASCII
# ============================================================
class TestDecodedMessage:
    def test_message_length(self, decoded_message, params):
        assert decoded_message is not None, "Could not read decoded_message.txt"
        n = int(params['dimension'])
        num_ct = int(params['num_ciphertexts'])
        chars_per_block = int(params['chars_per_block'])
        expected_len = num_ct * chars_per_block
        assert len(decoded_message) == expected_len, \
            f"Decoded message length {len(decoded_message)}, expected {expected_len}"

    def test_message_is_printable_ascii(self, decoded_message):
        assert decoded_message is not None
        for i, ch in enumerate(decoded_message):
            assert 32 <= ord(ch) <= 126, (
                f"Character at position {i} (ord={ord(ch)}) "
                f"is not printable ASCII"
            )

    def test_message_consistency_with_bits(self, plaintext_bits, decoded_message, params):
        """Verify that the decoded message matches what the bits encode."""
        assert plaintext_bits is not None
        assert decoded_message is not None
        bits_per_char = int(params['bits_per_char'])

        # Reconstruct message from bits
        reconstructed = []
        for bits in plaintext_bits:
            for j in range(0, len(bits), bits_per_char):
                byte_bits = bits[j:j + bits_per_char]
                val = 0
                for b in byte_bits:
                    val = (val << 1) | b
                reconstructed.append(chr(val))
        reconstructed = ''.join(reconstructed)

        assert reconstructed == decoded_message, (
            f"decoded_message.txt content doesn't match "
            f"what plaintext_bits.txt encodes.\n"
            f"From bits: {reconstructed!r}\n"
            f"From file: {decoded_message!r}"
        )


# ============================================================
# Test 5: Solution implements LLL (not a trivial bypass)
# ============================================================
class TestSolutionQuality:
    def test_solution_contains_lll(self):
        """The solution must contain an LLL implementation, not use external libs."""
        import re
        with open('/app/solution.py') as f:
            code = f.read()

        # Must contain evidence of LLL implementation
        code_lower = code.lower()
        has_lll_keyword = ('lll' in code_lower or 'lovasz' in code_lower
                           or 'lovász' in code_lower
                           or 'gram_schmidt' in code_lower
                           or 'gram-schmidt' in code_lower
                           or 'lattice' in code_lower)
        assert has_lll_keyword, (
            "solution.py does not appear to contain an LLL implementation. "
            "Must implement lattice basis reduction from scratch."
        )

        # Must have meaningful algorithmic structure, not just a comment
        # with a brute-force approach. Check for function definitions and
        # operations typical of lattice reduction.
        func_defs = len(re.findall(r'^\s*def\s+\w+', code, re.MULTILINE))
        assert func_defs >= 3, (
            f"solution.py only has {func_defs} function definitions. "
            "An LLL implementation requires multiple functions."
        )

    def test_no_brute_force(self):
        """Check that the solution doesn't use exhaustive search."""
        with open('/app/solution.py') as f:
            code = f.read()

        code_lower = code.lower()
        # A brute force approach would iterate over 2^n combinations
        # Check for signs of brute force (not definitive, but a heuristic)
        brute_indicators = [
            'itertools.product',
            'range(2**',
            'range(1 <<',
            '16777216',  # 2^24
        ]
        for indicator in brute_indicators:
            assert indicator not in code_lower, (
                f"solution.py appears to use brute-force enumeration "
                f"(found '{indicator}'). Must use lattice reduction."
            )

    def test_no_banned_imports(self):
        """The solution must not import banned lattice/math libraries."""
        import re
        with open('/app/solution.py') as f:
            code = f.read()

        banned = ['fpylll', 'fplll', 'sage', 'sympy', 'scipy']
        for lib in banned:
            # Check for actual import statements, not just substring matches
            patterns = [
                rf'^\s*import\s+{re.escape(lib)}\b',
                rf'^\s*from\s+{re.escape(lib)}\b',
            ]
            for pat in patterns:
                match = re.search(pat, code, re.MULTILINE)
                assert match is None, \
                    f"solution.py imports banned library: {lib}"


# ============================================================
# Test 6: All 8 ciphertexts solved (no partial solutions)
# ============================================================
class TestCompleteness:
    def test_all_ciphertexts_decrypted(self, plaintext_bits, ciphertexts, public_key):
        """Every single ciphertext must be correctly decrypted."""
        assert plaintext_bits is not None
        assert len(plaintext_bits) == len(ciphertexts)

        successes = 0
        for bits, ct in zip(plaintext_bits, ciphertexts):
            computed = sum(b * pk for b, pk in zip(bits, public_key))
            if computed == ct:
                successes += 1

        assert successes == len(ciphertexts), \
            f"Only {successes}/{len(ciphertexts)} ciphertexts correctly decrypted"
