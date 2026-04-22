"""
ROM programs for the multi-opcode stack machine.

Odrzywolek EML-native (match Adam Taylor's mz646):
    exp(x)  :  PUSH_X, PUSH_ONE, EML, HALT
    ln(x)   :  PUSH_ONE, PUSH_ONE, PUSH_X, EML,
               PUSH_ONE, EML, EML, HALT

CORDIC / composed:
    sin, cos, tan, sqrt, atan2, pow, exp2, log2  -- each a single primitive op.
"""

from eml_machine import (PUSH_X, PUSH_Y, PUSH_ONE, HALT,
                         EXEC_EML, EXEC_SIN, EXEC_COS, EXEC_SQRT,
                         EXEC_TAN, EXEC_ATAN2, EXEC_POW,
                         EXEC_EXP2, EXEC_LOG2)

FN_EXP   = 0
FN_LN    = 1
FN_SIN   = 2
FN_COS   = 3
FN_SQRT  = 4
FN_TAN   = 5
FN_ATAN2 = 6
FN_POW   = 7
FN_EXP2  = 8
FN_LOG2  = 9

PROGRAMS = {
    FN_EXP  : [PUSH_X, PUSH_ONE, EXEC_EML, HALT],
    FN_LN   : [PUSH_ONE, PUSH_ONE, PUSH_X, EXEC_EML,
               PUSH_ONE, EXEC_EML, EXEC_EML, HALT],
    FN_SIN  : [PUSH_X, EXEC_SIN,  HALT],
    FN_COS  : [PUSH_X, EXEC_COS,  HALT],
    FN_SQRT : [PUSH_X, EXEC_SQRT, HALT],
    FN_TAN  : [PUSH_X, EXEC_TAN,  HALT],
    FN_ATAN2: [PUSH_X, PUSH_Y, EXEC_ATAN2, HALT],   # atan2(y, x)
    FN_POW  : [PUSH_X, PUSH_Y, EXEC_POW,   HALT],   # pow(x, y)
    FN_EXP2 : [PUSH_X, EXEC_EXP2, HALT],
    FN_LOG2 : [PUSH_X, EXEC_LOG2, HALT],
}
