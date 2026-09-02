# FIFO Example

A small synchronous FIFO intended to demonstrate verification of a
stateful RTL design.

## Design Features

- Parameterized data width
- Parameterized depth
- Write interface
- Read interface
- Full indication
- Empty indication
- Circular write pointer
- Circular read pointer
- Occupancy counter

Default configuration:

```text
DATA_WIDTH = 8
DEPTH      = 4
