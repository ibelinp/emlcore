"""
Full 10-function testbench.  Tolerances match Adam's mz646: abs<1e-2, rel<1e-3.
"""

import math, sys
from eml_machine import EMLMachine
from programs import (PROGRAMS, FN_EXP, FN_LN, FN_SIN, FN_COS, FN_SQRT,
                      FN_TAN, FN_ATAN2, FN_POW, FN_EXP2, FN_LOG2)

ABS_TOL = 1.0e-2
REL_TOL = 1.0e-3

class Stats:
    def __init__(self, name):
        self.name = name; self.n = 0; self.fail = 0
        self.max_abs = 0.0; self.max_rel = 0.0; self.worst = None
        self.total_cycles = 0
        self.total_adds = 0; self.total_shifts = 0; self.total_mults = 0

    def record(self, label, got, ref, cycles, op):
        self.n += 1
        err = abs(got - ref)
        rel = err / max(abs(ref), 1e-12)
        if err > self.max_abs: self.max_abs = err; self.worst = label
        if rel > self.max_rel: self.max_rel = rel
        if err > ABS_TOL and rel > REL_TOL: self.fail += 1
        self.total_cycles += cycles
        self.total_adds   += op.adds
        self.total_shifts += op.shifts
        self.total_mults  += op.mults

    def report(self):
        print(f"\n=== {self.name} ===")
        print(f"  samples      : {self.n}")
        print(f"  failures     : {self.fail}  (abs<{ABS_TOL}, rel<{REL_TOL})")
        print(f"  max abs err  : {self.max_abs:.3e}  @ {self.worst}")
        print(f"  max rel err  : {self.max_rel:.3e}")
        print(f"  avg cycles   : {self.total_cycles/self.n:.1f}")
        print(f"  adds/shifts  : {self.total_adds}/{self.total_shifts}")
        print(f"  MULTIPLIES   : {self.total_mults}   <-- must be 0")


def sweep_1(name, m, fn, xs, ref):
    s = Stats(name)
    for x in xs:
        got, c, op = m.run(fn, x)
        s.record(f"x={x:+.4f}", got, ref(x), c, op)
    s.report()
    return s

def sweep_2(name, m, fn, pairs, ref):
    s = Stats(name)
    for (x, y) in pairs:
        got, c, op = m.run(fn, x, y)
        s.record(f"(x={x:+.3f}, y={y:+.3f})", got, ref(x, y), c, op)
    s.report()
    return s


def main():
    m = EMLMachine(PROGRAMS)
    R = []

    R.append(sweep_1("exp(x)   [-3.0, 4.0]",     m, FN_EXP,
        [round(-3.0 + 0.1*i, 3) for i in range(71)], math.exp))
    R.append(sweep_1("ln(x)    [0.1, 64.0]",     m, FN_LN,
        [0.1*(64.0/0.1)**(i/63) for i in range(64)], math.log))
    R.append(sweep_1("sin(x)   [-2pi, 2pi]",     m, FN_SIN,
        [-2*math.pi + (4*math.pi)*i/99 for i in range(100)], math.sin))
    R.append(sweep_1("cos(x)   [-2pi, 2pi]",     m, FN_COS,
        [-2*math.pi + (4*math.pi)*i/99 for i in range(100)], math.cos))
    R.append(sweep_1("sqrt(x)  [0.01, 100.0]",   m, FN_SQRT,
        [0.01*(100.0/0.01)**(i/99) for i in range(100)], math.sqrt))
    # tan: avoid poles at ±pi/2
    tan_xs = [v for v in (-1.4 + 2.8*i/80 for i in range(81))
              if abs(math.cos(v)) > 0.05]
    R.append(sweep_1("tan(x)   [-1.4, 1.4]",     m, FN_TAN,
        tan_xs, math.tan))
    # atan2: grid of (y, x) on unit-ish box, skipping origin
    atan2_pairs = [(x, y) for x in (-2, -1, -0.5, 0.5, 1, 2)
                           for y in (-2, -1, -0.5, 0.5, 1, 2)]
    R.append(sweep_2("atan2(y, x)",              m, FN_ATAN2,
        atan2_pairs, lambda x, y: math.atan2(y, x)))
    # pow: x in (0, 10], y in [-2, 3]
    pow_pairs = [(x, y) for x in (0.25, 0.5, 1.0, 2.0, 3.0, 5.0)
                         for y in (-2.0, -1.0, -0.5, 0.5, 1.0, 2.0, 3.0)]
    R.append(sweep_2("pow(x, y)",                m, FN_POW,
        pow_pairs, math.pow))
    R.append(sweep_1("exp2(x)  [-4, 8]",         m, FN_EXP2,
        [round(-4 + 12*i/60, 3) for i in range(61)], lambda v: 2.0 ** v))
    R.append(sweep_1("log2(x)  [0.1, 64]",       m, FN_LOG2,
        [0.1*(64.0/0.1)**(i/63) for i in range(64)], math.log2))

    total_n     = sum(r.n for r in R)
    total_fail  = sum(r.fail for r in R)
    total_mults = sum(r.total_mults for r in R)
    print("\n" + "="*52)
    print(f" TOTAL SAMPLES  : {total_n}")
    print(f" TOTAL FAILURES : {total_fail}")
    print(f" TOTAL MULTS    : {total_mults}   <-- must be 0")
    print("="*52)
    ok = total_fail == 0 and total_mults == 0
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
