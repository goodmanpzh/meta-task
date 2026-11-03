# cryptanalysis challenge - break Merkle-Hellman knapsack

ok so I've been messing around with the Merkle-Hellman knapsack cryptosystem for a course project and I intercepted some encrypted messages... I know the public key and the ciphertexts but not the private key. Pretty sure this is breakable with lattice reduction (Shamir showed this in like 1984?) but I can't get it working.

## what's in the container

Check `/app/data/`:

- **`public_key.txt`** — one integer per line, the public knapsack sequence (24 elements)
- **`ciphertexts.txt`** — 8 encrypted integers, one per line
- **`params.txt`** — tells you the encoding params

## how the encryption works

The Merkle-Hellman system is a subset-sum based public key crypto. To encrypt a block of bits `x = (x_0, x_1, ..., x_{n-1})` where each `x_i ∈ {0,1}`, compute ciphertext = Σ x_i · pubkey_i. So each ciphertext is just a subset sum of the public key values.

The private key is a superincreasing sequence that gets scrambled via modular multiplication to produce the public key. But you don't know the private key, modulus, or multiplier.

## what you need to do

1. Implement the LLL (Lenstra-Lenstra-Lovász) lattice basis reduction algorithm from scratch. **No lattice libraries are installed** — just Python stdlib + numpy. You need to actually write LLL yourself.

2. Use LLL to break the knapsack: construct an appropriate lattice from the public key and each ciphertext, reduce it, and extract the plaintext bits from the short vectors in the reduced basis.

3. The plaintext bits encode ASCII text. Each 24-bit ciphertext block corresponds to 3 ASCII characters (8 bits per character, MSB first). Decode all 8 ciphertexts → 24 characters of plaintext.

4. Write your results to:
   - **`/app/plaintext_bits.txt`** — one line per ciphertext, each line is the 24 bits separated by spaces (e.g., `0 1 1 0 1 0 0 1 ...`)
   - **`/app/decoded_message.txt`** — the complete decoded ASCII string (single line, no trailing newline)
   - **`/app/solution.py`** — your Python implementation

## constraints

- You must implement LLL yourself (the environment only has Python 3.11 + numpy, no scipy/sympy/fpylll/sage)
- Your solution must correctly decrypt ALL 8 ciphertexts
- Total runtime must be under 120 seconds

## hints

The density of this knapsack (d = n / log2(max(pubkey))) is below the critical threshold, so LLL-based attacks should work. You'll need to think carefully about how to embed the subset-sum problem into a lattice — the naive approach might not work. Look into lattice constructions that center the search around the ±1 vector space rather than {0,1}.

good luck 💀 this one took me forever to figure out
