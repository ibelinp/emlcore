# FPGA_MATH

A multiplierless stack machine that computes `exp`, `ln`, `sin`, `cos`, and `sqrt`
from a single programmable core. Fixed-point Q16.24, shift-and-add only,
cycle-accurate Python model as a stepping stone to RTL.

```
435 samples across 5 functions.
0 failures.
0 multiplies used. Anywhere.
```

## Why this exists

I was reading Odrzywolek's paper
["All Elementary Functions from a Single Operator"](https://arxiv.org/html/2603.21852v2)
and Adam Taylor's Vitis HLS take on it over at
[ATaylorCEngFIET/mz646](https://github.com/ATaylorCEngFIET/mz646). The core idea
is disarming: every elementary function you care about is just a tree of

```
eml(x, y) = exp(x) - ln(y)
```

Adam's implementation proves the concept runs on silicon. It uses the HLS math
library for `exp` and `ln`, which pulls in multipliers and BRAM, and it covers
exp and ln only.

I wanted to know how far I could push two ideas at once:

1. Replace the math library with CORDIC so the whole data path becomes
   shift + add + subtract. No multipliers, no block RAM coefficients.
2. Widen the opcode so one core handles more than EML. sin and cos come
   from CORDIC in circular mode. sqrt falls out for free.

This repo is the result. It simulates cleanly, it passes Adam's tolerances by
several orders of magnitude, and the op counter proves zero multiplies across
the entire engine.

## Results

Tolerances match Adam's testbench: `abs < 1e-2`, `rel < 1e-3`.

| Function | Range          | Samples | Failures | Max abs err | Max rel err | Avg cycles |
|----------|----------------|---------|----------|-------------|-------------|------------|
| exp(x)   | [-3.0, 4.0]    | 71      | 0        | 1.7e-5      | 2.9e-6      | 33         |
| ln(x)    | [0.1, 64.0]    | 64      | 0        | 9.8e-7      | 1.1e-5      | 95         |
| sin(x)   | [-2π, 2π]      | 100     | 0        | 4.1e-7      | 1.5e-3      | 26         |
| cos(x)   | [-2π, 2π]      | 100     | 0        | 4.9e-7      | 3.1e-5      | 26         |
| sqrt(x)  | [0.01, 100.0]  | 100     | 0        | 2.9e-6      | 1.6e-6      | 32         |

Totals across the whole run: 88k adds, 57k shifts, **0 multiplies**.

## Quick start

```bash
python test_eml.py
```

Expected tail:

```
 TOTAL SAMPLES  : 435
 TOTAL FAILURES : 0
 TOTAL MULTIPLIES USED : 0
 PASS
```

## How it works

Three files, in order of dependency.

```
cordic.py        Q16.24 fixed-point primitives and CORDIC cores
eml_machine.py   Stack + FSM + 3-bit opcode decoder
programs.py      ROM programs for each function
test_eml.py      Sweeps + tolerance check + multiplier counter
```

### The opcodes

```
000 PUSH_X     push input x
001 PUSH_ONE   push Q16.24 constant 1.0
010 EXEC_EML   pop y, pop x, push exp(x) - ln(y)    (Odrzywolek)
011 HALT       done
100 EXEC_SIN   pop x, push sin(x)                   (CORDIC circular)
101 EXEC_COS   pop x, push cos(x)                   (CORDIC circular)
110 EXEC_SQRT  pop x, push sqrt(x)
```

### The programs

Adam's exp and ln programs drop in unchanged:

```python
FN_EXP : [PUSH_X, PUSH_ONE, EXEC_EML, HALT]
FN_LN  : [PUSH_ONE, PUSH_ONE, PUSH_X, EXEC_EML,
          PUSH_ONE, EXEC_EML, EXEC_EML, HALT]
```

The new ones are one-liners:

```python
FN_SIN : [PUSH_X, EXEC_SIN,  HALT]
FN_COS : [PUSH_X, EXEC_COS,  HALT]
FN_SQRT: [PUSH_X, EXEC_SQRT, HALT]
```

### The sqrt trick

`sqrt` does not get its own CORDIC. It reuses exp and ln:

```
sqrt(x) = exp( ln(x) / 2 )
```

Divide by two is a one-bit arithmetic right shift, which costs nothing. So once
the EML core works, sqrt is free silicon. This is the whole pitch for
programmable math cores in one line.

### Multiplierless, for real

Every operation on a Q16.24 value goes through `add`, `sub`, `arith_shr`, or
`arith_shl` in `cordic.py`. Each of those bumps an op counter. The one labeled
`mults` is never touched. The testbench fails if it ever becomes nonzero. The
only integer multiplication that happens is inside Python's loop bounds and LUT
indices, which have nothing to do with the data path.

## Honest caveats

- This is a simulation model, not RTL. The hard part (algorithm correctness,
  numerics, convergence range) is done. The carpentry (state machine, bit
  widths, handshakes) is not.
- Cycle counts are optimistic. They assume the CORDIC iterations run as a
  pipelined unit and that range reduction is free. A real iterative RTL
  implementation will be slower per op; a pipelined one will trade area for
  throughput.
- Ranges matter. `exp` is sweep-tested over `[-3, 4]`, `ln` over `[0.1, 64]`,
  and so on. Outside these, you need wider Q-format or better range reduction.
- Pure-EML programs for sin, cos, and sqrt do exist per the paper, but deriving
  them requires running the author's bootstrapping solver. I did not do that.
  I added CORDIC opcodes instead, which is a different (arguably more useful)
  architectural point.

## What's next

A SystemVerilog version. The Python model is bit-exact and dumps results
directly usable as a testbench oracle. Rough estimate is ~1000 lines of RTL
and a week and change to get it through sim and synthesis, targeting zero DSP
slices in the synthesis report.

## Credits

- Adam Odrzywolek for the underlying result.
- Adam Taylor ([@ATaylorCEngFIET](https://github.com/ATaylorCEngFIET)) for
  [mz646](https://github.com/ATaylorCEngFIET/mz646), which made the EML idea
  concrete enough to extend.

## License

MIT. Have at it.
