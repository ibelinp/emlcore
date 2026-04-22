"""
Stack machine — cycle-accurate model.

Opcodes (4-bit):
    0x0 PUSH_X       push input x onto stack
    0x1 PUSH_Y       push second input y onto stack (for 2-operand ops)
    0x2 PUSH_ONE     push Q16.24 constant 1.0
    0x3 HALT         stop
    0x4 EXEC_EML     pop y, pop x, push exp(x) - ln(y)     [Odrzywolek]
    0x5 EXEC_SIN     pop x, push sin(x)                    [CORDIC circular]
    0x6 EXEC_COS     pop x, push cos(x)
    0x7 EXEC_SQRT    pop x, push sqrt(x)
    0x8 EXEC_TAN     pop x, push tan(x)
    0x9 EXEC_ATAN2   pop y, pop x, push atan2(y, x)
    0xA EXEC_POW     pop e, pop b, push b^e
    0xB EXEC_EXP2    pop x, push 2^x
    0xC EXEC_LOG2    pop x, push log2(x)
"""

from cordic import (fx_exp, fx_ln, fx_sin, fx_cos, fx_sqrt,
                    fx_tan, fx_atan2, fx_pow, fx_exp2, fx_log2,
                    OpStats, to_q, from_q, ONE, sub)

PUSH_X      = 0x0
PUSH_Y      = 0x1
PUSH_ONE    = 0x2
HALT        = 0x3
EXEC_EML    = 0x4
EXEC_SIN    = 0x5
EXEC_COS    = 0x6
EXEC_SQRT   = 0x7
EXEC_TAN    = 0x8
EXEC_ATAN2  = 0x9
EXEC_POW    = 0xA
EXEC_EXP2   = 0xB
EXEC_LOG2   = 0xC

OP_NAME = {PUSH_X:"PUSH_X", PUSH_Y:"PUSH_Y", PUSH_ONE:"PUSH_ONE", HALT:"HALT",
           EXEC_EML:"EML", EXEC_SIN:"SIN", EXEC_COS:"COS", EXEC_SQRT:"SQRT",
           EXEC_TAN:"TAN", EXEC_ATAN2:"ATAN2", EXEC_POW:"POW",
           EXEC_EXP2:"EXP2", EXEC_LOG2:"LOG2"}

EXEC_LATENCY = {EXEC_EML:30, EXEC_SIN:24, EXEC_COS:24, EXEC_SQRT:60,
                EXEC_TAN:90, EXEC_ATAN2:24, EXEC_POW:120,
                EXEC_EXP2:70, EXEC_LOG2:80}


class EMLMachine:
    def __init__(self, programs, stack_depth=16, trace=False):
        self.programs    = programs
        self.stack_depth = stack_depth
        self.trace       = trace

    def run(self, func_sel, x, y=0.0):
        prog = self.programs[func_sel]
        stack = []
        stats = OpStats()
        cycles = 0
        x_q, y_q = to_q(x), to_q(y)
        pc = 0
        while True:
            op = prog[pc]
            if self.trace:
                print(f"  pc={pc:02d} {OP_NAME[op]:<6} "
                      f"stack={[f'{from_q(v):.4f}' for v in stack]}")
            if   op == PUSH_X:   stack.append(x_q); cycles += 1; pc += 1
            elif op == PUSH_Y:   stack.append(y_q); cycles += 1; pc += 1
            elif op == PUSH_ONE: stack.append(ONE); cycles += 1; pc += 1
            elif op == EXEC_EML:
                b = stack.pop(); a = stack.pop()
                stack.append(sub(fx_exp(a, stats), fx_ln(b, stats), stats))
                cycles += EXEC_LATENCY[op]; pc += 1
            elif op == EXEC_SIN:
                stack.append(fx_sin(stack.pop(), stats))
                cycles += EXEC_LATENCY[op]; pc += 1
            elif op == EXEC_COS:
                stack.append(fx_cos(stack.pop(), stats))
                cycles += EXEC_LATENCY[op]; pc += 1
            elif op == EXEC_SQRT:
                stack.append(fx_sqrt(stack.pop(), stats))
                cycles += EXEC_LATENCY[op]; pc += 1
            elif op == EXEC_TAN:
                stack.append(fx_tan(stack.pop(), stats))
                cycles += EXEC_LATENCY[op]; pc += 1
            elif op == EXEC_ATAN2:
                yy = stack.pop(); xx = stack.pop()
                stack.append(fx_atan2(yy, xx, stats))
                cycles += EXEC_LATENCY[op]; pc += 1
            elif op == EXEC_POW:
                exp_v = stack.pop(); base_v = stack.pop()
                stack.append(fx_pow(base_v, exp_v, stats))
                cycles += EXEC_LATENCY[op]; pc += 1
            elif op == EXEC_EXP2:
                stack.append(fx_exp2(stack.pop(), stats))
                cycles += EXEC_LATENCY[op]; pc += 1
            elif op == EXEC_LOG2:
                stack.append(fx_log2(stack.pop(), stats))
                cycles += EXEC_LATENCY[op]; pc += 1
            elif op == HALT:
                cycles += 1; break
            else:
                raise ValueError(f"bad opcode {op}")
        return from_q(stack[-1]), cycles, stats
