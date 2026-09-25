"""
OptiTAC: Interactive Command-Line Interface & Demonstration Tool
Allows running optimizations on benchmark files, custom user files, or direct TAC input.
Usage:
    python optitac_cli.py --file benchmarks/01_arithmetic_cse.tac --cfg --dataflow --stats
    python optitac_cli.py (Interactive Menu Mode)
"""

import sys
import os
import argparse
from typing import List

from optitac.ir import Quadruple
from optitac.parser import TACParser
from optitac.cfg import ControlFlowGraph
from optitac.dataflow import AvailableExpressionsAnalysis, LivenessAnalysis
from optitac.optimizer import Optimizer, OptimizationStats
from optitac.telemetry import TelemetryReport


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def display_header():
    print("=" * 80)
    print("  OptiTAC: Intermediate Code (TAC) Optimization & Analysis Engine")
    print("  BCSE307P - Compiler Design Laboratory  |  Review 2: Core Implementation")
    print("  Author: Manan Sangwan   |   Registration No: 24BCE2277")
    print("=" * 80)


def print_code_comparison(orig_quads: List[Quadruple], opt_quads: List[Quadruple]):
    print("\n" + "=" * 80)
    print(f" {'ORIGINAL THREE-ADDRESS CODE':<38} | {'OPTIMIZED THREE-ADDRESS CODE':<38}")
    print("=" * 80)

    max_len = max(len(orig_quads), len(opt_quads))
    for i in range(max_len):
        left = orig_quads[i].to_tac() if i < len(orig_quads) else ""
        right = opt_quads[i].to_tac() if i < len(opt_quads) else ""
        marker = "  " if left == right else " *"
        print(f" {left:<38} | {right:<38}{marker}")
    print("=" * 80)
    print(" (* indicates statement optimized, replaced, or eliminated)")


def process_tac_program(tac_content: str, show_cfg: bool = True, show_dataflow: bool = True, dot_output: str = None):
    orig_quads = TACParser.parse_program(tac_content)
    if not orig_quads:
        print("[!] Error: No valid Three-Address Code instructions parsed.")
        return

    # 1. CFG Construction
    cfg = ControlFlowGraph.from_quadruples(orig_quads)
    orig_block_count = len(cfg.blocks)

    if show_cfg:
        print("\n" + cfg.render_ascii())

        # Show Dominators & Natural Loops
        dom = cfg.compute_dominators()
        loops = cfg.find_natural_loops()
        print("\n+-- GRAPH TOPOLOGY & LOOP ANALYSIS ----------------------------------------+")
        for b_name, d_set in dom.items():
            print(f"| Dominators of {b_name:<4} : {', '.join(sorted(list(d_set))):<45}|")
        if loops:
            print("+-- DETECTED NATURAL LOOPS ------------------------------------------------+")
            for src, header, body in loops:
                print(f"| Back-edge {src} -> {header} forms loop with blocks: {', '.join(body):<31}|")
        print("+--------------------------------------------------------------------------+")

    if show_dataflow:
        # Initial Data Flow Reports
        avail = AvailableExpressionsAnalysis(cfg)
        print("\n" + avail.format_report())
        liveness = LivenessAnalysis(cfg)
        print("\n" + liveness.format_report())

    # 2. Multi-Pass Optimization
    stats = Optimizer.optimize_cfg(cfg)
    opt_quads = cfg.to_quadruples()
    opt_block_count = len(cfg.blocks)

    # 3. Before vs After Comparison
    print_code_comparison(orig_quads, opt_quads)

    # 4. Telemetry Report
    print("\n" + TelemetryReport.generate_summary(orig_quads, opt_quads, stats, orig_block_count, opt_block_count))

    # 5. Export DOT if requested
    if dot_output:
        dot_code = cfg.export_dot()
        with open(dot_output, "w", encoding="utf-8") as f:
            f.write(dot_code)
        print(f"\n[+] CFG Graphviz DOT exported to: {dot_output}")


