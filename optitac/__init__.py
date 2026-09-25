"""
OptiTAC: Intermediate Code (Three-Address Code) Optimization & Visualizer Engine
Course: BCSE307P - Compiler Design Laboratory
Author: Manan Sangwan (Reg No: 24BCE2277)
"""

from optitac.ir import Quadruple
from optitac.parser import TACParser
from optitac.cfg import BasicBlock, ControlFlowGraph
from optitac.dataflow import AvailableExpressionsAnalysis, LivenessAnalysis
from optitac.optimizer import Optimizer, OptimizationStats
from optitac.telemetry import TelemetryReport

__version__ = "2.0.0"
__author__ = "Manan Sangwan"
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
