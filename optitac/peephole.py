"""
OptiTAC: Target Assembly Peephole Optimizer
Performs local multi-instruction sliding-window optimizations on RISC-V assembly:
1. Redundant Move Elimination (e.g. mv t0, t0)
2. Redundant Spill Load Elimination (e.g. sw s0, X(sp) followed by lw s0, X(sp))
3. Fall-through Jump Elimination (e.g. j L1 followed immediately by L1:)
4. Identity Arithmetic Reductions (e.g. addi t0, t0, 0)
"""

import re
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class PeepholeStats:
    moves_eliminated: int = 0
    spill_loads_eliminated: int = 0
    jumps_eliminated: int = 0
    identities_eliminated: int = 0

    @property
    def total_eliminated(self) -> int:
        return (
            self.moves_eliminated
            + self.spill_loads_eliminated
            + self.jumps_eliminated
            + self.identities_eliminated
        )


class AssemblyPeepholeOptimizer:
    """Sliding-window peephole optimizer for RISC-V assembly text."""

    SW_RE = re.compile(r"^\s*sw\s+([a-z0-9]+)\s*,\s*(-?\d+\(sp\))\s*(?:#.*)?$")
    LW_RE = re.compile(r"^\s*lw\s+([a-z0-9]+)\s*,\s*(-?\d+\(sp\))\s*(?:#.*)?$")
    MV_RE = re.compile(r"^\s*mv\s+([a-z0-9]+)\s*,\s*([a-z0-9]+)\s*(?:#.*)?$")
    JUMP_RE = re.compile(r"^\s*j\s+([a-zA-Z0-9_\.]+)\s*(?:#.*)?$")
    LABEL_RE = re.compile(r"^\s*([a-zA-Z0-9_\.]+):\s*$")
    ADDI_ZERO_RE = re.compile(r"^\s*addi\s+([a-z0-9]+)\s*,\s*([a-z0-9]+)\s*,\s*0\s*(?:#.*)?$")

    @classmethod
    def optimize(cls, asm_text: str) -> Tuple[str, PeepholeStats]:
        stats = PeepholeStats()
        lines = asm_text.splitlines()

        # Run multi-pass peephole until fixed point
        changed = True
        while changed:
            changed = False
            new_lines: List[str] = []
            i = 0
            n = len(lines)

            while i < n:
                curr = lines[i].strip()

                # Rule 1: Redundant Move (mv rd, rd)
                m = cls.MV_RE.match(curr)
                if m and m.group(1) == m.group(2):
                    stats.moves_eliminated += 1
                    changed = True
                    i += 1
                    continue

                # Rule 2: Identity Addi (addi rd, rd, 0)
                m = cls.ADDI_ZERO_RE.match(curr)
                if m and m.group(1) == m.group(2):
                    stats.identities_eliminated += 1
                    changed = True
                    i += 1
                    continue

                # Rule 3: Redundant Spill Load after Store (sw reg, off(sp) followed by lw reg, off(sp))
                if i + 1 < n:
                    next_line = lines[i + 1].strip()
                    m_sw = cls.SW_RE.match(curr)
                    m_lw = cls.LW_RE.match(next_line)
                    if m_sw and m_lw:
                        reg_sw, off_sw = m_sw.groups()
                        reg_lw, off_lw = m_lw.groups()
                        if reg_sw == reg_lw and off_sw == off_lw:
                            # Keep the sw, skip the redundant lw
                            new_lines.append(lines[i])
                            stats.spill_loads_eliminated += 1
                            changed = True
                            i += 2
                            continue

                # Rule 4: Fall-through Jump (j L1 followed immediately by L1:)
                if i + 1 < n:
                    next_line = lines[i + 1].strip()
                    m_jump = cls.JUMP_RE.match(curr)
                    m_label = cls.LABEL_RE.match(next_line)
                    if m_jump and m_label:
                        target = m_jump.group(1)
                        label = m_label.group(1)
                        if target == label:
                            # Skip the jump, keep the label
                            stats.jumps_eliminated += 1
                            changed = True
                            i += 1
                            continue

                new_lines.append(lines[i])
                i += 1

            lines = new_lines

        return "\n".join(lines), stats
