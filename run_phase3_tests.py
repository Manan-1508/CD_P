"""
OptiTAC: Phase 3 Comprehensive Test Runner & Validation Matrix
Executes and validates all Phase 3 requirements:
1. Valid & Complex Inputs (Factorial, Fibonacci, Nested Loops)
2. Boundary Cases (Single instruction, Zero-trip loop, High register spill stress)
3. Invalid Inputs & Error Conditions (Malformed syntax, Undefined labels, Division by zero, Duplicate labels)
"""

import sys
import os
import time

from optitac.parser import TACParser
from optitac.cfg import ControlFlowGraph
from optitac.optimizer import Optimizer
from optitac.regalloc import RegisterAllocator
from optitac.codegen import RISCVCodeGenerator
from optitac.peephole import AssemblyPeepholeOptimizer
from optitac.emulator import RISCVEmulator

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_phase3_suite():
    tests_dir = os.path.join(os.path.dirname(__file__), "tests_phase3")

    # Test Specifications: (Filename, Category, Expected Type, Expected Val / Error Substr, K_regs)
    suite = [
        # 1. Valid Complex Tests
        ("01_complex_factorial.tac", "Valid Complex", "EXEC", 720, 4),
        ("02_complex_fibonacci.tac", "Valid Complex", "EXEC", 21, 4),
        ("03_complex_nested_loops.tac", "Valid Complex", "EXEC", 20, 4),
        # 2. Boundary Cases
        ("04_boundary_single_inst.tac", "Boundary Case", "EXEC", 42, 4),
        ("05_boundary_zero_trip_loop.tac", "Boundary Case", "EXEC", 99, 4),
        ("06_boundary_high_spill.tac", "Boundary Case", "EXEC", 36, 3),  # K=3 forces spills
        # 3. Invalid Inputs & Error Conditions
        ("07_err_syntax_malformed.tac", "Error Condition", "ERROR", "Invalid Three-Address Code", 4),
        ("08_err_undefined_label.tac", "Error Condition", "ERROR", "undefined in the program", 4),
        ("09_err_division_by_zero.tac", "Error Condition", "ERROR", "division or modulo by zero", 4),
        ("10_err_duplicate_label.tac", "Error Condition", "ERROR", "Duplicate label", 4),
    ]

    print("=" * 100)
    print("  OptiTAC: PHASE 3 COMPREHENSIVE VALIDATION & TEST MATRIX")
    print("  Valid Complex Programs | Boundary Conditions | Error Diagnostics | RISC-V Emulation")
    print("=" * 100)
    print(f"{'Test Case File':<32} | {'Category':<16} | {'Status':<6} | {'Output / Diagnostic Result':<35}")
    print("-" * 100)

    total_passed = 0
    total_tests = len(suite)

    for filename, category, exp_type, exp_val, k in suite:
        filepath = os.path.join(tests_dir, filename)
        if not os.path.exists(filepath):
            print(f"{filename:<32} | {category:<16} | FAIL   | [!] File missing")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()

        if exp_type == "ERROR":
            # Test error diagnostics
            quads, diags = TACParser.parse_with_diagnostics(code)
            errors = [d for d in diags if d.severity == "ERROR"]
            matched = any(exp_val.lower() in d.message.lower() for d in errors)
            if matched:
                status = "PASS"
                total_passed += 1
                detail = f"Caught: {errors[0].message[:30]}..."
            else:
                status = "FAIL"
                detail = "Expected error was not caught"
            print(f"{filename:<32} | {category:<16} | {status:<6} | {detail:<35}")

        elif exp_type == "EXEC":
            # Test full end-to-end pipeline: Parse -> Optimize -> RegAlloc -> Codegen -> Emulate
            try:
                quads, diags = TACParser.parse_with_diagnostics(code)
                errors = [d for d in diags if d.severity == "ERROR"]
                if errors:
                    print(f"{filename:<32} | {category:<16} | FAIL   | Unexpected parser error")
                    continue

                cfg = ControlFlowGraph.from_quadruples(quads)
                stats = Optimizer.optimize_cfg(cfg)
                opt_quads = cfg.to_quadruples()

                alloc = RegisterAllocator(cfg, k=k).allocate()
                codegen = RISCVCodeGenerator(alloc)
                raw_asm = codegen.generate(opt_quads)
                opt_asm, peep_stats = AssemblyPeepholeOptimizer.optimize(raw_asm)

                emu = RISCVEmulator(opt_asm)
                res = emu.run()

                if res.success and res.return_code == exp_val:
                    status = "PASS"
                    total_passed += 1
                    spill_str = f" [Spills: {alloc.total_spills}]" if alloc.total_spills > 0 else ""
                    detail = f"Return Code = {res.return_code} (in {res.cycles_executed} cyc){spill_str}"
                else:
                    status = "FAIL"
                    detail = f"Got {res.return_code}, Expected {exp_val} ({res.error_message})"
                print(f"{filename:<32} | {category:<16} | {status:<6} | {detail:<35}")

            except Exception as e:
                print(f"{filename:<32} | {category:<16} | FAIL   | Exception: {str(e)[:30]}")

    print("=" * 100)
    print(f"  FINAL PHASE 3 VALIDATION SUMMARY: {total_passed}/{total_tests} Tests Passed ({(total_passed/total_tests)*100:.1f}% Success Rate)")
    print("=" * 100)


if __name__ == "__main__":
    run_phase3_suite()
