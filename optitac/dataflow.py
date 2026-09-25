"""
OptiTAC: Data-Flow Analysis Framework
Implements standard Dragon Book iterative fixed-point data-flow algorithms:
1. Available Expressions Analysis (Forward, Meet: Intersection) for Global CSE
2. Liveness Analysis (Backward, Meet: Union) for Global Dead Code Elimination
"""

from typing import Dict, Set, Tuple, List, Optional
from optitac.cfg import ControlFlowGraph, BasicBlock
from optitac.ir import Quadruple

Expression = Tuple[str, str, str]


class AvailableExpressionsAnalysis:
    """
    Forward Data-Flow Analysis to determine expressions available at each block boundary.
    - Direction: Forward
    - Domain: Set of all binary expressions (op, arg1, arg2)
    - Meet Operator: Intersection (∩)
    - Transfer Equation: OUT[B] = GEN[B] ∪ (IN[B] - KILL[B])
    - Boundary: OUT[Entry] = ∅; for all B != Entry: OUT[B] = U (Universal set)
    """

    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg
        self.universe: Set[Expression] = set()
        self.gen: Dict[str, Set[Expression]] = {}
        self.kill: Dict[str, Set[Expression]] = {}
        self.in_set: Dict[str, Set[Expression]] = {}
        self.out_set: Dict[str, Set[Expression]] = {}
        self._compute_universe()
        self._compute_gen_kill()
        self._solve_fixed_point()

    def _compute_universe(self):
        """Identifies all unique expressions evaluated across all blocks."""
        self.universe.clear()
        for b in self.cfg.blocks:
            for q in b.instructions:
                key = q.get_expression_key()
                if key and key[1] and key[2]:
                    self.universe.add(key)

    def _compute_gen_kill(self):
        """Computes GEN[B] and KILL[B] sets for each block."""
        for b in self.cfg.blocks:
            gen_b: Set[Expression] = set()
            killed_vars: Set[str] = set()

            for q in b.instructions:
                # If instruction evaluates expression, add to gen if operands not killed
                key = q.get_expression_key()
                if key and key[1] and key[2]:
                    gen_b.add(key)

                # If instruction defines a variable x, kill all expressions containing x
                def_var = q.defined_var()
                if def_var:
                    killed_vars.add(def_var)
                    # Any previously generated expr containing def_var is invalidated
                    gen_b = {e for e in gen_b if e[1] != def_var and e[2] != def_var}

            # KILL[B] = all expressions in universe containing any variable defined in B
            kill_b = {e for e in self.universe if e[1] in killed_vars or e[2] in killed_vars}

            self.gen[b.name] = gen_b
            self.kill[b.name] = kill_b

    def _solve_fixed_point(self):
        """Runs iterative fixed-point algorithm until OUT sets converge."""
        if not self.cfg.blocks:
            return

        entry_name = self.cfg.blocks[0].name
        self.out_set[entry_name] = set()
        self.in_set[entry_name] = set()

        for b in self.cfg.blocks[1:]:
            self.out_set[b.name] = set(self.universe)
            self.in_set[b.name] = set()

        changed = True
        iterations = 0
        while changed:
            changed = False
            iterations += 1
            for b in self.cfg.blocks:
                # IN[B] = INTERSECT_{P in Pred(B)} OUT[P]
                if b.name == entry_name:
                    in_b = set()
                elif not b.predecessors:
                    in_b = set()
                else:
                    pred_outs = [self.out_set[p.name] for p in b.predecessors]
                    in_b = set.intersection(*pred_outs) if pred_outs else set()

                self.in_set[b.name] = in_b

                # OUT[B] = GEN[B] U (IN[B] - KILL[B])
                out_b = self.gen[b.name] | (in_b - self.kill[b.name])
                if out_b != self.out_set[b.name]:
                    self.out_set[b.name] = out_b
                    changed = True

    def format_report(self) -> str:
        """Returns a formatted tabular string of GEN, KILL, IN, OUT sets."""
        lines = []
        lines.append("=" * 80)
        lines.append("  DATA-FLOW ANALYSIS: AVAILABLE EXPRESSIONS (FOR GLOBAL CSE)")
        lines.append("=" * 80)
        fmt_expr = lambda s: "{" + ", ".join([f"{e[1]} {e[0]} {e[2]}" for e in sorted(list(s))]) + "}"
        lines.append(f"{'Block':<6} | {'GEN[B]':<22} | {'KILL[B]':<22} | {'IN[B]':<24}")
        lines.append("-" * 80)
        for b in self.cfg.blocks:
            gen_str = fmt_expr(self.gen[b.name])
            kill_str = fmt_expr(self.kill[b.name])
            in_str = fmt_expr(self.in_set[b.name])
            lines.append(f"{b.name:<6} | {gen_str:<22} | {kill_str:<22} | {in_str:<24}")
        lines.append("=" * 80)
        return "\n".join(lines)


