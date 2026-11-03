#!/usr/bin/env python3
"""Generate test vectors for RS(15,9) decoder verification.
Only writes the received (possibly corrupted) codewords.
Expected results are computed at test time by the verifier.
"""
import random, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'reference'))
from gf16_tables import gf_exp, gf_log, gf_mul, gf_div, gf_inv, gf_pow

def poly_eval(p, x):
    y = 0; xi = 1
    for c in p:
        y ^= gf_mul(c, xi); xi = gf_mul(xi, x)
    return y

def poly_mul(p, q):
    r = [0]*(len(p)+len(q)-1)
    for i,a in enumerate(p):
        for j,b in enumerate(q):
            r[i+j] ^= gf_mul(a,b)
    return r

NSYM = 6; FCR = 0

def rs_generator():
    g = [1]
    for i in range(FCR, FCR+NSYM):
        g = poly_mul(g, [gf_exp[i], 1])
    return g

def rs_encode(msg):
    gen = rs_generator()
    enc = [0]*NSYM + list(msg)
    for i in range(len(msg)-1,-1,-1):
        coef = enc[NSYM+i]
        if coef != 0:
            for j in range(NSYM+1):
                enc[i+j] ^= gf_mul(gen[j], coef)
    return enc[:NSYM] + list(msg)

def rs_syndromes(cw):
    return [poly_eval(cw, gf_exp[i]) for i in range(FCR, FCR+NSYM)]

def rs_bm(S):
    C = [1]+[0]*NSYM; B = [1]+[0]*NSYM
    L=0; m=1; b=1
    for n in range(NSYM):
        d = S[n]
        for i in range(1,L+1): d ^= gf_mul(C[i], S[n-i])
        if d==0: m+=1
        elif 2*L<=n:
            T_=list(C); coef=gf_div(d,b)
            for i in range(m,NSYM+1): C[i]^=gf_mul(coef,B[i-m])
            L=n+1-L; B=list(T_); b=d; m=1
        else:
            coef=gf_div(d,b)
            for i in range(m,NSYM+1): C[i]^=gf_mul(coef,B[i-m])
            m+=1
    return C[:L+1], L

def rs_chien(Lambda, n=15):
    errs = len(Lambda)-1; positions = []
    for j in range(n):
        xi = gf_exp[(15-j)%15] if j>0 else 1
        val = 0; xp=1
        for c in Lambda:
            val ^= gf_mul(c, xp); xp=gf_mul(xp,xi)
        if val==0: positions.append(j)
    return positions

def is_reliable_fail(rx):
    """Check if error pattern reliably triggers decode failure."""
    S = rs_syndromes(rx)
    Lambda, L = rs_bm(S)
    roots = rs_chien(Lambda)
    return len(roots) != L

def symbols_to_hex(symbols):
    val = 0
    for i in range(14,-1,-1): val = (val<<4)|(symbols[i]&0xF)
    return f"{val:015X}"

def main():
    random.seed(12345)
    vectors = []

    # Error-free (3)
    for _ in range(3):
        msg = [random.randint(0,15) for _ in range(9)]
        cw = rs_encode(msg)
        vectors.append(list(cw))

    # Single errors (5)
    for _ in range(5):
        msg = [random.randint(0,15) for _ in range(9)]
        cw = rs_encode(msg)
        rx = list(cw)
        pos = random.randint(0,14)
        rx[pos] ^= random.randint(1,15)
        vectors.append(rx)

    # Double errors (7)
    for _ in range(7):
        msg = [random.randint(0,15) for _ in range(9)]
        cw = rs_encode(msg)
        rx = list(cw)
        for p in sorted(random.sample(range(15), 2)):
            rx[p] ^= random.randint(1,15)
        vectors.append(rx)

    # Triple errors (8)
    for _ in range(8):
        msg = [random.randint(0,15) for _ in range(9)]
        cw = rs_encode(msg)
        rx = list(cw)
        for p in sorted(random.sample(range(15), 3)):
            rx[p] ^= random.randint(1,15)
        vectors.append(rx)

    # Four errors - reliable failures (5)
    fail_seed = 1000
    fail_count = 0
    while fail_count < 5:
        random.seed(fail_seed)
        msg = [random.randint(0,15) for _ in range(9)]
        cw = rs_encode(msg)
        rx = list(cw)
        for p in sorted(random.sample(range(15), 4)):
            rx[p] ^= random.randint(1,15)
        if is_reliable_fail(rx):
            vectors.append(rx)
            fail_count += 1
        fail_seed += 1

    # Edge: all-zero
    cw = rs_encode([0]*9)
    vectors.append(list(cw))

    # Edge: all-0xF with single error
    cw = rs_encode([15]*9)
    rx = list(cw)
    rx[7] ^= 5
    vectors.append(rx)

    with open('/app/testbench/test_vectors.tv', 'w') as f:
        for rx in vectors:
            f.write(symbols_to_hex(rx) + '\n')

    print(f"Generated {len(vectors)} test vectors")

if __name__ == "__main__":
    main()
