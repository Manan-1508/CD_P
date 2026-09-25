"""
OptiTAC: Optimization Telemetry & Performance Analytics
Computes code reduction percentage, instruction density, and estimated execution metrics.
"""

from typing import List, Dict
from optitac.ir import Quadruple
from optitac.optimizer import OptimizationStats


class TelemetryReport:
    """Computes comparative compiler optimization metrics."""

    @staticmethod
    def estimate_cycles(quads: List[Quadruple]) -> int:
        """
        Estimates execution cycles based on instruction complexity:
        - Multiplications / Divisions: 3 cycles
        - Loads / Memory / Array / Calls: 2 cycles
        - Branches / Returns: 2 cycles
        - Simple ALU (Add, Sub, Bitwise, Copy): 1 cycle
        """
        total = 0
        for q in quads:
            if q.op in {"*", "/", "%"}:
                total += 3
            elif q.op in {"call", "[]_read", "[]_write"}:
                total += 2
            elif q.is_branch() or q.is_return():
                total += 2
            elif q.is_label():
                total += 0
            else:
                total += 1
        return total

    @classmethod
    def generate_summary(
        cls,
        orig_quads: List[Quadruple],
        opt_quads: List[Quadruple],
        stats: OptimizationStats,
        orig_block_count: int,
        opt_block_count: int,
    ) -> str:
        orig_len = len(orig_quads)
        opt_len = len(opt_quads)
        reduction_inst = ((orig_len - opt_len) / orig_len * 100) if orig_len > 0 else 0.0

        orig_cycles = cls.estimate_cycles(orig_quads)
        opt_cycles = cls.estimate_cycles(opt_quads)
        reduction_cycles = ((orig_cycles - opt_cycles) / orig_cycles * 100) if orig_cycles > 0 else 0.0

        lines = []
        lines.append("+==========================================================================+")
        lines.append("|                OPTITAC OPTIMIZATION & TELEMETRY REPORT                   |")
        lines.append("+==========================================================================+")
        lines.append(f"  * Source Statements (Original)     : {orig_len:<6}")
        lines.append(f"  * Optimized Statements (Final)     : {opt_len:<6}")
        lines.append(f"  * Total Dead/Redundant Eliminated  : {orig_len - opt_len:<6} ({reduction_inst:.1f}% reduction)")
        lines.append(f"  * Estimated Pipeline Latency       : {orig_cycles} cycles --> {opt_cycles} cycles ({reduction_cycles:.1f}% faster)")
        lines.append("+--------------------------------------------------------------------------+")
        lines.append("  TRANSFORMATION BREAKDOWN:")
        lines.append(f"  * Constant Folding Operations      : {stats.folded}")
        lines.append(f"  * Constant Values Propagated       : {stats.propagated}")
        lines.append(f"  * Algebraic Identity Reductions    : {stats.algebraic}")
        lines.append(f"  * Common Subexpressions Reused     : {stats.cse_removed}")
        lines.append(f"  * Dead Assignments / Temporaries   : {stats.dead_removed}")
        lines.append(f"  * Unreachable Basic Blocks Pruned  : {stats.blocks_pruned}")
        lines.append(f"  * Basic Blocks (Before / After)    : {orig_block_count} --> {opt_block_count}")
        lines.append(f"  * Fixed-Point Pipeline Iterations  : {stats.iterations}")
        lines.append("+==========================================================================+")
        return "\n".join(lines)
