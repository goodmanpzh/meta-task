#!/usr/bin/env python3
"""
GF(2^4) arithmetic reference implementation.
Primitive polynomial: p(x) = x^4 + x + 1 (0x13)
Primitive element: alpha = 2

This file provides lookup tables and basic operations for GF(2^4).
Use it to verify intermediate values during your Verilog development.
"""

PRIM_POLY = 0x13  # x^4 + x + 1

# Exponential table: gf_exp[i] = alpha^i
# Log table: gf_log[a] = i such that alpha^i = a (for a != 0)
gf_exp = [0] * 30
gf_log = [0] * 16

x = 1
for i in range(15):
    gf_exp[i] = x
    gf_log[x] = i
    x <<= 1
    if x >= 16:
        x ^= PRIM_POLY

# Extend for wraparound convenience
for i in range(15, 30):
    gf_exp[i] = gf_exp[i - 15]

def gf_mul(a, b):
    """Multiply two GF(2^4) elements."""
    if a == 0 or b == 0:
        return 0
    return gf_exp[(gf_log[a] + gf_log[b]) % 15]

def gf_div(a, b):
    """Divide a by b in GF(2^4)."""
    if b == 0:
        raise ZeroDivisionError("Division by zero in GF(2^4)")
    if a == 0:
        return 0
    return gf_exp[(gf_log[a] - gf_log[b]) % 15]

def gf_inv(a):
    """Multiplicative inverse in GF(2^4)."""
    if a == 0:
        raise ZeroDivisionError("Zero has no inverse")
    return gf_exp[15 - gf_log[a]]

def gf_pow(a, n):
    """Raise a to power n in GF(2^4)."""
    if a == 0:
        return 0
    return gf_exp[(gf_log[a] * n) % 15]

if __name__ == "__main__":
    print("=== GF(2^4) Exponential Table ===")
    print(f"alpha = {gf_exp[1]}")
    for i in range(15):
        print(f"  alpha^{i:2d} = {gf_exp[i]:2d} (0x{gf_exp[i]:X})")

    print("\n=== GF(2^4) Log Table ===")
    for a in range(1, 16):
        print(f"  log({a:2d}) = {gf_log[a]:2d}")

    print("\n=== GF(2^4) Inverse Table ===")
    for a in range(1, 16):
        print(f"  inv({a:2d}) = {gf_inv(a):2d}")

    print("\n=== GF(2^4) Multiplication Table ===")
    print("     ", end="")
    for b in range(16):
        print(f"{b:3d}", end="")
    print()
    for a in range(16):
        print(f"  {a:2d}:", end="")
        for b in range(16):
            print(f"{gf_mul(a,b):3d}", end="")
        print()
