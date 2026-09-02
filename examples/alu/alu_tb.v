`timescale 1ns/1ps

module alu_tb;

    localparam WIDTH = 4;

    localparam OP_ADD = 3'b000;
    localparam OP_SUB = 3'b001;
    localparam OP_AND = 3'b010;
    localparam OP_OR  = 3'b011;
    localparam OP_XOR = 3'b100;
    localparam OP_NOT = 3'b101;

    reg [WIDTH-1:0] a;
    reg [WIDTH-1:0] b;
    reg [2:0]       op;

    wire [WIDTH-1:0] y;
    wire             zero;
    wire             carry;

    integer errors;

    task check;
        input [WIDTH-1:0] expected_y;
        input expected_zero;
        input expected_carry;
        input [127:0] test_name;

        begin
            #1;

            if (
                y !== expected_y ||
                zero !== expected_zero ||
                carry !== expected_carry
            ) begin

                $display(
                    "TEST_RESULT id=%0s status=FAIL expected_y=%0h actual_y=%0h expected_zero=%0b actual_zero=%0b expected_carry=%0b actual_carry=%0b",
                    test_name,
                    expected_y,
                    y,
                    expected_zero,
                    zero,
                    expected_carry,
                    carry
                );

                errors = errors + 1;
            end
            else begin

                $display(
                    "TEST_RESULT id=%0s status=PASS y=%0h zero=%0b carry=%0b",
                    test_name,
                    y,
                    zero,
                    carry
                );

            end
        end
    endtask

    initial begin

        errors = 0;

        // ADD
        a  = 4'd3;
        b  = 4'd2;
        op = OP_ADD;

        check(
            4'd5,
            1'b0,
            1'b0,
            "TC_ADD"
        );

        // ADD overflow
        a  = 4'hF;
        b  = 4'h1;
        op = OP_ADD;

        check(
            4'h0,
            1'b1,
            1'b1,
            "TC_ADD_OVERFLOW"
        );

        // SUB
        a  = 4'd7;
        b  = 4'd3;
        op = OP_SUB;

        check(
            4'd4,
            1'b0,
            1'b1,
            "TC_SUB"
        );

        // SUB underflow
        a  = 4'd3;
        b  = 4'd7;
        op = OP_SUB;

        check(
            4'hC,
            1'b0,
            1'b0,
            "TC_SUB_UNDERFLOW"
        );

        // AND
        a  = 4'b1100;
        b  = 4'b1010;
        op = OP_AND;

        check(
            4'b1000,
            1'b0,
            1'b0,
            "TC_AND"
        );

        // OR
        a  = 4'b1100;
        b  = 4'b1010;
        op = OP_OR;

        check(
            4'b1110,
            1'b0,
            1'b0,
            "TC_OR"
        );

        // XOR
        a  = 4'b1100;
        b  = 4'b1010;
        op = OP_XOR;

        check(
            4'b0110,
            1'b0,
            1'b0,
            "TC_XOR"
        );

        // NOT
        a  = 4'b1010;
        b  = 4'b0000;
        op = OP_NOT;

        check(
            4'b0101,
            1'b0,
            1'b0,
            "TC_NOT"
        );

        // Zero
        a  = 4'b0000;
        b  = 4'b0000;
        op = OP_ADD;

        check(
            4'b0000,
            1'b1,
            1'b0,
            "TC_ZERO"
        );

        // Default/unsupported opcode
        a  = 4'b1111;
        b  = 4'b1111;
        op = 3'b111;

        check(
            4'b0000,
            1'b1,
            1'b0,
            "TC_DEFAULT"
        );

        if (errors == 0)
            $display("TEST_SUMMARY status=PASS errors=0");
        else
            $display("TEST_SUMMARY status=FAIL errors=%0d", errors);

        $finish;

    end

endmodule