class LivenessAnalysis:
    """
    Backward Data-Flow Analysis to determine variables live at each block boundary.
    - Direction: Backward
    - Domain: Set of variables
    - Meet Operator: Union (∪)
    - Transfer Equation: IN[B] = USE[B] ∪ (OUT[B] - DEF[B])
    - Boundary: OUT[Exit] = ∅; IN[B] = ∅ initially
    """

    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg
        self.use: Dict[str, Set[str]] = {}
        self.def_set: Dict[str, Set[str]] = {}
        self.in_set: Dict[str, Set[str]] = {}
        self.out_set: Dict[str, Set[str]] = {}
        self._compute_use_def()
        self._solve_fixed_point()

    def _compute_use_def(self):
        """Computes USE[B] and DEF[B] sets for each block."""
        for b in self.cfg.blocks:
            use_b: Set[str] = set()
            def_b: Set[str] = set()

            for q in b.instructions:
                # Variables used before definition in this block belong to USE[B]
                for u in q.used_vars():
                    if u not in def_b:
                        use_b.add(u)

                # Variables defined belong to DEF[B]
                d = q.defined_var()
                if d and d not in use_b:
                    def_b.add(d)

            self.use[b.name] = use_b
            self.def_set[b.name] = def_b

    def _solve_fixed_point(self):
        """Runs backward fixed-point iteration until IN sets converge."""
        for b in self.cfg.blocks:
            self.in_set[b.name] = set()
            self.out_set[b.name] = set()

        changed = True
        while changed:
            changed = False
            # Backward traversal
            for b in reversed(self.cfg.blocks):
                # OUT[B] = UNION_{S in Succ(B)} IN[S]
                out_b: Set[str] = set()
                for s in b.successors:
                    out_b |= self.in_set[s.name]

                self.out_set[b.name] = out_b

                # IN[B] = USE[B] U (OUT[B] - DEF[B])
                in_b = self.use[b.name] | (out_b - self.def_set[b.name])
                if in_b != self.in_set[b.name]:
                    self.in_set[b.name] = in_b
                    changed = True

    def format_report(self) -> str:
        """Returns a formatted tabular string of USE, DEF, IN, OUT sets."""
        lines = []
        lines.append("=" * 80)
        lines.append("  DATA-FLOW ANALYSIS: VARIABLE LIVENESS (FOR GLOBAL DEAD CODE ELIMINATION)")
        lines.append("=" * 80)
        fmt_set = lambda s: "{" + ", ".join(sorted(list(s))) + "}"
        lines.append(f"{'Block':<6} | {'USE[B]':<20} | {'DEF[B]':<20} | {'IN[B]':<20} | {'OUT[B]':<20}")
        lines.append("-" * 80)
        for b in self.cfg.blocks:
            lines.append(
                f"{b.name:<6} | {fmt_set(self.use[b.name]):<20} | {fmt_set(self.def_set[b.name]):<20} | {fmt_set(self.in_set[b.name]):<20} | {fmt_set(self.out_set[b.name]):<20}"
            )
        lines.append("=" * 80)
        return "\n".join(lines)
