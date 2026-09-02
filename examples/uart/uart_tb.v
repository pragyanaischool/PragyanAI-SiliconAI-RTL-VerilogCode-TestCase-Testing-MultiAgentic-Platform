`timescale 1ns/1ps

module uart_tb;

    localparam CLK_PER_BIT = 4;

    reg clk;
    reg rst;

    reg tx_start;
    reg [7:0] tx_data;

    wire tx;
    wire busy;

    integer errors;
    integer i;

    reg [7:0] received;

    uart_tx #(
        .CLK_PER_BIT(CLK_PER_BIT)
    ) dut (
        .clk(clk),
        .rst(rst),
        .tx_start(tx_start),
        .tx_data(tx_data),
        .tx(tx),
        .busy(busy)
    );

    always #5 clk = ~clk;

    task transmit_and_check;
        input [7:0] data;
        input [127:0] test_name;

        begin
            received = 0;

            @(negedge clk);

            tx_data  = data;
            tx_start = 1'b1;

            @(negedge clk);
            tx_start = 1'b0;

            // Wait for start bit
            wait (busy == 1'b1);

            repeat (CLK_PER_BIT/2)
                @(posedge clk);

            if (tx !== 1'b0) begin
                $display(
                    "TEST_RESULT id=%0s status=FAIL reason=BAD_START_BIT",
                    test_name
                );
                errors = errors + 1;
            end

            // Move to center of first data bit.
            repeat (CLK_PER_BIT)
                @(posedge clk);

            for (i = 0; i < 8; i = i + 1) begin
                received[i] = tx;

                repeat (CLK_PER_BIT)
                    @(posedge clk);
            end

            // Stop bit
            if (tx !== 1'b1) begin
                $display(
                    "TEST_RESULT id=%0s status=FAIL reason=BAD_STOP_BIT",
                    test_name
                );
                errors = errors + 1;
            end

            repeat (CLK_PER_BIT)
                @(posedge clk);

            if (received !== data) begin
                $display(
                    "TEST_RESULT id=%0s status=FAIL expected=%02h actual=%02h",
                    test_name,
                    data,
                    received
                );
                errors = errors + 1;
            end
            else begin
                $display(
                    "TEST_RESULT id=%0s status=PASS expected=%02h actual=%02h",
                    test_name,
                    data,
                    received
                );
            end
        end
    endtask

    initial begin
        clk      = 1'b0;
        rst      = 1'b1;
        tx_start = 1'b0;
        tx_data  = 8'h00;
        errors   = 0;

        // Reset
        repeat (2)
            @(posedge clk);

        rst = 1'b0;

        transmit_and_check(
            8'hA5,
            "TC_UART_A5"
        );

        transmit_and_check(
            8'h3C,
            "TC_UART_3C"
        );

        transmit_and_check(
            8'h00,
            "TC_UART_00"
        );

        transmit_and_check(
            8'hFF,
            "TC_UART_FF"
        );

        if (errors == 0)
            $display("TEST_SUMMARY status=PASS errors=0");
        else
            $display("TEST_SUMMARY status=FAIL errors=%0d", errors);

        $finish;
    end

endmodule
