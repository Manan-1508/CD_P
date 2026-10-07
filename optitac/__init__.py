"""
OptiTAC: Intermediate Code (Three-Address Code) Optimization & Analysis Engine
A modular framework for CFG analysis, fixed-point data-flow solvers, and multi-pass optimizations.
"""

from optitac.ir import Quadruple
from optitac.parser import TACParser
from optitac.cfg import BasicBlock, ControlFlowGraph
from optitac.dataflow import AvailableExpressionsAnalysis, LivenessAnalysis
from optitac.optimizer import Optimizer, OptimizationStats
from optitac.telemetry import TelemetryReport

__version__ = "2.0.0"
__all__ = [
    "Quadruple",
    "TACParser",
    "BasicBlock",
    "ControlFlowGraph",
    "AvailableExpressionsAnalysis",
    "LivenessAnalysis",
    "Optimizer",
    "OptimizationStats",
    "TelemetryReport",
]
