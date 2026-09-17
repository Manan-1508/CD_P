# OptiTAC: Intermediate Code (Three-Address Code) Optimization Engine

---

## Overview

OptiTAC is a compiler middle-end optimization tool designed to analyze, partition, and optimize Three-Address Code (TAC) sequences.

The engine parses raw intermediate instructions into Quadruples, partitions them into Basic Blocks using the Dragon Book Leader Identification Algorithm, and executes local optimization passes.

---

## Implemented Features (Phase 1 / Review 1)

1. **TAC Lexer & Parser:**
   - Tokenizes arithmetic assignments, copies, conditional jumps (`if <cond> goto <label>`), unconditional jumps (`goto <label>`), and labels.
   - Structures statements into `Quadruple(op, arg1, arg2, result)`.

2. **Basic Block Partitioning:**
   - Implements the 3-rule Leader Identification Algorithm (Dragon Book).
   - Segments code into single-entry, single-exit basic blocks.

3. **Multi-Pass Optimization:**
   - **Constant Folding:** Evaluates static arithmetic expressions at compile time.
   - **Constant Propagation:** Replaces variables with known constant values downstream.
   - **Common Subexpression Elimination (CSE):** Eliminates duplicate expressions via value-numbering with commutative operator normalization (`a + b` == `b + a`).
   - **Dead Code Elimination (DCE):** Prunes unreferenced temporary variables.

4. **Telemetry & Verification:**
   - Generates side-by-side diff comparison between original and optimized TAC.
   - Computes reduction metrics (% statement reduction, constant folds, temporaries saved).

---

## How to Run

Requirements: Python 3.8+ (no external dependencies required)

```bash
python prototype.py
```