def interactive_menu():
    display_header()
    benchmarks_dir = os.path.join(os.path.dirname(__file__), "benchmarks")

    while True:
        print("\n[ SELECT EXECUTION MODE ]")
        print(" 1. Benchmark 1: Arithmetic & Algebraic Identities (01_arithmetic_cse.tac)")
        print(" 2. Benchmark 2: Branching & Dead Code Elimination (02_branching_dce.tac)")
        print(" 3. Benchmark 3: While Loop & Back-edge CFG (03_while_loop.tac)")
        print(" 4. Benchmark 4: Global CSE across Basic Blocks (04_global_cse.tac)")
        print(" 5. Benchmark 5: Array Addressing & Offset Calculations (05_array_address.tac)")
        print(" 6. Enter Custom TAC Code Interactively")
        print(" 7. Specify Path to Custom .tac File")
        print(" 0. Exit")

        choice = input("\nEnter choice [0-7]: ").strip()
        if choice == "0":
            print("\nExiting OptiTAC Engine. Goodbye!")
            break

        tac_code = ""
        bench_map = {
            "1": "01_arithmetic_cse.tac",
            "2": "02_branching_dce.tac",
            "3": "03_while_loop.tac",
            "4": "04_global_cse.tac",
            "5": "05_array_address.tac",
        }

        if choice in bench_map:
            file_path = os.path.join(benchmarks_dir, bench_map[choice])
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    tac_code = f.read()
            else:
                print(f"[!] Benchmark file not found at: {file_path}")
                continue
        elif choice == "6":
            print("\nEnter TAC code line by line (Type 'END' on a new line to submit):")
            lines = []
            while True:
                line = input()
                if line.strip().upper() == "END":
                    break
                lines.append(line)
            tac_code = "\n".join(lines)
        elif choice == "7":
            custom_path = input("Enter path to .tac file: ").strip().strip('"').strip("'")
            if os.path.exists(custom_path):
                with open(custom_path, "r", encoding="utf-8") as f:
                    tac_code = f.read()
            else:
                print(f"[!] File not found: {custom_path}")
                continue
        else:
            print("[!] Invalid choice. Please choose 0-7.")
            continue

        process_tac_program(tac_code, show_cfg=True, show_dataflow=True)


def main():
    parser = argparse.ArgumentParser(
        description="OptiTAC: Intermediate Code (TAC) Optimization & Analysis Engine (Review 2)"
    )
    parser.add_argument("--file", "-f", help="Path to input .tac file")
    parser.add_argument("--no-cfg", action="store_true", help="Disable CFG visualization")
    parser.add_argument("--no-dataflow", action="store_true", help="Disable Data-Flow analysis tables")
    parser.add_argument("--dot", help="Path to export Graphviz .dot file")
    parser.add_argument("--benchmark", "-b", choices=["1", "2", "3", "4", "5"], help="Run benchmark number directly")

    args = parser.parse_args()

    if not args.file and not args.benchmark:
        interactive_menu()
        return

    display_header()
    tac_content = ""

    if args.file:
        if not os.path.exists(args.file):
            print(f"[!] Error: File not found: {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            tac_content = f.read()
    elif args.benchmark:
        bench_map = {
            "1": "01_arithmetic_cse.tac",
            "2": "02_branching_dce.tac",
            "3": "03_while_loop.tac",
            "4": "04_global_cse.tac",
            "5": "05_array_address.tac",
        }
        b_file = os.path.join(os.path.dirname(__file__), "benchmarks", bench_map[args.benchmark])
        with open(b_file, "r", encoding="utf-8") as f:
            tac_content = f.read()

    process_tac_program(
        tac_content,
        show_cfg=not args.no_cfg,
        show_dataflow=not args.no_dataflow,
        dot_output=args.dot,
    )


if __name__ == "__main__":
    main()
