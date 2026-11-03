`timescale 1ns / 1ps

module tb_rs_decoder;
    parameter NUM_TESTS = 30;
    parameter CLK_PERIOD = 10;

    reg         clk;
    reg         rst_n;
    reg         start;
    reg  [59:0] data_in;
    wire        done;
    wire        decode_fail;
    wire [59:0] data_out;
    wire [2:0]  error_count;

    // Test vector storage
    reg [59:0] test_vectors [0:NUM_TESTS-1];

    // Result file
    integer result_file;
    integer i;
    integer test_id;
    integer timeout_counter;

    // DUT instantiation
    rs_decoder dut (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .data_in(data_in),
        .done(done),
        .decode_fail(decode_fail),
        .data_out(data_out),
        .error_count(error_count)
    );

    // Clock generation
    initial begin
        clk = 0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end

    // Load test vectors and run tests
    initial begin
        // Load test vectors
        $readmemh("/app/testbench/test_vectors.tv", test_vectors);

        // Open result file
        result_file = $fopen("/app/output/sim_results.txt", "w");
        if (result_file == 0) begin
            $display("ERROR: Cannot open result file");
            $finish;
        end

        // Reset
        rst_n = 0;
        start = 0;
        data_in = 60'h0;
        #(CLK_PERIOD * 5);
        rst_n = 1;
        #(CLK_PERIOD * 2);

        // Run all test vectors
        for (test_id = 0; test_id < NUM_TESTS; test_id = test_id + 1) begin
            // Apply input
            @(posedge clk);
            data_in = test_vectors[test_id];
            start = 1;
            @(posedge clk);
            start = 0;

            // Wait for done with timeout
            timeout_counter = 0;
            while (!done && timeout_counter < 5000) begin
                @(posedge clk);
                timeout_counter = timeout_counter + 1;
            end

            if (timeout_counter >= 5000) begin
                $display("TIMEOUT on test %0d", test_id);
                $fwrite(result_file, "%0d TIMEOUT 0 0\n", test_id);
            end else begin
                $fwrite(result_file, "%0d %015H %0d %0d\n",
                    test_id, data_out, error_count, decode_fail);
                $display("Test %0d: out=%015H errors=%0d fail=%0d",
                    test_id, data_out, error_count, decode_fail);
            end

            // Wait a few cycles between tests
            repeat(5) @(posedge clk);
        end

        $fclose(result_file);
        $display("\nAll %0d tests completed. Results written to /app/output/sim_results.txt", NUM_TESTS);
        $finish;
    end

    // Safety timeout
    initial begin
        #(CLK_PERIOD * 500000);
        $display("GLOBAL TIMEOUT");
        $finish;
    end

endmodule
