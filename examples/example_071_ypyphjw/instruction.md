# Reed-Solomon RS(15,9) Decoder over GF(2^4)

Implement a complete Reed-Solomon RS(15,9) decoder in Verilog that corrects up to 3 symbol errors per codeword. The decoder operates over GF(2^4) with primitive polynomial p(x) = x^4 + x + 1 (binary: 10011). The primitive element is alpha = 2 (i.e., the polynomial x). The generator polynomial has roots at alpha^0, alpha^1, ..., alpha^5 (FCR = 0, meaning the first consecutive root is alpha^0). Codewords are 15 symbols of 4 bits each, with 6 parity symbols (positions 0-5) followed by 9 message symbols (positions 6-14).

Your decoder must implement the following pipeline stages as a synchronous FSM:

1. **Syndrome Computation**: Evaluate the received polynomial R(x) at alpha^0 through alpha^5 to produce 6 syndromes S_0..S_5. Use Horner's method or direct substitution over GF(2^4).

2. **Berlekamp-Massey Algorithm**: From the 6 syndromes, iteratively compute the error locator polynomial Lambda(x) of degree at most 3. The BM algorithm must track the connection polynomial, discrepancy, and shift register length across 6 iterations.

3. **Chien Search**: Evaluate Lambda(x) at alpha^{-j} for j = 0..14 to find error positions. A zero evaluation indicates an error at position j. The number of roots found must equal the degree of Lambda; otherwise signal a decode failure.

4. **Forney Algorithm**: Compute error magnitudes using the error evaluator polynomial Omega(x) = S(x) * Lambda(x) mod x^6 and the formal derivative Lambda'(x). For each error position j with locator X_j = alpha^j:
   e_j = X_j * Omega(X_j^{-1}) / Lambda'(X_j^{-1})

All arithmetic is over GF(2^4). You may implement GF multiplication using lookup tables (recommended for 4-bit symbols), direct logic, or the log/exp table approach.

## Module Interface

Implement the file `/app/src/rs_decoder.v` with the following port specification. The module receives one 60-bit word (15 symbols x 4 bits, symbol 0 in bits [3:0], symbol 14 in bits [59:56]) on `data_in` when `start` is asserted. After processing, it asserts `done` for one cycle and presents the corrected 60-bit codeword on `data_out`. If the received word has more than 3 errors, assert `decode_fail` alongside `done`. The `error_count` output gives the number of errors found (0-3, or 0 on failure).

```verilog
module rs_decoder(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [59:0] data_in,   // received codeword, 15 x 4-bit symbols
    output reg         done,
    output reg         decode_fail,
    output reg  [59:0] data_out,  // corrected codeword
    output reg  [2:0]  error_count
);
```

A testbench is provided at `/app/testbench/tb_rs_decoder.v`. It reads test vectors from `/app/testbench/test_vectors.tv`, feeds each received word into your decoder, and writes the simulation results to `/app/output/sim_results.txt`. Each line of the output file has the format: `<test_id> <corrected_hex> <error_count> <fail_flag>`.

Compile and simulate with:
```
cd /app && iverilog -o sim -I src src/rs_decoder.v testbench/tb_rs_decoder.v && vvp sim
```

A Python reference for GF(2^4) arithmetic is provided at `/app/reference/gf16_tables.py` — it contains the exp/log tables and basic operations. You may use it to verify intermediate values but the final deliverable must be the Verilog module.

The test vectors include: error-free codewords, single errors, double errors, triple errors (the correction limit), and cases with 4+ errors (which must be flagged as decode failures). Your implementation must handle all cases correctly.
