# OptiTAC: Intermediate Code (Three-Address Code) Optimization & Analysis Engine

OptiTAC is an intermediate code analysis and multi-pass compiler optimization framework. It parses Three-Address Code (TAC), constructs formal Control Flow Graphs (CFG), executes mathematical Data-Flow Analyses (Available Expressions and Liveness Analysis), and applies local and global optimization transformations.

---

## Architecture & Directory Structure

```
├── optitac/
│   ├── __init__.py           # Package exports
│   ├── ir.py                 # Quadruple data structure & instruction semantics
│   ├── parser.py             # Dynamic TAC parser supporting full instruction set & comments
│   ├── cfg.py                # CFG construction, Dominator trees, loops & ASCII/DOT visualizers
│   ├── dataflow.py           # Available Expressions & Liveness fixed-point iterative solvers
│   ├── optimizer.py          # Multi-pass intra-block and inter-block optimization engine
│   └── telemetry.py          # Instruction reduction & estimated cycle latency metrics
├── benchmarks/
│   ├── 01_arithmetic_cse.tac # Constant folding, algebraic identities & DAG CSE
│   ├── 02_branching_dce.tac  # Multi-block branching & dead code elimination
│   ├── 03_while_loop.tac     # Iterative while loop, back-edges & natural loops
│   ├── 04_global_cse.tac     # Cross-block common subexpression reuse
│   └── 05_array_address.tac  # Array indexing (4*i) offset optimization
├── optitac_cli.py            # Unified command-line interface & interactive menu runner
├── run_tests.py              # Automated test runner with comparative benchmark matrix
└── prototype.py              # Phase 1 standalone reference prototype
```

---

## Core Capabilities

### 1. Dynamic TAC Parser & Intermediate Representation
- Tokenizes arithmetic assignments (`+`, `-`, `*`, `/`, `%`), bitwise operators (`&`, `|`, `^`), unary negations, and copy assignments.
- Supports control-flow constructs: conditional jumps (`if a > b goto L1`, `ifFalse x goto L2`), unconditional jumps (`goto L`), function parameters/calls (`param x`, `call f, 2`), and array indexing (`x = a[i]`, `a[i] = x`).
- Strips single-line (`//`, `#`) and multi-line (`/* ... */`) comments while preserving source line references.

### 2. Control Flow Graph (CFG) Engine
- **Leader Identification (§8.4 Dragon Book)**:
  - First statement is a leader.
  - Any statement targeted by a conditional or unconditional branch is a leader.
  - Any statement immediately following a branch is a leader.
- **Topology Analysis**:
  - Computes directed predecessor and successor sets.
  - Computes Dominance Relations ($D(n) = \{n\} \cup \bigcap_{p \in \text{Pred}(n)} D(p)$).
  - Detects Natural Loops via back-edges ($n \to d$ where $d \text{ dom } n$).
  - Exports visual ASCII block diagrams in terminal and Graphviz DOT (`.dot`) formats.

### 3. Data-Flow Analysis Framework
- **Available Expressions Analysis (Forward Analysis, Meet = $\cap$)**:
  - Transfer function: $\text{OUT}[B] = \text{GEN}[B] \cup (\text{IN}[B] - \text{KILL}[B])$
  - Fixed-point iteration identifies expressions available along all entry paths for **Global CSE**.
- **Liveness Analysis (Backward Analysis, Meet = $\cup$)**:
  - Transfer function: $\text{IN}[B] = \text{USE}[B] \cup (\text{OUT}[B] - \text{DEF}[B])$
  - Computes active variables at block boundaries for **Global Dead Code Elimination**.

### 4. Multi-Pass Optimization Engine
- **Local Optimizations (Intra-Block)**:
  - Constant Folding: Evaluates constant expressions at compile time.
  - Constant & Copy Propagation: Replaces downstream variable uses with folded constants and aliased variables.
  - Algebraic Identities: $x + 0 \to x$, $x - 0 \to x$, $x \times 1 \to x$, $x \times 0 \to 0$, $x - x \to 0$, $x / 1 \to x$.
  - DAG-based Local CSE: Canonical value numbering with commutative normalization ($a + b \equiv b + a$).
- **Global Optimizations (Inter-Block)**:
  - Global CSE: Replaces redundant evaluations across basic blocks using Available Expressions.
  - Global DCE: Eliminates assignments to variables dead at block exit using Liveness sets.
  - Unreachable Block Pruning: Removes orphaned blocks from the CFG.
- **Fixed-Point Convergence**: Iteratively applies passes until no further transformations occur.

---

## Execution & Usage

Requirements: Python 3.8+ (Standard Library only, zero external pip dependencies required).

### Run Automated Benchmark Test Suite
Runs all 5 benchmarks, validates transformations, and displays comparative reduction metrics:
```bash
python run_tests.py
```

### Run Interactive Demonstration Tool
Launches an interactive menu to run benchmarks, inspect custom TAC files, or paste code directly:
```bash
python optitac_cli.py
```

### CLI Command Options
Run on a specific `.tac` file with CFG, data-flow sets, and optimization telemetry:
```bash
python optitac_cli.py --file benchmarks/01_arithmetic_cse.tac
python optitac_cli.py --file benchmarks/03_while_loop.tac --dot loop_cfg.dot
python optitac_cli.py --benchmark 4
```

### Run Phase 1 Reference Prototype
```bash
python prototype.py
```
