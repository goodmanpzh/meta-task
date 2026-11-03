"""
Test suite for RS(15,9) decoder over GF(2^4).
Verifies the Verilog implementation by checking properties of the output,
computing expected values from the test vectors using a Python RS codec.
"""
import os
import subprocess
import pytest

SIM_RESULTS = "/app/output/sim_results.txt"
SRC_FILE = "/app/src/rs_decoder.v"
TB_FILE = "/app/testbench/tb_rs_decoder.v"
TV_FILE = "/app/testbench/test_vectors.tv"

# ============================================================
# GF(2^4) reference implementation
# Primitive polynomial: x^4 + x + 1 (0x13), alpha = 2
# ============================================================
GF_EXP = [1, 2, 4, 8, 3, 6, 12, 11, 5, 10, 7, 14, 15, 13, 9]
GF_LOG = [0, 0, 1, 4, 2, 8, 5, 10, 3, 14, 9, 7, 6, 13, 11, 12]

def gf_mul(a, b):
    if a == 0 or b == 0: return 0
    return GF_EXP[(GF_LOG[a] + GF_LOG[b]) % 15]

def gf_div(a, b):
    if a == 0: return 0
    return GF_EXP[(GF_LOG[a] - GF_LOG[b]) % 15]

def gf_inv(a):
    return GF_EXP[15 - GF_LOG[a]]

def poly_eval(p, x):
    y = 0; xi = 1
    for c in p:
        y ^= gf_mul(c, xi); xi = gf_mul(xi, x)
    return y

def poly_mul(p, q):
    r = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            r[i+j] ^= gf_mul(a, b)
    return r

NSYM = 6; FCR = 0

def rs_generator():
    g = [1]
    for i in range(FCR, FCR + NSYM):
        g = poly_mul(g, [GF_EXP[i], 1])
    return g

def rs_encode(msg):
    gen = rs_generator()
    enc = [0]*NSYM + list(msg)
    for i in range(len(msg)-1, -1, -1):
        coef = enc[NSYM + i]
        if coef != 0:
            for j in range(NSYM + 1):
                enc[i+j] ^= gf_mul(gen[j], coef)
    return enc[:NSYM] + list(msg)

def rs_syndromes(cw):
    return [poly_eval(cw, GF_EXP[i]) for i in range(FCR, FCR + NSYM)]

def rs_berlekamp_massey(S):
    C = [1]+[0]*NSYM; B = [1]+[0]*NSYM
    L = 0; m = 1; b = 1
    for n in range(NSYM):
        d = S[n]
        for i in range(1, L+1):
            d ^= gf_mul(C[i], S[n-i])
        if d == 0:
            m += 1
        elif 2*L <= n:
            T = list(C); coef = gf_div(d, b)
            for i in range(m, NSYM+1):
                C[i] ^= gf_mul(coef, B[i-m])
            L = n+1-L; B = list(T); b = d; m = 1
        else:
            coef = gf_div(d, b)
            for i in range(m, NSYM+1):
                C[i] ^= gf_mul(coef, B[i-m])
            m += 1
    return C[:L+1], L

def rs_chien_search(Lambda, n=15):
    positions = []
    for j in range(n):
        xi = GF_EXP[(15-j)%15] if j > 0 else 1
        val = 0; xp = 1
        for c in Lambda:
            val ^= gf_mul(c, xp); xp = gf_mul(xp, xi)
        if val == 0:
            positions.append(j)
    return positions

def rs_forney(S, Lambda, positions):
    # Omega = S * Lambda mod x^6
    omega = [0]*NSYM
    for k in range(NSYM):
        for i in range(len(Lambda)):
            if k-i >= 0 and k-i < NSYM:
                omega[k] ^= gf_mul(Lambda[i], S[k-i])
    # Lambda' (formal derivative)
    lp = [Lambda[i] if i % 2 == 1 else 0 for i in range(1, len(Lambda))]
    if not lp: lp = [0]
    result = {}
    for pos in positions:
        xj = GF_EXP[pos] if pos > 0 else 1
        xji = GF_EXP[(15-pos)%15] if pos > 0 else 1
        ov = 0; xp = 1
        for c in omega:
            ov ^= gf_mul(c, xp); xp = gf_mul(xp, xji)
        lpv = 0; xp = 1
        for c in lp:
            lpv ^= gf_mul(c, xp); xp = gf_mul(xp, xji)
        if lpv != 0:
            result[pos] = gf_mul(xj, gf_div(ov, lpv))
        else:
            result[pos] = 0
    return result

