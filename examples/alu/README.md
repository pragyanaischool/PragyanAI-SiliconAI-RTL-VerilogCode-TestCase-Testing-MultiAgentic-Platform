# ALU Example

A small combinational Arithmetic Logic Unit designed to demonstrate
functional verification, boundary testing and mutation testing.

## Supported Operations

| Opcode | Operation |
|---|---|
| `000` | ADD |
| `001` | SUB |
| `010` | AND |
| `011` | OR |
| `100` | XOR |
| `101` | NOT |
| `111` | Default |

## Interface

| Signal | Direction | Description |
|---|---|---|
| `a` | input | Operand A |
| `b` | input | Operand B |
| `op` | input | Operation |
| `y` | output | Result |
| `zero` | output | Result is zero |
| `carry` | output | Carry/compare indication |

Default width:

```text
WIDTH = 4
