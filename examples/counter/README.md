# Counter Example

A simple parameterized synchronous up-counter designed as a starter
example for PragyanAI SiliconAI.

## Design

The counter supports:

- Synchronous reset
- Enable control
- Increment operation
- Hold behavior when disabled
- Natural binary wrap-around
- Configurable counter width

## RTL

File:

`counter.v`

Interface:

| Signal | Direction | Description |
|---|---|---|
| `clk` | input | Clock |
| `rst` | input | Synchronous active-high reset |
| `en` | input | Counter enable |
| `count` | output | Counter value |

## Testbench

File:

`counter_tb.v`

The testbench checks:

1. Reset
2. First increment
3. Multiple increments
4. Hold when disabled
5. Re-enable
6. Counter wrap-around

## Run with Icarus Verilog

From the repository root:

```bash
iverilog -g2012 \
    -o counter_sim \
    examples/counter/counter.v \
    examples/counter/counter_tb.v

vvp counter_sim
