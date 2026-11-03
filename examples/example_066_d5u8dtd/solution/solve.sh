#!/bin/bash
set -e

cat > /app/solution.py << 'PYEOF'
import math

def read_integers(filepath):
    with open(filepath) as f:
        return [int(line.strip()) for line in f if line.strip()]

def read_params(filepath):
    params = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                k, v = line.split('=', 1)
                params[k.strip()] = v.strip()
    return params

def lll_reduce(basis, delta=0.99):
    """
    LLL lattice basis reduction using floating-point Gram-Schmidt.
    Input: list of integer vectors (list of lists).
    Output: LLL-reduced basis (list of integer lists).
    """
    n = len(basis)
    m = len(basis[0])
    B = [list(map(float, row)) for row in basis]

    def dot(u, v):
        s = 0.0
        for a, b in zip(u, v):
            s += a * b
        return s

    # Gram-Schmidt orthogonalization
    def compute_gs():
        Bs = [[0.0] * m for _ in range(n)]
        mu = [[0.0] * n for _ in range(n)]
        Bn = [0.0] * n
        for i in range(n):
            for k in range(m):
                Bs[i][k] = B[i][k]
            for j in range(i):
                if Bn[j] < 1e-30:
                    mu[i][j] = 0.0
                else:
                    mu[i][j] = dot(B[i], Bs[j]) / Bn[j]
                for k in range(m):
                    Bs[i][k] -= mu[i][j] * Bs[j][k]
            Bn[i] = dot(Bs[i], Bs[i])
        return mu, Bn

    mu, Bn = compute_gs()

    k = 1
    while k < n:
        # Size reduce B[k] with respect to B[k-1], ..., B[0]
        for j in range(k - 1, -1, -1):
            if abs(mu[k][j]) > 0.5:
                r = round(mu[k][j])
                for i in range(m):
                    B[k][i] -= r * B[j][i]
                mu, Bn = compute_gs()

        # Check Lovász condition
        if Bn[k] >= (delta - mu[k][k - 1] ** 2) * Bn[k - 1]:
            k += 1
        else:
            # Swap B[k] and B[k-1]
            B[k], B[k - 1] = B[k - 1], B[k]
            mu, Bn = compute_gs()
            k = max(k - 1, 1)

    return [[int(round(x)) for x in row] for row in B]


def solve_knapsack(public_key, ciphertext):
    """
    Solve the subset-sum problem: find x in {0,1}^n such that
    sum(x_i * pubkey_i) = ciphertext.

    Uses the CJLOSS lattice construction:
    - Build an (n+1) x (n+1) matrix where the first n rows have
      2*I_n in the left block and 2*N*pubkey_i in the last column.
    - The last row has all 1s in the left block and 2*N*ciphertext
      in the last column.
    - A solution vector will have entries +/-1 in the first n positions
      and 0 in the last position.
    """
    n = len(public_key)
    N_scale = int(math.ceil(math.sqrt(n / 2)))

    # Build lattice basis
    matrix = []
    for i in range(n):
        row = [0] * (n + 1)
        row[i] = 2
        row[n] = 2 * N_scale * public_key[i]
        matrix.append(row)

    last_row = [1] * n + [2 * N_scale * ciphertext]
    matrix.append(last_row)

    # LLL reduce
    reduced = lll_reduce(matrix)

    # Search reduced basis for solution vector
    for row in reduced:
        if row[n] != 0:
            continue
        if all(abs(row[i]) == 1 for i in range(n)):
            # Two possible sign conventions
            bits = [(1 + row[i]) // 2 for i in range(n)]
            if sum(b * pk for b, pk in zip(bits, public_key)) == ciphertext:
                return bits
            bits = [(1 - row[i]) // 2 for i in range(n)]
            if sum(b * pk for b, pk in zip(bits, public_key)) == ciphertext:
                return bits
    return None


def bits_to_text(bits, bits_per_char=8):
    """Convert a bit vector to ASCII text (MSB first)."""
    chars = []
    for i in range(0, len(bits), bits_per_char):
        byte_bits = bits[i:i + bits_per_char]
        val = 0
        for b in byte_bits:
            val = (val << 1) | b
        chars.append(chr(val))
    return ''.join(chars)


def main():
    # Read input data
    public_key = read_integers('/app/data/public_key.txt')
    ciphertexts = read_integers('/app/data/ciphertexts.txt')
    params = read_params('/app/data/params.txt')

    n = int(params['dimension'])
    num_ct = int(params['num_ciphertexts'])
    bits_per_char = int(params['bits_per_char'])
    chars_per_block = int(params['chars_per_block'])

    assert len(public_key) == n
    assert len(ciphertexts) == num_ct

    print(f"Public key dimension: {n}")
    print(f"Number of ciphertexts: {num_ct}")
    print(f"Density: {n / math.log2(max(public_key)):.4f}")

    # Solve each ciphertext
    all_bits = []
    message_chars = []

    for idx, ct in enumerate(ciphertexts):
        print(f"\nSolving ciphertext {idx}: {ct}")
        bits = solve_knapsack(public_key, ct)
        if bits is None:
            raise RuntimeError(f"Failed to solve ciphertext {idx}")

        # Verify
        check = sum(b * pk for b, pk in zip(bits, public_key))
        assert check == ct, f"Verification failed for ciphertext {idx}: {check} != {ct}"

        text = bits_to_text(bits, bits_per_char)
        print(f"  Bits: {' '.join(map(str, bits))}")
        print(f"  Text: {text}")

        all_bits.append(bits)
        message_chars.append(text)

    # Write outputs
    with open('/app/plaintext_bits.txt', 'w') as f:
        for bits in all_bits:
            f.write(' '.join(map(str, bits)) + '\n')

    decoded = ''.join(message_chars)
    print(f"\nDecoded message: {decoded}")

    with open('/app/decoded_message.txt', 'w') as f:
        f.write(decoded)

    print("\nDone!")


if __name__ == '__main__':
    main()
PYEOF

python3 /app/solution.py
