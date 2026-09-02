`timescale 1ns/1ps

module counter_tb;

    parameter WIDTH = 4;

    reg clk;
    reg rst;
    reg en;

    wire [WIDTH-1:0] count;

    integer errors;

    counter #(
        .WIDTH(WIDTH)
    ) dut (
        .clk(clk),
        .rst(rst),
        .en(en),
        .count(count)
    );

    always #5 clk = ~clk;

    task check_count;
        input [WIDTH-1:0] expected;
        input [127:0] test_name;
        begin
            #1;

            if (count !== expected) begin
                $display(
                    "TEST_RESULT id=%0s status=FAIL expected=%0d actual=%0d",
                    test_name,
                    expected,
                    count
                );
                errors = errors + 1;
            end
            else begin
                $display(
                    "TEST_RESULT id=%0s status=PASS expected=%0d actual=%0d",
                    test_name,
                    expected,
                    count
                );
            end
        end
    endtask

    initial begin
        clk = 1'b0;
        rst = 1'b1;
        en  = 1'b0;
        errors = 0;

        // Reset
        @(posedge clk);
        #1;

        check_count(4'd0, "TC_RESET");

        // Enable and count
        rst = 1'b0;
        en  = 1'b1;

        @(posedge clk);
        check_count(4'd1, "TC_INCREMENT_1");

        @(posedge clk);
        check_count(4'd2, "TC_INCREMENT_2");

        @(posedge clk);
        check_count(4'd3, "TC_INCREMENT_3");

        // Disable
        en = 1'b0;

        @(posedge clk);
        check_count(4'd3, "TC_HOLD");

        // Re-enable
        en = 1'b1;

        @(posedge clk);
        check_count(4'd4, "TC_REENABLE");

        // Wrap-around
        repeat (11) @(posedge clk);

        check_count(4'd15, "TC_WRAP_PREP");

        @(posedge clk);
        check_count(4'd0, "TC_WRAP");

        if (errors == 0)
            $display("TEST_SUMMARY status=PASS errors=0");
        else
            $display("TEST_SUMMARY status=FAIL errors=%0d", errors);

        $finish;
    end

endmodule