def rs_decode(received):
    """Decode received 15-symbol word. Returns (corrected, success, num_errors)."""
    S = rs_syndromes(received)
    if all(s == 0 for s in S):
        return list(received), True, 0
    Lambda, L = rs_berlekamp_massey(S)
    positions = rs_chien_search(Lambda)
    if len(positions) != L:
        return list(received), False, 0
    magnitudes = rs_forney(S, Lambda, positions)
    corrected = list(received)
    for pos, mag in magnitudes.items():
        corrected[pos] ^= mag
    verify = rs_syndromes(corrected)
    return corrected, all(s == 0 for s in verify), len(positions)

def hex_to_symbols(h):
    val = int(h, 16)
    return [(val >> (i*4)) & 0xF for i in range(15)]

def symbols_to_hex(syms):
    val = 0
    for i in range(14, -1, -1):
        val = (val << 4) | (syms[i] & 0xF)
    return f"{val:015X}"


def _compute_expected():
    """Compute expected decode results from test vectors using Python RS codec."""
    results = []
    with open(TV_FILE) as f:
        tv_lines = [l.strip() for l in f if l.strip()]
    for idx, tv_hex in enumerate(tv_lines):
        rx_syms = hex_to_symbols(tv_hex)
        corrected, success, num_err = rs_decode(rx_syms)
        results.append({
            'idx': idx,
            'rx_hex': tv_hex.upper(),
            'cw_hex': symbols_to_hex(corrected),
            'num_errors': num_err,
            'should_fail': 0 if success else 1,
        })
    return results


def _load_sim_results():
    """Load simulation output, return dict keyed by test_id."""
    results = {}
    if not os.path.exists(SIM_RESULTS):
        return results
    with open(SIM_RESULTS) as f:
        for line in f:
            line = line.strip()
            if not line or 'TIMEOUT' in line:
                continue
            parts = line.split()
            if len(parts) >= 4:
                tid = int(parts[0])
                results[tid] = {
                    'out_hex': parts[1].upper(),
                    'error_count': int(parts[2]),
                    'fail': int(parts[3]),
                }
    return results


# ============================================================
# Tests
# ============================================================

