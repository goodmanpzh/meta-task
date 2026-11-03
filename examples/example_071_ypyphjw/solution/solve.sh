#!/bin/bash
set -e

cat > /app/src/rs_decoder.v << 'VEOF'
// RS(15,9) decoder over GF(2^4), primitive poly x^4+x+1, FCR=0, t=3
module rs_decoder(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [59:0] data_in,
    output reg         done,
    output reg         decode_fail,
    output reg  [59:0] data_out,
    output reg  [2:0]  error_count
);

    // GF(2^4) exp table: alpha^i for i=0..14
    function [3:0] gf_exp;
    input [3:0] i;
    begin
        case(i)
        0: gf_exp=1;  1: gf_exp=2;  2: gf_exp=4;  3: gf_exp=8;
        4: gf_exp=3;  5: gf_exp=6;  6: gf_exp=12; 7: gf_exp=11;
        8: gf_exp=5;  9: gf_exp=10; 10:gf_exp=7;  11:gf_exp=14;
        12:gf_exp=15; 13:gf_exp=13; 14:gf_exp=9;
        default: gf_exp=0;
        endcase
    end
    endfunction

    // GF(2^4) log table: log_alpha(x) for x=1..15
    function [3:0] gf_log;
    input [3:0] x;
    begin
        case(x)
        1: gf_log=0;  2: gf_log=1;  3: gf_log=4;  4: gf_log=2;
        5: gf_log=8;  6: gf_log=5;  7: gf_log=10; 8: gf_log=3;
        9: gf_log=14; 10:gf_log=9;  11:gf_log=7;  12:gf_log=6;
        13:gf_log=13; 14:gf_log=11; 15:gf_log=12;
        default: gf_log=0;
        endcase
    end
    endfunction

    // GF multiply
    function [3:0] gfm;
    input [3:0] a, b;
    reg [4:0] s;
    begin
        if (a==0 || b==0) gfm = 0;
        else begin
            s = gf_log(a) + gf_log(b);
            if (s >= 15) s = s - 15;
            gfm = gf_exp(s[3:0]);
        end
    end
    endfunction

    // GF divide
    function [3:0] gfd;
    input [3:0] a, b;
    reg signed [5:0] d;
    begin
        if (a==0) gfd = 0;
        else begin
            d = $signed({1'b0,gf_log(a)}) - $signed({1'b0,gf_log(b)});
            if (d < 0) d = d + 15;
            gfd = gf_exp(d[3:0]);
        end
    end
    endfunction

    // States
    localparam IDLE=0, LOAD=1, SYN=2, SYN_STORE=3, SYN_CHECK=4,
               BM_INIT=5, BM_DISC=6, BM_APPLY=7, BM_ADV=8,
               CH_INIT=9, CH_EVAL=10, CH_CHECK=11, CH_VERIFY=12,
               FN_OMEGA=13, FN_EVAL=14, FN_NEXT=15,
               CORRECT=16, OUTPUT=17, FAIL=18;

    reg [4:0] state;
    reg [3:0] rx [0:14];
    reg [3:0] syn [0:5];

    // Syndrome
    reg [3:0] si, sj, sacc;

    // BM
    reg [3:0] C0, C1, C2, C3;
    reg [3:0] B0, B1, B2, B3;
    reg [3:0] T0, T1, T2, T3;
    reg [3:0] bL, bm, bb;
    reg [3:0] bstep, bdelta, bj, bcoef;

    // Chien
    reg [3:0] cpos, cacc, cj, calpha;
    reg [3:0] epos0, epos1, epos2;
    reg [2:0] nerr;
    reg [3:0] ldeg;

    // Forney
    reg [3:0] om0, om1, om2, om3, om4, om5;
    reg [3:0] fni, fnj;
    reg [3:0] fnxj, fnxji, fnxp;
    reg [3:0] fnov, fnlpv;
    reg [3:0] emag0, emag1, emag2;
    reg [2:0] fnph;
    reg [3:0] fnacc;

    integer k;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; done <= 0; decode_fail <= 0;
            data_out <= 0; error_count <= 0;
            si<=0; sj<=0; sacc<=0;
            C0<=1; C1<=0; C2<=0; C3<=0;
            B0<=1; B1<=0; B2<=0; B3<=0;
            T0<=0; T1<=0; T2<=0; T3<=0;
            bL<=0; bm<=1; bb<=1; bstep<=0; bdelta<=0; bj<=0; bcoef<=0;
            cpos<=0; cacc<=0; cj<=0; calpha<=0;
            epos0<=0; epos1<=0; epos2<=0; nerr<=0; ldeg<=0;
            om0<=0; om1<=0; om2<=0; om3<=0; om4<=0; om5<=0;
            fni<=0; fnj<=0; fnxj<=0; fnxji<=0; fnxp<=0;
            fnov<=0; fnlpv<=0; fnph<=0; fnacc<=0;
            emag0<=0; emag1<=0; emag2<=0;
            for(k=0;k<15;k=k+1) rx[k]<=0;
            for(k=0;k<6;k=k+1) syn[k]<=0;
        end else begin
            done <= 0;
            case(state)

            IDLE: if (start) begin
                for(k=0;k<15;k=k+1) rx[k] <= data_in[k*4 +: 4];
                decode_fail <= 0; error_count <= 0; nerr <= 0;
                si <= 0; sj <= 4'd14; sacc <= 4'd0;
                state <= SYN;
            end

            // ---- Syndrome computation ----
            // Horner: S_i = R(alpha^i)
            // acc starts at 0, process from symbol 14 down to 0:
            //   acc = acc * alpha^i ^ rx[sj]
            // After sj=0, acc = S_i
            SYN: begin
                sacc <= gfm(sacc, gf_exp(si)) ^ rx[sj];
                if (sj == 0)
                    state <= SYN_STORE;
                else
                    sj <= sj - 1;
            end

            SYN_STORE: begin
                syn[si] <= sacc;
                if (si == 5)
                    state <= SYN_CHECK;
                else begin
                    si <= si + 1;
                    sj <= 4'd14;
                    sacc <= 0;
                    state <= SYN;
                end
            end

            SYN_CHECK: begin
                if (syn[0]==0 && syn[1]==0 && syn[2]==0 &&
                    syn[3]==0 && syn[4]==0 && syn[5]==0)
                    state <= OUTPUT;
                else
                    state <= BM_INIT;
            end

            // ---- Berlekamp-Massey ----
            BM_INIT: begin
                C0<=1; C1<=0; C2<=0; C3<=0;
                B0<=1; B1<=0; B2<=0; B3<=0;
                bL<=0; bm<=1; bb<=1; bstep<=0;
                bdelta<=0; bj<=0;
                state <= BM_DISC;
            end

            // Compute discrepancy: delta = S[step] + sum_{j=1}^{L} C[j]*S[step-j]
            BM_DISC: begin
                if (bj == 0) begin
                    bdelta <= syn[bstep];
                    if (bL > 0)
                        bj <= 1;
                    else
                        state <= BM_APPLY;
                end else begin
                    // Add C[bj] * S[bstep - bj]
                    if (bstep >= bj) begin
                        case(bj)
                            1: bdelta <= bdelta ^ gfm(C1, syn[bstep-1]);
                            2: bdelta <= bdelta ^ gfm(C2, syn[bstep-2]);
                            3: bdelta <= bdelta ^ gfm(C3, syn[bstep-3]);
                        endcase
                    end
                    if (bj >= bL)
                        state <= BM_APPLY;
                    else
                        bj <= bj + 1;
                end
            end

            BM_APPLY: begin
                if (bdelta == 0) begin
                    bm <= bm + 1;
                end else if ({1'b0,bL,1'b0} <= {1'b0,bstep}) begin
                    // 2*L <= step: swap
                    T0 <= C0; T1 <= C1; T2 <= C2; T3 <= C3;
                    bcoef <= gfd(bdelta, bb);
                    // C[i] ^= coef * B[i-m]
                    case(bm)
                        1: begin
                            C1 <= C1 ^ gfd(gfm(bdelta, B0), bb);
                            C2 <= C2 ^ gfd(gfm(bdelta, B1), bb);
                            C3 <= C3 ^ gfd(gfm(bdelta, B2), bb);
                        end
                        2: begin
                            C2 <= C2 ^ gfd(gfm(bdelta, B0), bb);
                            C3 <= C3 ^ gfd(gfm(bdelta, B1), bb);
                        end
                        3: begin
                            C3 <= C3 ^ gfd(gfm(bdelta, B0), bb);
                        end
                    endcase
                    // These will be overwritten next cycle for B
                end else begin
                    // No swap, just update C
                    case(bm)
                        1: begin
                            C1 <= C1 ^ gfm(gfd(bdelta, bb), B0);
                            C2 <= C2 ^ gfm(gfd(bdelta, bb), B1);
                            C3 <= C3 ^ gfm(gfd(bdelta, bb), B2);
                        end
                        2: begin
                            C2 <= C2 ^ gfm(gfd(bdelta, bb), B0);
                            C3 <= C3 ^ gfm(gfd(bdelta, bb), B1);
                        end
                        3: begin
                            C3 <= C3 ^ gfm(gfd(bdelta, bb), B0);
                        end
                    endcase
                    bm <= bm + 1;
                end
                state <= BM_ADV;
            end

            BM_ADV: begin
                // Complete the swap if needed
                if (bdelta != 0 && {1'b0,bL,1'b0} <= {1'b0,bstep}) begin
                    B0 <= T0; B1 <= T1; B2 <= T2; B3 <= T3;
                    bL <= bstep + 1 - bL;
                    bb <= bdelta;
                    bm <= 1;
                end
                // Advance
                if (bstep == 5) begin
                    ldeg <= bL;
                    state <= CH_INIT;
                end else begin
                    bstep <= bstep + 1;
                    bj <= 0;
                    state <= BM_DISC;
                end
            end

            // ---- Chien Search ----
            // Evaluate Lambda(alpha^(-j)) for j=0..14
            // alpha^(-j) = alpha^(15-j) mod 15
            // Lambda(x) = C0 + C1*x + C2*x^2 + C3*x^3
            CH_INIT: begin
                cpos <= 0; nerr <= 0;
                calpha <= gf_exp(0); // alpha^(15-0 mod 15) = alpha^0 = 1
                // Start evaluation with Horner from highest degree
                cj <= ldeg;
                case(ldeg)
                    0: cacc <= C0;
                    1: cacc <= C1;
                    2: cacc <= C2;
                    3: cacc <= C3;
                    default: cacc <= 0;
                endcase
                state <= CH_EVAL;
            end

            CH_EVAL: begin
                // Horner step: cacc = cacc * alpha^(-cpos) ^ C[cj-1]
                if (cj == 0) begin
                    // Evaluation complete for this position
                    state <= CH_CHECK;
                end else begin
                    case(cj-1)
                        0: cacc <= gfm(cacc, calpha) ^ C0;
                        1: cacc <= gfm(cacc, calpha) ^ C1;
                        2: cacc <= gfm(cacc, calpha) ^ C2;
                        3: cacc <= gfm(cacc, calpha) ^ C3;
                        default: cacc <= gfm(cacc, calpha);
                    endcase
                    cj <= cj - 1;
                end
            end

            CH_CHECK: begin
                if (cacc == 0 && nerr < 3) begin
                    case(nerr)
                        0: epos0 <= cpos;
                        1: epos1 <= cpos;
                        2: epos2 <= cpos;
                    endcase
                    nerr <= nerr + 1;
                end
                if (cpos == 14) begin
                    state <= CH_VERIFY;
                end else begin
                    cpos <= cpos + 1;
                    // Compute new alpha^(-(cpos+1)) = alpha^(15-(cpos+1)) mod 15
                    // For cpos+1: if cpos+1 == 15, use 0; but cpos goes up to 14
                    if (cpos == 13)
                        calpha <= gf_exp(4'd1); // alpha^(15-14)=alpha^1
                    else if (cpos == 14)
                        calpha <= gf_exp(4'd0); // shouldn't reach
                    else
                        calpha <= gf_exp(4'd14 - cpos); // alpha^(15-(cpos+1)) = alpha^(14-cpos)
                    // Reset Horner
                    cj <= ldeg;
                    case(ldeg)
                        0: cacc <= C0;
                        1: cacc <= C1;
                        2: cacc <= C2;
                        3: cacc <= C3;
                        default: cacc <= 0;
                    endcase
                    state <= CH_EVAL;
                end
            end

            CH_VERIFY: begin
                if (nerr == ldeg[2:0] && nerr > 0)
                    state <= FN_OMEGA;
                else if (nerr == 0 && ldeg == 0)
                    state <= OUTPUT;
                else begin
                    decode_fail <= 1;
                    state <= FAIL;
                end
            end

            // ---- Forney Algorithm ----
            // Phase 0: compute Omega polynomial
            // Omega[k] = sum_{i+j=k, i<7, j<6} C[i] * syn[j], for k=0..5
            FN_OMEGA: begin
                // Compute all omega coefficients combinationally
                om0 <= gfm(C0, syn[0]);
                om1 <= gfm(C0, syn[1]) ^ gfm(C1, syn[0]);
                om2 <= gfm(C0, syn[2]) ^ gfm(C1, syn[1]) ^ gfm(C2, syn[0]);
                om3 <= gfm(C0, syn[3]) ^ gfm(C1, syn[2]) ^ gfm(C2, syn[1]) ^ gfm(C3, syn[0]);
                om4 <= gfm(C0, syn[4]) ^ gfm(C1, syn[3]) ^ gfm(C2, syn[2]) ^ gfm(C3, syn[1]);
                om5 <= gfm(C0, syn[5]) ^ gfm(C1, syn[4]) ^ gfm(C2, syn[3]) ^ gfm(C3, syn[2]);
                fni <= 0;
                fnph <= 0;
                state <= FN_EVAL;
            end

            FN_EVAL: begin
                // Compute error magnitude for error at epos[fni]
                // Using: e = X_j * Omega(X_j^{-1}) / Lambda'(X_j^{-1})
                case(fnph)
                0: begin
                    // Determine position
                    case(fni)
                        0: fnxj <= (epos0 == 0) ? 4'd1 : gf_exp(epos0);
                        1: fnxj <= (epos1 == 0) ? 4'd1 : gf_exp(epos1);
                        2: fnxj <= (epos2 == 0) ? 4'd1 : gf_exp(epos2);
                    endcase
                    case(fni)
                        0: fnxji <= (epos0 == 0) ? 4'd1 : gf_exp(4'd15 - epos0);
                        1: fnxji <= (epos1 == 0) ? 4'd1 : gf_exp(4'd15 - epos1);
                        2: fnxji <= (epos2 == 0) ? 4'd1 : gf_exp(4'd15 - epos2);
                    endcase
                    fnph <= 1;
                end
                1: begin
                    // Evaluate Omega(fnxji) using Horner: ((om5*x + om4)*x + om3)*x + ...
                    // acc = om5
                    fnacc <= om5;
                    fnj <= 4;
                    fnph <= 2;
                end
                2: begin
                    // Horner steps for Omega
                    case(fnj)
                        4: fnacc <= gfm(fnacc, fnxji) ^ om4;
                        3: fnacc <= gfm(fnacc, fnxji) ^ om3;
                        2: fnacc <= gfm(fnacc, fnxji) ^ om2;
                        1: fnacc <= gfm(fnacc, fnxji) ^ om1;
                        0: fnacc <= gfm(fnacc, fnxji) ^ om0;
                    endcase
                    if (fnj == 0) begin
                        fnph <= 3;
                    end else
                        fnj <= fnj - 1;
                end
                3: begin
                    fnov <= fnacc; // store Omega(X_j^{-1})
                    // Now compute Lambda'(X_j^{-1})
                    // Lambda(x) = C0 + C1*x + C2*x^2 + C3*x^3
                    // Lambda'(x) = C1 + 0*x + C3*x^2 (odd-index coeffs, shifted down)
                    // So Lambda'(x) = C1 + C3*x^2
                    // Eval at fnxji: C1 + C3 * fnxji^2
                    fnlpv <= C1 ^ gfm(C3, gfm(fnxji, fnxji));
                    fnph <= 4;
                end
                4: begin
                    // Compute magnitude: fnxj * fnov / fnlpv
                    if (fnlpv != 0) begin
                        case(fni)
                            0: emag0 <= gfm(fnxj, gfd(fnov, fnlpv));
                            1: emag1 <= gfm(fnxj, gfd(fnov, fnlpv));
                            2: emag2 <= gfm(fnxj, gfd(fnov, fnlpv));
                        endcase
                    end else begin
                        case(fni)
                            0: emag0 <= 0;
                            1: emag1 <= 0;
                            2: emag2 <= 0;
                        endcase
                    end
                    fnph <= 5;
                end
                5: begin
                    state <= FN_NEXT;
                    fnph <= 0;
                end
                endcase
            end

            FN_NEXT: begin
                if (fni + 1 >= nerr) begin
                    state <= CORRECT;
                end else begin
                    fni <= fni + 1;
                    fnph <= 0;
                    state <= FN_EVAL;
                end
            end

            // ---- Error Correction ----
            CORRECT: begin
                for (k = 0; k < 15; k = k + 1) begin
                    if (nerr > 0 && epos0 == k[3:0])
                        rx[k] <= rx[k] ^ emag0;
                    if (nerr > 1 && epos1 == k[3:0])
                        rx[k] <= rx[k] ^ emag1;
                    if (nerr > 2 && epos2 == k[3:0])
                        rx[k] <= rx[k] ^ emag2;
                end
                state <= OUTPUT;
            end

            // ---- Output ----
            OUTPUT: begin
                for (k = 0; k < 15; k = k + 1)
                    data_out[k*4 +: 4] <= rx[k];
                error_count <= nerr;
                done <= 1;
                state <= IDLE;
            end

            FAIL: begin
                for (k = 0; k < 15; k = k + 1)
                    data_out[k*4 +: 4] <= rx[k];
                error_count <= 3'd0;
                decode_fail <= 1;
                done <= 1;
                state <= IDLE;
            end

            default: state <= IDLE;

            endcase
        end
    end

endmodule
VEOF

# Compile and simulate
cd /app
iverilog -o sim -I src src/rs_decoder.v testbench/tb_rs_decoder.v && vvp sim

echo "Simulation complete. Results in /app/output/sim_results.txt"
