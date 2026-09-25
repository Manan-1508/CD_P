"""
OptiTAC: Control Flow Graph (CFG) Construction & Graph Analytics Engine
Implements Dragon Book Leader Identification (§8.4), Predecessor/Successor edge building,
Dominance Tree calculation, Natural Loop detection, and ASCII/Graphviz DOT renderers.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from optitac.ir import Quadruple


@dataclass
class BasicBlock:
    block_id: int
    name: str
    instructions: List[Quadruple] = field(default_factory=list)
    predecessors: List['BasicBlock'] = field(default_factory=list)
    successors: List['BasicBlock'] = field(default_factory=list)
    is_entry: bool = False
    is_exit: bool = False

    def last_instruction(self) -> Optional[Quadruple]:
        return self.instructions[-1] if self.instructions else None

    def get_labels(self) -> List[str]:
        return [q.arg1 for q in self.instructions if q.op == "LABEL" and q.arg1]

    def __repr__(self) -> str:
        return f"<Block {self.name} ({len(self.instructions)} insts)>"

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BasicBlock):
            return False
        return self.name == other.name


class ControlFlowGraph:
    """Manages directed control flow between basic blocks."""

    def __init__(self, blocks: List[BasicBlock]):
        self.blocks: List[BasicBlock] = blocks
        self.entry_block: Optional[BasicBlock] = blocks[0] if blocks else None
        self.exit_blocks: List[BasicBlock] = [b for b in blocks if b.is_exit]
        self.label_to_block: Dict[str, BasicBlock] = {}
        self._build_label_map()

    def _build_label_map(self):
        self.label_to_block.clear()
        for b in self.blocks:
            for lbl in b.get_labels():
                self.label_to_block[lbl] = b

    @classmethod
    def from_quadruples(cls, quads: List[Quadruple]) -> 'ControlFlowGraph':
        """
        Builds CFG using Dragon Book 3-Rule Leader Identification Algorithm:
        Rule 1: The first statement of the program is a leader.
        Rule 2: Any statement that is the target of a conditional or unconditional goto is a leader.
        Rule 3: Any statement that immediately follows a conditional or unconditional goto is a leader.
        """
        if not quads:
            return cls([])

        # Step A: Identify target labels and index mapping
        label_to_idx: Dict[str, int] = {}
        for idx, q in enumerate(quads):
            if q.op == "LABEL" and q.arg1:
                label_to_idx[q.arg1] = idx

        # Step B: Identify Leaders
        leaders: Set[int] = {0}  # Rule 1

        for idx, q in enumerate(quads):
            if q.is_conditional_branch():
                target = q.res
                if target in label_to_idx:
                    leaders.add(label_to_idx[target])  # Rule 2
                if idx + 1 < len(quads):
                    leaders.add(idx + 1)  # Rule 3
            elif q.is_unconditional_jump():
                target = q.arg1
                if target and target in label_to_idx:
                    leaders.add(label_to_idx[target])  # Rule 2
                if idx + 1 < len(quads):
                    leaders.add(idx + 1)  # Rule 3
            elif q.is_label():
                leaders.add(idx)

        sorted_leaders = sorted(list(leaders))

        # Step C: Form Basic Blocks from consecutive leader boundaries
        blocks: List[BasicBlock] = []
        for i, lead_idx in enumerate(sorted_leaders):
            end_idx = sorted_leaders[i + 1] if (i + 1 < len(sorted_leaders)) else len(quads)
            blk_quads = quads[lead_idx:end_idx]
            if blk_quads:
                block = BasicBlock(
                    block_id=i + 1,
                    name=f"B{i + 1}",
                    instructions=blk_quads
                )
                blocks.append(block)

        if blocks:
            blocks[0].is_entry = True

        cfg = cls(blocks)
        cfg.rebuild_edges()
        return cfg

    def rebuild_edges(self):
        """Constructs directed predecessor and successor edges between basic blocks."""
        self._build_label_map()
        for b in self.blocks:
            b.predecessors.clear()
            b.successors.clear()

        for i, block in enumerate(self.blocks):
            last_inst = block.last_instruction()
            if not last_inst:
                if i + 1 < len(self.blocks):
                    self._add_edge(block, self.blocks[i + 1])
                continue

            if last_inst.is_unconditional_jump():
                target_lbl = last_inst.arg1
                if target_lbl and target_lbl in self.label_to_block:
                    self._add_edge(block, self.label_to_block[target_lbl])
            elif last_inst.is_conditional_branch():
                target_lbl = last_inst.res
                # Taken branch edge
                if target_lbl in self.label_to_block:
                    self._add_edge(block, self.label_to_block[target_lbl])
                # Fallthrough edge
                if i + 1 < len(self.blocks):
                    self._add_edge(block, self.blocks[i + 1])
            elif last_inst.is_return():
                block.is_exit = True
            else:
                # Normal sequential fallthrough
                if i + 1 < len(self.blocks):
                    self._add_edge(block, self.blocks[i + 1])

        # Identify exit blocks
        self.exit_blocks = [b for b in self.blocks if not b.successors or b.is_exit]

    def _add_edge(self, src: BasicBlock, dst: BasicBlock):
        if dst not in src.successors:
            src.successors.append(dst)
        if src not in dst.predecessors:
            dst.predecessors.append(src)

    def compute_dominators(self) -> Dict[str, Set[str]]:
        """
        Computes dominance relations:
        D(Entry) = {Entry}
        D(n) = {n} U ( INTERSECT_{p in Pred(n)} D(p) )
        """
        all_block_names = {b.name for b in self.blocks}
        dom: Dict[str, Set[str]] = {}

        if not self.blocks:
            return dom

        entry_name = self.blocks[0].name
        dom[entry_name] = {entry_name}

        for b in self.blocks[1:]:
            dom[b.name] = set(all_block_names)

        changed = True
        while changed:
            changed = False
            for b in self.blocks[1:]:
                if not b.predecessors:
                    new_dom = {b.name}
                else:
                    pred_doms = [dom[p.name] for p in b.predecessors]
                    intersected = set.intersection(*pred_doms) if pred_doms else set()
                    new_dom = {b.name} | intersected

                if new_dom != dom[b.name]:
                    dom[b.name] = new_dom
                    changed = True

        return dom

    def find_natural_loops(self) -> List[tuple]:
        """
        Detects natural loops using back-edges.
        An edge n -> d is a back-edge if d dominates n.
        Returns list of (back_edge_src, loop_header_dst, loop_nodes).
        """
        dom = self.compute_dominators()
        loops = []

        for b in self.blocks:
            for succ in b.successors:
                # Check if succ dominates b (Back-edge: b -> succ)
                if succ.name in dom.get(b.name, set()):
                    header = succ
                    # Construct natural loop body
                    loop_body: Set[str] = {header.name, b.name}
                    stack = [b]
                    while stack:
                        curr = stack.pop()
                        for pred in curr.predecessors:
                            if pred.name not in loop_body:
                                loop_body.add(pred.name)
                                stack.append(pred)
                    loops.append((b.name, header.name, sorted(list(loop_body))))

        return loops

    def remove_unreachable_blocks(self) -> int:
        """Prunes basic blocks not reachable from entry block."""
        if not self.blocks:
            return 0

        visited: Set[str] = set()
        stack = [self.blocks[0]]
        while stack:
            curr = stack.pop()
            if curr.name not in visited:
                visited.add(curr.name)
                for s in curr.successors:
                    stack.append(s)

        unreachable = [b for b in self.blocks if b.name not in visited]
        if unreachable:
            self.blocks = [b for b in self.blocks if b.name in visited]
            self.rebuild_edges()
        return len(unreachable)

    def to_quadruples(self) -> List[Quadruple]:
        """Flattens all basic block instructions back into a linear Quadruple sequence."""
        quads = []
        for b in self.blocks:
            quads.extend(b.instructions)
        return quads

    def render_ascii(self) -> str:
        """Generates an ASCII visualization of the Control Flow Graph."""
        lines = []
        lines.append("+==========================================================================+")
        lines.append("|                       CONTROL FLOW GRAPH (CFG)                           |")
        lines.append("+==========================================================================+")

        for b in self.blocks:
            tag = " [ENTRY]" if b.is_entry else (" [EXIT]" if b.is_exit else "")
            preds = ", ".join([p.name for p in b.predecessors]) or "None"
            succs = ", ".join([s.name for s in b.successors]) or "None (EXIT)"

            lines.append(f"\n+-- Basic Block: {b.name}{tag} " + "-" * (54 - len(b.name) - len(tag)) + "+")
            lines.append(f"| Predecessors : {preds:<58}|")
            lines.append(f"| Successors   : {succs:<58}|")
            lines.append("+--------------------------------------------------------------------------+")
            for q in b.instructions:
                lines.append(f"|   {q.to_tac():<71}|")
            lines.append("+--------------------------------------------------------------------------+")
            if b.successors:
                edge_arrows = "  |\n  +--> Branches to: " + ", ".join([s.name for s in b.successors])
                lines.append(edge_arrows)

        return "\n".join(lines)

    def export_dot(self) -> str:
        """Exports the CFG in Graphviz DOT format."""
        dot = ["digraph CFG {", '  node [shape=box, style="filled,rounded", fontname="Courier"];']
        for b in self.blocks:
            color = "#D4EDDA" if b.is_entry else ("#F8D7DA" if b.is_exit else "#E2E3E5")
            label_lines = [f"{b.name}:"]
            for q in b.instructions:
                clean_tac = q.to_tac().replace('"', '\\"')
                label_lines.append(f"  {clean_tac}")
            node_label = "\\l".join(label_lines) + "\\l"
            dot.append(f'  {b.name} [label="{node_label}", fillcolor="{color}"];')

        for b in self.blocks:
            for s in b.successors:
                dot.append(f"  {b.name} -> {s.name};")

        dot.append("}")
        return "\n".join(dot)