class TestRSDecoderStructure:
    """Verify the Verilog source file exists and has correct structure."""

    def test_source_exists(self):
        assert os.path.exists(SRC_FILE), f"{SRC_FILE} not found"

    def test_module_declaration(self):
        with open(SRC_FILE) as f:
            src = f.read()
        assert "module rs_decoder" in src, "Module 'rs_decoder' not found"
        for port in ["clk", "rst_n", "start", "data_in", "done",
                      "decode_fail", "data_out", "error_count"]:
            assert port in src, f"Port '{port}' not found in module"

    def test_compiles(self):
        result = subprocess.run(
            ["iverilog", "-o", "/tmp/rs_test_compile", "-I", "/app/src",
             SRC_FILE, TB_FILE],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"Compilation failed:\n{result.stderr}"

    def test_gf_arithmetic_present(self):
        with open(SRC_FILE) as f:
            src = f.read().lower()
        has_gf = any(kw in src for kw in [
            "gf_mul", "gfm", "gf_exp", "gf_log", "galois",
            "multiply", "mul_table", "log_table", "exp_table",
            "alpha", "0xd1", "gf16"
        ])
        assert has_gf, "No GF(2^4) arithmetic implementation found"

    def test_fsm_present(self):
        with open(SRC_FILE) as f:
            src = f.read()
        has_states = ("case" in src and
                      ("state" in src.lower() or "S_" in src or "IDLE" in src))
        assert has_states, "No FSM/state machine found in decoder"


class TestSimulation:
    """Verify the simulation runs and produces output."""

    @pytest.fixture(autouse=True)
    def setup(self):
        if not os.path.exists(SIM_RESULTS):
            subprocess.run(
                ["iverilog", "-o", "/app/sim", "-I", "/app/src",
                 SRC_FILE, TB_FILE],
                capture_output=True, timeout=30
            )
            if os.path.exists("/app/sim"):
                subprocess.run(
                    ["vvp", "/app/sim"],
                    capture_output=True, timeout=120,
                    cwd="/app"
                )

    def test_sim_results_exist(self):
        assert os.path.exists(SIM_RESULTS), \
            "sim_results.txt not found - simulation may have failed"

    def test_sim_results_not_empty(self):
        assert os.path.getsize(SIM_RESULTS) > 0, \
            "sim_results.txt is empty"

    def test_all_tests_completed(self):
        sim = _load_sim_results()
        assert len(sim) >= 30, \
            f"Only {len(sim)}/30 test results found"

    def test_no_timeouts(self):
        with open(SIM_RESULTS) as f:
            content = f.read()
        assert "TIMEOUT" not in content, "One or more tests timed out"


class TestErrorFreeCodewords:
    """Verify decoder passes through error-free codewords unchanged."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.expected = _compute_expected()
        self.sim = _load_sim_results()

    def test_errorfree_correct(self):
        errorfree_ids = [i for i, e in enumerate(self.expected)
                         if e['num_errors'] == 0 and e['should_fail'] == 0]
        assert len(errorfree_ids) >= 3, "Need at least 3 error-free test cases"
        for tid in errorfree_ids:
            if tid not in self.sim:
                pytest.fail(f"Test {tid} missing from results")
            exp = self.expected[tid]
            sim = self.sim[tid]
            # Error-free: output should equal input
            assert sim['out_hex'] == exp['rx_hex'], \
                f"Test {tid}: error-free codeword should pass through unchanged"
            assert sim['fail'] == 0


class TestSingleErrors:
    """Verify decoder corrects single-symbol errors."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.expected = _compute_expected()
        self.sim = _load_sim_results()

    def test_single_error_correction(self):
        """Output for single-error cases must be a valid codeword."""
        # Identify single-error cases: received has non-zero syndromes,
        # but Python decode finds exactly 1 error
        single_ids = [i for i, e in enumerate(self.expected)
                      if e['num_errors'] == 1 and e['should_fail'] == 0]
        assert len(single_ids) >= 5
        for tid in single_ids:
            if tid not in self.sim:
                pytest.fail(f"Test {tid} missing")
            sim = self.sim[tid]
            assert sim['fail'] == 0, \
                f"Test {tid}: single error should be correctable"
            # Output must be a valid codeword
            out_syms = hex_to_symbols(sim['out_hex'])
            synd = rs_syndromes(out_syms)
            assert all(s == 0 for s in synd), \
                f"Test {tid}: corrected output is not a valid codeword"

    def test_single_error_count(self):
        single_ids = [i for i, e in enumerate(self.expected)
                      if e['num_errors'] == 1 and e['should_fail'] == 0]
        for tid in single_ids:
            if tid in self.sim:
                assert self.sim[tid]['error_count'] == 1, \
                    f"Test {tid}: error_count should be 1"


class TestDoubleErrors:
    """Verify decoder corrects double-symbol errors."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.expected = _compute_expected()
        self.sim = _load_sim_results()

    def test_double_error_correction(self):
        double_ids = [i for i, e in enumerate(self.expected)
                      if e['num_errors'] == 2 and e['should_fail'] == 0]
        assert len(double_ids) >= 5
        for tid in double_ids:
            if tid not in self.sim:
                pytest.fail(f"Test {tid} missing")
            sim = self.sim[tid]
            assert sim['fail'] == 0
            out_syms = hex_to_symbols(sim['out_hex'])
            synd = rs_syndromes(out_syms)
            assert all(s == 0 for s in synd), \
                f"Test {tid}: corrected output is not a valid codeword"

    def test_double_error_message_matches(self):
        """Corrected message portion must match the Python decoder's result."""
        double_ids = [i for i, e in enumerate(self.expected)
                      if e['num_errors'] == 2 and e['should_fail'] == 0]
        for tid in double_ids:
            if tid not in self.sim:
                continue
            sim = self.sim[tid]
            if sim['fail'] == 1:
                continue
            exp = self.expected[tid]
            sim_msg = hex_to_symbols(sim['out_hex'])[6:]  # message symbols
            exp_msg = hex_to_symbols(exp['cw_hex'])[6:]
            assert sim_msg == exp_msg, \
                f"Test {tid}: message mismatch after correction"


class TestTripleErrors:
    """Verify decoder corrects triple-symbol errors (at correction limit)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.expected = _compute_expected()
        self.sim = _load_sim_results()

    def test_triple_error_correction(self):
        triple_ids = [i for i, e in enumerate(self.expected)
                      if e['num_errors'] == 3 and e['should_fail'] == 0]
        assert len(triple_ids) >= 5
        for tid in triple_ids:
            if tid not in self.sim:
                pytest.fail(f"Test {tid} missing")
            sim = self.sim[tid]
            assert sim['fail'] == 0
            out_syms = hex_to_symbols(sim['out_hex'])
            synd = rs_syndromes(out_syms)
            assert all(s == 0 for s in synd), \
                f"Test {tid}: corrected output is not a valid codeword"

    def test_triple_error_message_matches(self):
        """Corrected message must match Python decoder for triple-error cases."""
        triple_ids = [i for i, e in enumerate(self.expected)
                      if e['num_errors'] == 3 and e['should_fail'] == 0]
        for tid in triple_ids:
            if tid not in self.sim:
                continue
            sim = self.sim[tid]
            if sim['fail'] == 1:
                continue
            exp = self.expected[tid]
            sim_msg = hex_to_symbols(sim['out_hex'])[6:]
            exp_msg = hex_to_symbols(exp['cw_hex'])[6:]
            assert sim_msg == exp_msg, \
                f"Test {tid}: triple error message mismatch"


class TestDecodeFailure:
    """Verify decoder detects uncorrectable errors (4+ symbols)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.expected = _compute_expected()
        self.sim = _load_sim_results()

    def test_four_error_failure_detection(self):
        fail_ids = [i for i, e in enumerate(self.expected)
                    if e['should_fail'] == 1]
        assert len(fail_ids) >= 5, "Need at least 5 failure test cases"
        for tid in fail_ids:
            if tid not in self.sim:
                pytest.fail(f"Test {tid} missing")
            sim = self.sim[tid]
            assert sim['fail'] == 1, \
                f"Test {tid}: 4-error case should set decode_fail=1"


class TestCodewordValidity:
    """Cross-check all correctable outputs are valid RS codewords."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.expected = _compute_expected()
        self.sim = _load_sim_results()

    def test_all_corrected_outputs_are_valid_codewords(self):
        correctable_ids = [i for i, e in enumerate(self.expected)
                           if e['should_fail'] == 0]
        for tid in correctable_ids:
            if tid not in self.sim:
                continue
            sim = self.sim[tid]
            if sim['fail'] == 1:
                continue
            syms = hex_to_symbols(sim['out_hex'])
            syndromes = rs_syndromes(syms)
            assert all(s == 0 for s in syndromes), \
                f"Test {tid}: output {sim['out_hex']} is not a valid codeword"

    def test_message_portions_match_expected(self):
        correctable_ids = [i for i, e in enumerate(self.expected)
                           if e['should_fail'] == 0]
        for tid in correctable_ids:
            if tid not in self.sim:
                continue
            sim = self.sim[tid]
            if sim['fail'] == 1:
                continue
            exp = self.expected[tid]
            sim_msg = hex_to_symbols(sim['out_hex'])[6:]
            exp_msg = hex_to_symbols(exp['cw_hex'])[6:]
            assert sim_msg == exp_msg, \
                f"Test {tid}: message mismatch"
