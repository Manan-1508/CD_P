"""
OptiTAC: Register Allocation Engine via Graph Coloring
Implements Chaitin-Briggs heuristic graph coloring over variable interference graphs.
Uses Variable Liveness analysis (IN and OUT sets) to compute live ranges.
"""

from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass, field
from optitac.cfg import ControlFlowGraph
from optitac.dataflow import LivenessAnalysis
from optitac.ir import Quadruple


@dataclass
class AllocationResult:
    """Stores the outcome of register allocation."""
    reg_map: Dict[str, str] = field(default_factory=dict)
    spilled_vars: Set[str] = field(default_factory=set)
    stack_offsets: Dict[str, int] = field(default_factory=dict)
    interference_graph: Dict[str, Set[str]] = field(default_factory=dict)
    k: int = 4
    colors_used: int = 0
    total_spills: int = 0
    frame_size: int = 16

    def format_report(self) -> str:
        """Returns a formatted human-readable report of the allocation."""
        lines = []
        lines.append("=" * 80)
        lines.append("  REGISTER ALLOCATION: CHAITIN-BRIGGS GRAPH COLORING")
        lines.append(f"  Target Physical Registers (K = {self.k}) | Total Variables: {len(self.interference_graph)}")
        lines.append("=" * 80)
        lines.append(f"{'Variable':<12} | {'Degree':<8} | {'Assigned Location':<22} | {'Interferes With'}")
        lines.append("-" * 80)

        for var in sorted(self.interference_graph.keys()):
            degree = len(self.interference_graph[var])
            loc = self.reg_map.get(var, "UNALLOCATED")
            if var in self.spilled_vars:
                loc_str = f"SPILL [offset: {self.stack_offsets.get(var, 0)}(sp)]"
            else:
                loc_str = f"REG [{loc}]"
            neighbors = "{" + ", ".join(sorted(self.interference_graph[var])) + "}"
            lines.append(f"{var:<12} | {degree:<8} | {loc_str:<22} | {neighbors}")

        lines.append("=" * 80)
        lines.append(f"  SUMMARY: {len(self.reg_map) - len(self.spilled_vars)} in registers | "
                     f"{len(self.spilled_vars)} spilled to stack | "
                     f"Frame Size: {self.frame_size} bytes")
        lines.append("=" * 80)
        return "\n".join(lines)


class RegisterAllocator:
    """
    Chaitin-Briggs Register Allocator using Graph Coloring.
    - Constructs Interference Graph from instruction-level variable liveness.
    - Applies Simplify, Spill, and Select phases.
    - Assigns physical registers (e.g. t0..tK-1) or stack offsets for spilled variables.
    """

    DEFAULT_REGISTERS = ["t0", "t1", "t2", "t3", "t4", "t5", "t6"]

    def __init__(self, cfg: ControlFlowGraph, liveness: Optional[LivenessAnalysis] = None, k: int = 4):
        self.cfg = cfg
        self.liveness = liveness or LivenessAnalysis(cfg)
        self.k = max(2, min(k, len(self.DEFAULT_REGISTERS)))
        self.available_registers = self.DEFAULT_REGISTERS[:self.k]

    def build_interference_graph(self) -> Dict[str, Set[str]]:
        """
        Builds the variable interference graph.
        Two variables interfere if their live ranges overlap (i.e. both are simultaneously live).
        """
        graph: Dict[str, Set[str]] = {}

        # Collect all variables in the CFG
        for b in self.cfg.blocks:
            for q in b.instructions:
                d = q.defined_var()
                if d and not Quadruple.is_constant(d):
                    graph.setdefault(d, set())
                for u in q.used_vars():
                    if not Quadruple.is_constant(u):
                        graph.setdefault(u, set())

        # For each basic block, trace liveness backwards instruction by instruction
        for b in self.cfg.blocks:
            # Start at the end of the block with OUT[B]
            live: Set[str] = set(self.liveness.out_set.get(b.name, set()))

            # Ensure all variables in OUT are in graph
            for v in live:
                graph.setdefault(v, set())

            for q in reversed(b.instructions):
                d = q.defined_var()
                if d and not Quadruple.is_constant(d):
                    graph.setdefault(d, set())
                    # The defined variable interferes with everything currently live
                    for v in live:
                        if v != d:
                            # Copy statement optimization: x = y does not create interference between x and y
                            if q.op == "=" and q.arg1 == v:
                                continue
                            graph[d].add(v)
                            graph[v].add(d)

                    # Remove def from live set
                    live.discard(d)

                # Add used variables to live set and ensure simultaneously live variables interfere
                for u in q.used_vars():
                    if not Quadruple.is_constant(u):
                        graph.setdefault(u, set())
                        for other in live:
                            if other != u:
                                graph[u].add(other)
                                graph[other].add(u)
                        live.add(u)

        return graph

    def allocate(self) -> AllocationResult:
        """Executes Chaitin-Briggs Graph Coloring register allocation."""
        graph = self.build_interference_graph()
        result = AllocationResult(
            interference_graph={k: set(v) for k, v in graph.items()},
            k=self.k,
        )

        if not graph:
            return result

        # Working copies for graph reduction
        work_graph: Dict[str, Set[str]] = {k: set(v) for k, v in graph.items()}
        simplify_stack: List[str] = []
        spill_candidates: Set[str] = set()

        # Phase 1: Simplify & Optimistic Spill Loop
        while work_graph:
            # Find a node with degree < K
            low_degree_node = None
            for node, neighbors in work_graph.items():
                if len(neighbors) < self.k:
                    low_degree_node = node
                    break

            if low_degree_node is not None:
                # Simplify: push to stack and remove from work_graph
                simplify_stack.append(low_degree_node)
                neighbors = work_graph.pop(low_degree_node)
                for n in neighbors:
                    if n in work_graph:
                        work_graph[n].discard(low_degree_node)
            else:
                # Spill phase: pick node with highest degree as spill candidate
                spill_node = max(work_graph.keys(), key=lambda n: len(work_graph[n]))
                spill_candidates.add(spill_node)
                simplify_stack.append(spill_node)
                neighbors = work_graph.pop(spill_node)
                for n in neighbors:
                    if n in work_graph:
                        work_graph[n].discard(spill_node)

        # Phase 2: Select / Coloring
        reg_map: Dict[str, str] = {}
        spilled_vars: Set[str] = set()
        stack_offsets: Dict[str, int] = {}
        current_stack_offset = -4

        while simplify_stack:
            node = simplify_stack.pop()
            # Find colors used by already-colored neighbors in original interference graph
            used_colors = {reg_map[neighbor] for neighbor in graph[node] if neighbor in reg_map}

            # Pick the first available physical register
            assigned_color = None
            for reg in self.available_registers:
                if reg not in used_colors:
                    assigned_color = reg
                    break

            if assigned_color is not None:
                reg_map[node] = assigned_color
            else:
                # Actual spill occurred
                spilled_vars.add(node)
                reg_map[node] = f"{current_stack_offset}(sp)"
                stack_offsets[node] = current_stack_offset
                current_stack_offset -= 4

        # Calculate stack frame size aligned to 16 bytes (standard RISC-V ABI)
        raw_frame = abs(current_stack_offset) + 8
        aligned_frame = ((raw_frame + 15) // 16) * 16

        result.reg_map = reg_map
        result.spilled_vars = spilled_vars
        result.stack_offsets = stack_offsets
        result.colors_used = len(set(r for r in reg_map.values() if not r.endswith("(sp)")))
        result.total_spills = len(spilled_vars)
        result.frame_size = aligned_frame

        return result
