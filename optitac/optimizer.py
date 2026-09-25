"""
OptiTAC: Multi-Pass Optimization Engine
Implements intra-block and inter-block optimization passes:
1. Constant Folding & Constant Propagation
2. Algebraic Identities & Simplification
3. DAG-based Local Common Subexpression Elimination (CSE)
4. Global Common Subexpression Elimination (via Available Expressions)
5. Global Dead Code Elimination (via Liveness Analysis)
6. Unreachable Basic Block Pruning
"""

from typing import Dict, List, Set, Tuple, Optional
from optitac.ir import Quadruple
from optitac.cfg import BasicBlock, ControlFlowGraph
from optitac.dataflow import AvailableExpressionsAnalysis, LivenessAnalysis


class OptimizationStats:
    def __init__(self):
        self.folded: int = 0
        self.propagated: int = 0
        self.algebraic: int = 0
        self.cse_removed: int = 0
        self.dead_removed: int = 0
        self.blocks_pruned: int = 0
        self.iterations: int = 0

    def merge(self, other: 'OptimizationStats'):
        self.folded += other.folded
        self.propagated += other.propagated
        self.algebraic += other.algebraic
        self.cse_removed += other.cse_removed
        self.dead_removed += other.dead_removed
        self.blocks_pruned += other.blocks_pruned

    def to_dict(self) -> Dict[str, int]:
        return {
            "folded": self.folded,
            "propagated": self.propagated,
            "algebraic": self.algebraic,
            "cse_removed": self.cse_removed,
            "dead_removed": self.dead_removed,
            "blocks_pruned": self.blocks_pruned,
            "iterations": self.iterations,
        }


