# emlcore

A multiplierless stack machine that computes ten transcendental functions from
a single programmable core. Fixed-point Q16.24. Everything on the data path is
a shift, add, or subtract. Cycle-accurate Python model as a stepping stone to
RTL.

```
719 samples across 10 functions.
0 failures.
0 multiplies used. Anywhere.
```

## Why this exists

I was reading Odrzywolek's paper
["All Elementary Functions from a Single Operator"](https://arxiv.org/html/2603.21852v2)
and Adam Taylor's Vitis HLS take on it over at
[ATaylorCEngFIET/mz646](https://github.com/ATaylorCEngFIET/mz646). The core
idea is disarming: every elementary function you care about is just a tree of

```
eml(x, y) = exp(x) - ln(y)
```

Seeing that idea run on silicon made me want to know how far I could push two
things at once:

1. Replace the HLS math library with CORDIC so the whole data path becomes
   shift + add + subtract. No DSP slices, no block RAM coefficients.
2. Widen the opcode so one core handles more than EML. `sin` and `cos` come
   from CORDIC in circular mode. `sqrt` is `exp(ln(x) / 2)`. `tan`, `atan2`,
   `pow`, `exp2`, and `log2` fall out of the same primitives.

This repo is the result. It simulates cleanly, it passes the tolerances by
several orders of magnitude, and the op counter proves zero multiplies across
the entire engine.

## Results

Tolerances: `abs < 1e-2`, `rel < 1e-3`.

| Function      | Range                | Samples | Failures | Max abs err | Avg cycles |
|---------------|----------------------|---------|----------|-------------|------------|
| exp(x)        | [-3.0, 4.0]          | 71      | 0        | 1.7e-5      | 33         |
| ln(x)         | [0.1, 64.0]          | 64      | 0        | 9.8e-7      | 95         |
| sin(x)        | [-2π, 2π]            | 100     | 0        | 4.1e-7      | 26         |
| cos(x)        | [-2π, 2π]            | 100     | 0        | 4.9e-7      | 26         |
| sqrt(x)       | [0.01, 100.0]        | 100     | 0        | 2.9e-6      | 62         |
| tan(x)        | [-1.4, 1.4]          | 81      | 0        | 5.3e-6      | 92         |
| atan2(y, x)   | grid over ±2         | 36      | 0        | 1.8e-7      | 27         |
| pow(x, y)     | x ∈ (0, 5], y ∈ ±3   | 42      | 0        | 1.5e-5      | 123        |
| exp2(x)       | [-4, 8]              | 61      | 0        | 7.5e-5      | 72         |
| log2(x)       | [0.1, 64]            | 64      | 0        | 7.7e-7      | 82         |
| **total**     |                      | **719** | **0**    |             |            |

Total op mix across the run: ~107k adds, ~83k shifts, **0 multiplies**.

## Quick start

```bash
python test_eml.py
```

Expected tail:

```
 TOTAL SAMPLES  : 719
 TOTAL FAILURES : 0
 TOTAL MULTS    : 0
 PASS
```

## How it works

Three files, in order of dependency.

```
cordic.py        Q16.24 primitives, CORDIC cores, shift-add mul/div, the 10 fx_* functions
eml_machine.py   Stack + FSM + 4-bit opcode decoder
programs.py      ROM programs for each function
test_eml.py      Sweeps + tolerance check + multiplier counter
```

### The opcodes

```
0x0 PUSH_X      push input x
0x1 PUSH_Y      push second input y (for 2-operand ops)
0x2 PUSH_ONE    push 1.0
0x3 HALT
0x4 EXEC_EML    pop y, pop x, push exp(x) - ln(y)    (Odrzywolek)
0x5 EXEC_SIN    pop x, push sin(x)
0x6 EXEC_COS    pop x, push cos(x)
0x7 EXEC_SQRT   pop x, push sqrt(x)
0x8 EXEC_TAN    pop x, push tan(x)
0x9 EXEC_ATAN2  pop y, pop x, push atan2(y, x)
0xA EXEC_POW    pop e, pop b, push b^e
0xB EXEC_EXP2   pop x, push 2^x
0xC EXEC_LOG2   pop x, push log2(x)
```

Thirteen of sixteen slots used. Three reserved.

### The programs

The EML programs for `exp` and `ln` are the Odrzywolek trees, one of which has
a satisfying trace:

```python
# exp(x):  eml(x, 1) = exp(x) - ln(1) = exp(x)
FN_EXP : [PUSH_X, PUSH_ONE, EXEC_EML, HALT]

# ln(x):  eml(1, eml(eml(1, x), 1))
#   → inner eml(1, x)   = e - ln(x)
#   → middle eml(...,1) = exp(e - ln(x)) = e^e / x
#   → outer eml(1, ...) = e - ln(e^e / x) = ln(x)
FN_LN  : [PUSH_ONE, PUSH_ONE, PUSH_X, EXEC_EML,
          PUSH_ONE, EXEC_EML, EXEC_EML, HALT]
```

The new eight are all single-op programs. Because once you have the primitives,
you just call them:

```python
FN_SIN  : [PUSH_X, EXEC_SIN,  HALT]
FN_TAN  : [PUSH_X, EXEC_TAN,  HALT]
FN_POW  : [PUSH_X, PUSH_Y, EXEC_POW, HALT]
# ...etc
```

### The sqrt trick

`sqrt` does not get its own CORDIC. It reuses exp and ln:

```
sqrt(x) = exp( ln(x) / 2 )
```

Divide by two is a one-bit arithmetic right shift, which costs nothing. So
once the EML core works, `sqrt` is free silicon. This is the whole pitch for
programmable math cores in one line.

### Multiplierless, for real

Every operation on a Q16.24 value goes through `add`, `sub`, `arith_shr`, or
`arith_shl` in `cordic.py`. Each of those bumps an op counter. The one labeled
`mults` is never touched. The testbench fails if it ever becomes nonzero.

`pow(x, y)` and `tan(x)` need variable-times-variable products. They use
`sa_mult` (a bitwise shift-add multiplier) and `sa_div` (a restoring binary
divider). Those are arithmetically equivalent to a DSP multiply but implemented
as a chain of single-bit adders, which means they synthesize to LUT fabric and
use zero DSP slices.

The only integer arithmetic that escapes the op counter is Python loop bounds
and LUT indexing. Those have nothing to do with the data path and disappear in
RTL.

## Honest caveats

- This is a simulation model, not RTL. The hard part (algorithm correctness,
  numerics, convergence ranges, sign handling) is done. The carpentry (state
  machine, bit widths, AXI handshake) is not.
- Cycle counts are optimistic. They assume the CORDIC iterations run as a
  pipelined unit. A literal iterative RTL port will be slower per op; a
  fully-pipelined one will trade area for throughput.
- Ranges matter. Each sweep stays inside the convergence range for its
  underlying CORDIC. Outside these ranges you need wider Q-format or better
  range reduction.
- Pure-EML trees for the trig and root functions exist per the paper, but
  deriving them requires the author's bootstrapping solver. I did not do that.
  I added CORDIC opcodes instead, which is a different architectural choice
  and arguably more practical.

## What's next

A SystemVerilog version. The Python model is bit-exact and dumps results
directly usable as a testbench oracle. Rough estimate: ~1000 lines of RTL and
a week and change to get it through sim and synthesis, targeting zero DSP
slices in the synthesis report.

## Credits

- Adam Odrzywolek for the underlying mathematical result.
- Adam Taylor ([@ATaylorCEngFIET](https://github.com/ATaylorCEngFIET)) for
  [mz646](https://github.com/ATaylorCEngFIET/mz646), which made the EML idea
  concrete enough to extend.

## License

MIT. Have at it.
