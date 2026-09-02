`timescale 1ns/1ps

module fifo_tb;

    localparam DATA_WIDTH = 8;
    localparam DEPTH      = 4;

    reg clk;
    reg rst;

    reg wr_en;
    reg [DATA_WIDTH-1:0] wr_data;

    reg rd_en;
    wire [DATA_WIDTH-1:0] rd_data;

    wire full;
    wire empty;

    integer errors;

    fifo #(
        .DATA_WIDTH(DATA_WIDTH),
        .DEPTH(DEPTH)
    ) dut (
        .clk(clk),
        .rst(rst),
        .wr_en(wr_en),
        .wr_data(wr_data),
        .rd_en(rd_en),
        .rd_data(rd_data),
        .full(full),
        .empty(empty)
    );

    always #5 clk = ~clk;

    task write_data;
        input [DATA_WIDTH-1:0] data;
        begin
            @(negedge clk);

            wr_en   = 1'b1;
            wr_data = data;

            @(negedge clk);

            wr_en   = 1'b0;
        end
    endtask

    task read_check;
        input [DATA_WIDTH-1:0] expected;
        input [127:0] test_name;

        begin
            @(negedge clk);

            rd_en = 1'b1;

            @(posedge clk);
            #1;

            if (rd_data !== expected) begin
                $display(
                    "TEST_RESULT id=%0s status=FAIL expected=%0d actual=%0d",
                    test_name,
                    expected,
                    rd_data
                );

                errors = errors + 1;
            end
            else begin
                $display(
                    "TEST_RESULT id=%0s status=PASS expected=%0d actual=%0d",
                    test_name,
                    expected,
                    rd_data
                );
            end

            @(negedge clk);
            rd_en = 1'b0;
        end
    endtask

    initial begin
        clk     = 1'b0;
        rst     = 1'b1;
        wr_en   = 1'b0;
        wr_data = 0;
        rd_en   = 1'b0;

        errors = 0;

        // Reset
        @(posedge clk);
        #1;

        if (!empty) begin
            $display(
                "TEST_RESULT id=TC_RESET status=FAIL expected=EMPTY actual=NOT_EMPTY"
            );
            errors = errors + 1;
        end
        else begin
            $display(
                "TEST_RESULT id=TC_RESET status=PASS"
            );
        end

        rst = 1'b0;

        // Fill FIFO
        write_data(8'h11);
        write_data(8'h22);
        write_data(8'h33);
        write_data(8'h44);

        #1;

        if (!full) begin
            $display(
                "TEST_RESULT id=TC_FULL status=FAIL expected=FULL actual=NOT_FULL"
            );
            errors = errors + 1;
        end
        else begin
            $display(
                "TEST_RESULT id=TC_FULL status=PASS"
            );
        end

        // Read FIFO
        read_check(8'h11, "TC_READ_1");
        read_check(8'h22, "TC_READ_2");
        read_check(8'h33, "TC_READ_3");
        read_check(8'h44, "TC_READ_4");

        #1;

        if (!empty) begin
            $display(
                "TEST_RESULT id=TC_EMPTY status=FAIL expected=EMPTY actual=NOT_EMPTY"
            );
            errors = errors + 1;
        end
        else begin
            $display(
                "TEST_RESULT id=TC_EMPTY status=PASS"
            );
        end

        if (errors == 0)
            $display("TEST_SUMMARY status=PASS errors=0");
        else
            $display("TEST_SUMMARY status=FAIL errors=%0d", errors);

        $finish;
    end

endmodule
