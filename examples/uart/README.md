# UART TX Example

A small UART transmitter demonstrating sequential control logic,
finite-state-machine behavior, timing and serial protocol verification.

## Design

The transmitter implements:

```text
IDLE
  ↓
START BIT
  ↓
8 DATA BITS
  ↓
STOP BIT
  ↓
IDLE
