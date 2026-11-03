#!/usr/bin/env python3
"""
Generate a Merkle-Hellman knapsack cryptosystem instance.
Produces public_key.txt and ciphertexts.txt for the lattice reduction challenge.
This script is deleted after running during Docker build.
"""
import random
import math
import os
import sys

SEED = 83714209
random.seed(SEED)

N = 24  # dimension (bits per block)
NUM_MESSAGES = 8

SECRET_MESSAGE = "LLL_Breaks_MH_Knapsack!!"
assert len(SECRET_MESSAGE) == N, f"Message must be {N} chars, got {len(SECRET_MESSAGE)}"


def generate_superincreasing_sequence(n):
    seq = []
    total = 0
    for i in range(n):
        val = total + random.randint(1, max(1, total // 4 + 5))
        seq.append(val)
        total += val
    return seq


def find_coprime(q):
    while True:
        r = random.randint(2, q - 1)
        if math.gcd(r, q) == 1:
            return r


def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    g, x, y = extended_gcd(b % a, a)
    return g, y - (b // a) * x, x


def mod_inverse(r, q):
    g, x, _ = extended_gcd(r, q)
    assert g == 1
    return x % q


def message_to_bit_blocks(message, block_size):
    chars_per_block = block_size // 8
    blocks = []
    for i in range(0, len(message), chars_per_block):
        chunk = message[i:i + chars_per_block]
        bits = []
        for ch in chunk:
            byte_val = ord(ch)
            for bit_pos in range(7, -1, -1):
                bits.append((byte_val >> bit_pos) & 1)
        assert len(bits) == block_size
        blocks.append(bits)
    return blocks


def encrypt(bits, public_key):
    return sum(b * pk for b, pk in zip(bits, public_key))


def lll_reduce(basis, delta=0.99):
    """LLL lattice basis reduction with floating-point Gram-Schmidt.
    Works well for small dimensions (n <= 30) and moderate entry sizes.
    """
    n = len(basis)
    m = len(basis[0])
    B = [list(map(float, row)) for row in basis]

    def dot(u, v):
        return sum(a * b for a, b in zip(u, v))

    def gram_schmidt():
        Bs = [[0.0] * m for _ in range(n)]
        mu = [[0.0] * n for _ in range(n)]
        Bn = [0.0] * n
        for i in range(n):
            Bs[i] = list(B[i])
            for j in range(i):
                if Bn[j] < 1e-30:
                    mu[i][j] = 0.0
                else:
                    mu[i][j] = dot(B[i], Bs[j]) / Bn[j]
                Bs[i] = [Bs[i][k] - mu[i][j] * Bs[j][k] for k in range(m)]
            Bn[i] = dot(Bs[i], Bs[i])
        return mu, Bn

    mu, Bn = gram_schmidt()

    k = 1
    while k < n:
        # Size reduction
        for j in range(k - 1, -1, -1):
            if abs(mu[k][j]) > 0.5:
                r = round(mu[k][j])
                B[k] = [B[k][i] - r * B[j][i] for i in range(m)]
                mu, Bn = gram_schmidt()

        # Lovász condition
        if Bn[k] >= (delta - mu[k][k - 1] ** 2) * Bn[k - 1]:
            k += 1
        else:
            B[k], B[k - 1] = B[k - 1], B[k]
            mu, Bn = gram_schmidt()
            k = max(k - 1, 1)

    return [[round(x) for x in row] for row in B]


def solve_knapsack_lll(public_key, target):
    """
    Use LLL to solve subset-sum / low-density knapsack.
    Uses the CJLOSS lattice embedding.
    """
    n = len(public_key)
    # Scale factor
    N_scale = int(math.ceil(math.sqrt(n / 2)))

    # Build (n+1) x (n+1) lattice basis
    matrix = []
    for i in range(n):
        row = [0] * (n + 1)
        row[i] = 2
        row[n] = 2 * N_scale * public_key[i]
        matrix.append(row)

    last_row = [1] * n + [2 * N_scale * target]
    matrix.append(last_row)

    reduced = lll_reduce(matrix)

    # Search for solution vector
    for row in reduced:
        if row[n] != 0:
            continue
        if all(abs(row[i]) == 1 for i in range(n)):
            # Try both sign conventions
            bits = [(1 + row[i]) // 2 for i in range(n)]
            if sum(b * pk for b, pk in zip(bits, public_key)) == target:
                return bits
            bits = [(1 - row[i]) // 2 for i in range(n)]
            if sum(b * pk for b, pk in zip(bits, public_key)) == target:
                return bits
    return None


def try_generate():
    """Attempt to generate a valid instance. Returns True on success."""
    random.seed(SEED)

    private_key = generate_superincreasing_sequence(N)
    total_private = sum(private_key)
    q = total_private + random.randint(total_private // 4, total_private // 2)
    r = find_coprime(q)
    r_inv = mod_inverse(r, q)

    public_key = [(r * a) % q for a in private_key]
    density = N / math.log2(max(public_key))
    print(f"Density: {density:.4f}")
    print(f"Max public key value: {max(public_key)}")

    bit_blocks = message_to_bit_blocks(SECRET_MESSAGE, N)
    ciphertexts = [encrypt(bits, public_key) for bits in bit_blocks]

    # Verify private key decryption works
    for idx, (ct, expected_bits) in enumerate(zip(ciphertexts, bit_blocks)):
        s = (r_inv * ct) % q
        recovered = [0] * N
        for i in range(N - 1, -1, -1):
            if private_key[i] <= s:
                recovered[i] = 1
                s -= private_key[i]
        if s != 0 or recovered != expected_bits:
            print(f"Private key decryption failed for block {idx}")
            return False

    # Verify LLL attack works
    print("Verifying LLL attack works...")
    for idx, (ct, expected_bits) in enumerate(zip(ciphertexts, bit_blocks)):
        result = solve_knapsack_lll(public_key, ct)
        if result is None:
            print(f"LLL attack failed for ciphertext {idx}")
            return False
        if result != expected_bits:
            print(f"LLL got wrong bits for ciphertext {idx}")
            return False
        print(f"  Ciphertext {idx}: OK")

    # All passed, write files
    os.makedirs("/app/data", exist_ok=True)

    with open("/app/data/public_key.txt", "w") as f:
        for val in public_key:
            f.write(f"{val}\n")

    with open("/app/data/ciphertexts.txt", "w") as f:
        for ct in ciphertexts:
            f.write(f"{ct}\n")

    with open("/app/data/params.txt", "w") as f:
        f.write(f"dimension={N}\n")
        f.write(f"num_ciphertexts={NUM_MESSAGES}\n")
        f.write(f"bits_per_char=8\n")
        f.write(f"bit_order=MSB_first\n")
        f.write(f"chars_per_block={N // 8}\n")
        f.write(f"encoding=ASCII\n")

    print(f"Generated {NUM_MESSAGES} ciphertexts with {N}-bit public key")
    return True


if not try_generate():
    # Try multiple seeds until we find one that works
    for seed_offset in range(1, 100):
        SEED = 83714209 + seed_offset
        print(f"\nRetrying with seed {SEED}...")
        if try_generate():
            break
    else:
        print("FATAL: Could not find a working seed")
        sys.exit(1)

print("\nAll verifications passed! Files written to /app/data/")