class Optimizer:
    """Core multi-pass intermediate code optimizer."""

    @staticmethod
    def _is_int(val: Optional[str]) -> bool:
        if val is None:
            return False
        return val.lstrip("-").isdigit()

    @classmethod
    def run_local_pass(cls, block: BasicBlock, stats: OptimizationStats) -> bool:
        """
        Executes intra-block optimizations:
        1. Constant Folding & Propagation
        2. Algebraic Simplification
        3. DAG-based Local Value Numbering / CSE
        """
        original_tac = [q.to_tac() for q in block.instructions]
        quads = list(block.instructions)

        # Step A: Constant Folding, Constant Propagation & Copy Propagation
        constants: Dict[str, str] = {}
        copies: Dict[str, str] = {}
        stage1: List[Quadruple] = []

        for q in quads:
            orig_a1, orig_a2 = q.arg1, q.arg2
            a1 = copies.get(q.arg1, q.arg1) if q.arg1 else q.arg1
            a2 = copies.get(q.arg2, q.arg2) if q.arg2 else q.arg2

            a1 = constants.get(a1, a1) if a1 else a1
            a2 = constants.get(a2, a2) if a2 else a2

            if (a1 != orig_a1) or (a2 != orig_a2):
                stats.propagated += 1

            # Constant Folding check
            folded = False
            if q.op in {"+", "-", "*", "/", "%", "&", "|", "^"} and cls._is_int(a1) and cls._is_int(a2):
                v1, v2 = int(a1), int(a2)
                try:
                    res_val = None
                    if q.op == "+": res_val = v1 + v2
                    elif q.op == "-": res_val = v1 - v2
                    elif q.op == "*": res_val = v1 * v2
                    elif q.op == "/" and v2 != 0: res_val = v1 // v2
                    elif q.op == "%" and v2 != 0: res_val = v1 % v2
                    elif q.op == "&": res_val = v1 & v2
                    elif q.op == "|": res_val = v1 | v2
                    elif q.op == "^": res_val = v1 ^ v2

                    if res_val is not None:
                        constants[q.res] = str(res_val)
                        if q.res in copies:
                            del copies[q.res]
                        copies = {k: v for k, v in copies.items() if v != q.res}
                        new_q = Quadruple(op="=", arg1=str(res_val), arg2=None, res=q.res, raw="", line_no=q.line_no)
                        stage1.append(new_q)
                        stats.folded += 1
                        folded = True
                except ZeroDivisionError:
                    pass

            if not folded:
                # Update constant state and copy propagation map
                if q.op == "=" and a1:
                    if cls._is_int(a1):
                        constants[q.res] = a1
                        if q.res in copies:
                            del copies[q.res]
                    elif a1 != q.res:
                        root = copies.get(a1, a1)
                        copies[q.res] = root
                        if q.res in constants:
                            del constants[q.res]
                else:
                    if q.res in constants:
                        del constants[q.res]
                    if q.res in copies:
                        del copies[q.res]
                    copies = {k: v for k, v in copies.items() if v != q.res}

                stage1.append(Quadruple(op=q.op, arg1=a1, arg2=a2, res=q.res, raw="", line_no=q.line_no))

        # Step B: Algebraic Simplification
        stage2: List[Quadruple] = []
        for q in stage1:
            a1, a2 = q.arg1, q.arg2
            simplified = False

            if q.op == "+":
                if a1 == "0" and a2:
                    stage2.append(Quadruple(op="=", arg1=a2, arg2=None, res=q.res, line_no=q.line_no))
                    stats.algebraic += 1
                    simplified = True
                elif a2 == "0" and a1:
                    stage2.append(Quadruple(op="=", arg1=a1, arg2=None, res=q.res, line_no=q.line_no))
                    stats.algebraic += 1
                    simplified = True
            elif q.op == "-":
                if a2 == "0" and a1:
                    stage2.append(Quadruple(op="=", arg1=a1, arg2=None, res=q.res, line_no=q.line_no))
                    stats.algebraic += 1
                    simplified = True
                elif a1 == a2 and a1:
                    stage2.append(Quadruple(op="=", arg1="0", arg2=None, res=q.res, line_no=q.line_no))
                    stats.algebraic += 1
                    simplified = True
            elif q.op == "*":
                if (a1 == "1" and a2) or (a2 == "1" and a1):
                    non_one = a2 if a1 == "1" else a1
                    stage2.append(Quadruple(op="=", arg1=non_one, arg2=None, res=q.res, line_no=q.line_no))
                    stats.algebraic += 1
                    simplified = True
                elif (a1 == "0" and a2) or (a2 == "0" and a1):
                    stage2.append(Quadruple(op="=", arg1="0", arg2=None, res=q.res, line_no=q.line_no))
                    stats.algebraic += 1
                    simplified = True
            elif q.op == "/":
                if a2 == "1" and a1:
                    stage2.append(Quadruple(op="=", arg1=a1, arg2=None, res=q.res, line_no=q.line_no))
                    stats.algebraic += 1
                    simplified = True

            if not simplified:
                stage2.append(q)

        # Step C: DAG-based Local Value Numbering / CSE
        stage3: List[Quadruple] = []
        seen_expr: Dict[Tuple[str, str, Optional[str]], str] = {}

        for q in stage2:
            if q.is_branch() or q.is_label() or q.is_return() or q.op in {"=", "param", "call", "[]_write"}:
                stage3.append(q)
                continue

            expr_key = q.get_expression_key()
            if expr_key and expr_key in seen_expr:
                prev_temp = seen_expr[expr_key]
                new_q = Quadruple(op="=", arg1=prev_temp, arg2=None, res=q.res, line_no=q.line_no)
                stage3.append(new_q)
                stats.cse_removed += 1
            else:
                if expr_key:
                    seen_expr[expr_key] = q.res
                stage3.append(q)

        block.instructions = stage3
        new_tac = [q.to_tac() for q in block.instructions]
        return new_tac != original_tac

    @classmethod
    def run_global_cse(cls, cfg: ControlFlowGraph, stats: OptimizationStats) -> bool:
        """
        Global Common Subexpression Elimination:
        Replaces redundant computation in block B if expression is in IN[B].
        """
        avail = AvailableExpressionsAnalysis(cfg)
        changed = False

        # Build mapping of expression -> defining temporary across blocks
        global_expr_defs: Dict[Tuple[str, str, str], str] = {}
        for b in cfg.blocks:
            for q in b.instructions:
                key = q.get_expression_key()
                if key and key not in global_expr_defs and q.res:
                    global_expr_defs[key] = q.res

        for b in cfg.blocks:
            avail_in = set(avail.in_set.get(b.name, set()))
            new_insts = []

            for q in b.instructions:
                key = q.get_expression_key()
                if key and key in avail_in and key in global_expr_defs:
                    existing_var = global_expr_defs[key]
                    if existing_var != q.res:
                        new_q = Quadruple(op="=", arg1=existing_var, arg2=None, res=q.res, line_no=q.line_no)
                        new_insts.append(new_q)
                        stats.cse_removed += 1
                        changed = True
                        continue
                elif key:
                    avail_in.add(key)

                # Invalidate if operand is reassigned
                d = q.defined_var()
                if d:
                    avail_in = {e for e in avail_in if e[1] != d and e[2] != d}

                new_insts.append(q)

            b.instructions = new_insts

        return changed

    @classmethod
    def run_global_dce(cls, cfg: ControlFlowGraph, stats: OptimizationStats) -> bool:
        """
        Global Dead Code Elimination:
        Uses backward Liveness Analysis. Removes assignments x = ... if x is not live-out
        and not read in the remainder of block B.
        """
        liveness = LivenessAnalysis(cfg)
        changed = False

        for b in cfg.blocks:
            live = set(liveness.out_set.get(b.name, set()))
            surviving: List[Quadruple] = []

            # Traverse instructions in reverse within block
            for q in reversed(b.instructions):
                def_var = q.defined_var()

                # Check if this assignment is dead
                is_dead = False
                if def_var and q.is_assignment() and q.op not in {"call", "[]_write"}:
                    # Dead if variable is not in live set and target is temporary or local variable
                    if def_var not in live:
                        is_dead = True

                if is_dead:
                    stats.dead_removed += 1
                    changed = True
                else:
                    # Variable defined is no longer live before this instruction
                    if def_var and def_var in live:
                        live.remove(def_var)
                    # Operands used become live
                    for u in q.used_vars():
                        live.add(u)
                    surviving.append(q)

            b.instructions = list(reversed(surviving))

        return changed

    @classmethod
    def optimize_cfg(cls, cfg: ControlFlowGraph, max_iterations: int = 5) -> OptimizationStats:
        """
        Master Fixed-Point Optimization Pipeline.
        Iteratively executes Local Passes, Global CSE, Global DCE, and Unreachable Code Elimination.
        """
        stats = OptimizationStats()

        for iteration in range(1, max_iterations + 1):
            stats.iterations = iteration
            pass_changed = False

            # 1. Intra-Block Local Optimizations
            for b in cfg.blocks:
                if cls.run_local_pass(b, stats):
                    pass_changed = True

            # 2. Global Common Subexpression Elimination
            if cls.run_global_cse(cfg, stats):
                pass_changed = True

            # 3. Global Dead Code Elimination
            if cls.run_global_dce(cfg, stats):
                pass_changed = True

            # 4. Prune Unreachable Basic Blocks
            pruned = cfg.remove_unreachable_blocks()
            if pruned > 0:
                stats.blocks_pruned += pruned
                pass_changed = True

            # Convergence condition: fixed point reached
            if not pass_changed:
                break

        return stats
