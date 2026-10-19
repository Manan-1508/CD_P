"""
OptiTAC: Intermediate Code (Three-Address Code) Optimization & Backend Engine
A modular framework for CFG analysis, fixed-point data-flow solvers, multi-pass optimizations,
Chaitin-Briggs register allocation, RISC-V code generation, and emulation.
"""

from optitac.ir import Quadruple
from optitac.parser import TACParser, Diagnostic, ParseDiagnosticError
from optitac.cfg import BasicBlock, ControlFlowGraph
from optitac.dataflow import AvailableExpressionsAnalysis, LivenessAnalysis
from optitac.optimizer import Optimizer, OptimizationStats
from optitac.telemetry import TelemetryReport
from optitac.regalloc import RegisterAllocator, AllocationResult
from optitac.codegen import RISCVCodeGenerator
from optitac.peephole import AssemblyPeepholeOptimizer, PeepholeStats
from optitac.emulator import RISCVEmulator, ExecutionResult

__version__ = "3.0.0"
__all__ = [
    "Quadruple",
    "TACParser",
    "Diagnostic",
    "ParseDiagnosticError",
    "BasicBlock",
    "ControlFlowGraph",
    "AvailableExpressionsAnalysis",
    "LivenessAnalysis",
    "Optimizer",
    "OptimizationStats",
    "TelemetryReport",
    "RegisterAllocator",
    "AllocationResult",
    "RISCVCodeGenerator",
    "AssemblyPeepholeOptimizer",
    "PeepholeStats",
    "RISCVEmulator",
    "ExecutionResult",
]
