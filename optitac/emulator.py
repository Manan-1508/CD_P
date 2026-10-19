"""
OptiTAC: Pure-Python RISC-V (RV32I/M) Functional Emulator & Simulator
Executes generated assembly directly without external cross-compilation toolchains.
Validates program semantics, computes executed instruction cycles, and captures exit codes.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import re


@dataclass
class ExecutionResult:
    return_code: int = 0
    cycles_executed: int = 0
    instructions_executed: int = 0
    final_registers: Dict[str, int] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""

    def format_report(self) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append("  RISC-V BARE-METAL EMULATION & EXECUTION VERIFICATION")
        lines.append("=" * 80)
        if self.success:
            lines.append(f"  Execution Status       : SUCCESS (Completed normally)")
            lines.append(f"  Program Return Code    : {self.return_code} (in register a0)")
            lines.append(f"  Instructions Executed  : {self.instructions_executed}")
            lines.append(f"  Simulated CPU Cycles   : {self.cycles_executed}")
            lines.append("-" * 80)
            lines.append("  REGISTER STATE AT TERMINATION:")
            # Print non-zero registers
            non_zero = [f"{reg}={val}" for reg, val in sorted(self.final_registers.items()) if val != 0 and reg not in {"sp", "ra"}]
            if non_zero:
                lines.append("  " + ", ".join(non_zero[:10]))
            else:
                lines.append("  All general-purpose registers zeroed or restored.")
        else:
            lines.append(f"  Execution Status       : FAILED")
            lines.append(f"  Runtime Error          : {self.error_message}")
        lines.append("=" * 80)
        return "\n".join(lines)


class RISCVEmulator:
    """
    Simulates a 32-bit RISC-V processor executing standard RV32I/M instructions.
    """

    REGISTER_ALIASES = {
        "zero": 0, "x0": 0,
        "ra": 1, "x1": 1,
        "sp": 2, "x2": 2,
        "gp": 3, "x3": 3,
        "tp": 4, "x4": 4,
        "t0": 5, "x5": 5,
        "t1": 6, "x6": 6,
        "t2": 7, "x7": 7,
        "s0": 8, "fp": 8, "x8": 8,
        "s1": 9, "x9": 9,
        "a0": 10, "x10": 10,
        "a1": 11, "x11": 11,
        "a2": 12, "x12": 12,
        "a3": 13, "x13": 13,
        "a4": 14, "x14": 14,
        "a5": 15, "x15": 15,
        "a6": 16, "x16": 16,
        "a7": 17, "x17": 17,
        "s2": 18, "x18": 18,
        "s3": 19, "x19": 19,
        "s4": 20, "x20": 20,
        "s5": 21, "x21": 21,
        "s6": 22, "x22": 22,
        "s7": 23, "x23": 23,
        "s8": 24, "x24": 24,
        "s9": 25, "x25": 25,
        "s10": 26, "x26": 26,
        "s11": 27, "x27": 27,
        "t3": 28, "x28": 28,
        "t4": 29, "x29": 29,
        "t5": 30, "x30": 30,
        "t6": 31, "x31": 31,
    }

    REV_REG_MAP = {v: k for k, v in REGISTER_ALIASES.items() if not k.startswith("x") and k != "fp"}

    def __init__(self, asm_text: str):
        self.asm_text = asm_text
        self.regs = [0] * 32
        self.memory: Dict[int, int] = {}
        # Initial stack pointer at 0x10000
        self.INITIAL_SP = 0x10000
        self.regs[2] = self.INITIAL_SP
        # Return address set to sentinel exit address
        self.SENTINEL_EXIT_PC = 0xFFFF0000
        self.regs[1] = self.SENTINEL_EXIT_PC
        self.labels: Dict[str, int] = {}
        self.instructions: List[Tuple[str, List[str], str]] = []
        self._load_program()

    def _get_reg_idx(self, name: str) -> int:
        clean = name.strip(", ").lower()
        if clean not in self.REGISTER_ALIASES:
            raise ValueError(f"Unknown register: '{name}'")
        return self.REGISTER_ALIASES[clean]

    def _load_program(self):
        """Parses assembly text into instructions and resolves labels."""
        raw_lines = self.asm_text.splitlines()
        inst_idx = 0

        for line in raw_lines:
            clean = line.split("#")[0].strip()
            if not clean:
                continue

            # Check for label (including local labels like .L_epilogue:)
            if clean.endswith(":"):
                lbl = clean[:-1].strip()
                self.labels[lbl] = inst_idx
                continue

            # Skip assembler directives (e.g. .text, .globl, .type)
            if clean.startswith("."):
                continue

            # Parse mnemonic and operands
            parts = clean.split(None, 1)
            mnemonic = parts[0].lower()
            operands = []
            if len(parts) > 1:
                # Split operands by comma
                operands = [op.strip() for op in parts[1].split(",")]

            self.instructions.append((mnemonic, operands, clean))
            inst_idx += 1

    def run(self, max_instructions: int = 50000) -> ExecutionResult:
        """Executes the loaded program until ret / sentinel PC or max_instructions."""
        pc = 0
        total_insts = 0
        total_cycles = 0

        # Find entry point: main if present, else 0
        if "main" in self.labels:
            pc = self.labels["main"]

        while 0 <= pc < len(self.instructions):
            if total_insts >= max_instructions:
                return ExecutionResult(
                    return_code=self.regs[10],
                    cycles_executed=total_cycles,
                    instructions_executed=total_insts,
                    success=False,
                    error_message=f"Execution limit exceeded ({max_instructions} instructions). Possible infinite loop.",
                )

            mnemonic, ops, raw = self.instructions[pc]
            total_insts += 1
            next_pc = pc + 1

            # Cycle weight modeling
            cycle_cost = 1
            if mnemonic in {"mul"}:
                cycle_cost = 3
            elif mnemonic in {"div", "rem"}:
                cycle_cost = 12
            elif mnemonic in {"j", "ret", "beq", "bne", "blt", "bge", "bnez", "beqz"}:
                cycle_cost = 2
            elif mnemonic in {"lw", "sw"}:
                cycle_cost = 2

            total_cycles += cycle_cost

            # Instruction Execution
            try:
                if mnemonic == "li":
                    # li rd, imm
                    rd = self._get_reg_idx(ops[0])
                    imm = int(ops[1])
                    if rd != 0:
                        self.regs[rd] = imm

                elif mnemonic == "mv":
                    # mv rd, rs
                    rd = self._get_reg_idx(ops[0])
                    rs = self._get_reg_idx(ops[1])
                    if rd != 0:
                        self.regs[rd] = self.regs[rs]

                elif mnemonic == "add":
                    rd = self._get_reg_idx(ops[0])
                    r1 = self._get_reg_idx(ops[1])
                    r2 = self._get_reg_idx(ops[2])
                    val = (self.regs[r1] + self.regs[r2]) & 0xFFFFFFFF
                    if rd != 0:
                        self.regs[rd] = val if val < 0x80000000 else val - 0x100000000

                elif mnemonic == "addi":
                    rd = self._get_reg_idx(ops[0])
                    r1 = self._get_reg_idx(ops[1])
                    imm = int(ops[2])
                    val = (self.regs[r1] + imm) & 0xFFFFFFFF
                    if rd != 0:
                        self.regs[rd] = val if val < 0x80000000 else val - 0x100000000

                elif mnemonic == "sub":
                    rd = self._get_reg_idx(ops[0])
                    r1 = self._get_reg_idx(ops[1])
                    r2 = self._get_reg_idx(ops[2])
                    val = (self.regs[r1] - self.regs[r2]) & 0xFFFFFFFF
                    if rd != 0:
                        self.regs[rd] = val if val < 0x80000000 else val - 0x100000000

                elif mnemonic == "neg":
                    rd = self._get_reg_idx(ops[0])
                    rs = self._get_reg_idx(ops[1])
                    val = (-self.regs[rs]) & 0xFFFFFFFF
                    if rd != 0:
                        self.regs[rd] = val if val < 0x80000000 else val - 0x100000000

                elif mnemonic == "mul":
                    rd = self._get_reg_idx(ops[0])
                    r1 = self._get_reg_idx(ops[1])
                    r2 = self._get_reg_idx(ops[2])
                    val = (self.regs[r1] * self.regs[r2]) & 0xFFFFFFFF
                    if rd != 0:
                        self.regs[rd] = val if val < 0x80000000 else val - 0x100000000

                elif mnemonic == "div":
                    rd = self._get_reg_idx(ops[0])
                    r1 = self._get_reg_idx(ops[1])
                    r2 = self._get_reg_idx(ops[2])
                    divisor = self.regs[r2]
                    val = (self.regs[r1] // divisor) if divisor != 0 else 0
                    if rd != 0:
                        self.regs[rd] = val

                elif mnemonic == "rem":
                    rd = self._get_reg_idx(ops[0])
                    r1 = self._get_reg_idx(ops[1])
                    r2 = self._get_reg_idx(ops[2])
                    divisor = self.regs[r2]
                    val = (self.regs[r1] % divisor) if divisor != 0 else 0
                    if rd != 0:
                        self.regs[rd] = val

                elif mnemonic == "and":
                    rd = self._get_reg_idx(ops[0])
                    r1 = self._get_reg_idx(ops[1])
                    r2 = self._get_reg_idx(ops[2])
                    if rd != 0:
                        self.regs[rd] = self.regs[r1] & self.regs[r2]

                elif mnemonic == "or":
                    rd = self._get_reg_idx(ops[0])
                    r1 = self._get_reg_idx(ops[1])
                    r2 = self._get_reg_idx(ops[2])
                    if rd != 0:
                        self.regs[rd] = self.regs[r1] | self.regs[r2]

                elif mnemonic == "xor":
                    rd = self._get_reg_idx(ops[0])
                    r1 = self._get_reg_idx(ops[1])
                    r2 = self._get_reg_idx(ops[2])
                    if rd != 0:
                        self.regs[rd] = self.regs[r1] ^ self.regs[r2]

                elif mnemonic == "seqz":
                    rd = self._get_reg_idx(ops[0])
                    rs = self._get_reg_idx(ops[1])
                    if rd != 0:
                        self.regs[rd] = 1 if self.regs[rs] == 0 else 0

                elif mnemonic == "j":
                    target = ops[0]
                    if target not in self.labels:
                        raise RuntimeError(f"Jump to undefined label '{target}'")
                    next_pc = self.labels[target]

                elif mnemonic == "beq":
                    r1 = self._get_reg_idx(ops[0])
                    r2 = self._get_reg_idx(ops[1])
                    target = ops[2]
                    if self.regs[r1] == self.regs[r2]:
                        next_pc = self.labels[target]

                elif mnemonic == "bne":
                    r1 = self._get_reg_idx(ops[0])
                    r2 = self._get_reg_idx(ops[1])
                    target = ops[2]
                    if self.regs[r1] != self.regs[r2]:
                        next_pc = self.labels[target]

                elif mnemonic == "blt":
                    r1 = self._get_reg_idx(ops[0])
                    r2 = self._get_reg_idx(ops[1])
                    target = ops[2]
                    if self.regs[r1] < self.regs[r2]:
                        next_pc = self.labels[target]

                elif mnemonic == "bge":
                    r1 = self._get_reg_idx(ops[0])
                    r2 = self._get_reg_idx(ops[1])
                    target = ops[2]
                    if self.regs[r1] >= self.regs[r2]:
                        next_pc = self.labels[target]

                elif mnemonic == "bnez":
                    r1 = self._get_reg_idx(ops[0])
                    target = ops[1]
                    if self.regs[r1] != 0:
                        next_pc = self.labels[target]

                elif mnemonic == "beqz":
                    r1 = self._get_reg_idx(ops[0])
                    target = ops[1]
                    if self.regs[r1] == 0:
                        next_pc = self.labels[target]

                elif mnemonic == "lw":
                    # lw rd, offset(sp)
                    rd = self._get_reg_idx(ops[0])
                    m = re.match(r"(-?\d+)\(([a-z0-9]+)\)", ops[1].lower())
                    if not m:
                        raise ValueError(f"Malformed memory address '{ops[1]}'")
                    offset = int(m.group(1))
                    base_reg = self._get_reg_idx(m.group(2))
                    addr = self.regs[base_reg] + offset
                    val = self.memory.get(addr, 0)
                    if rd != 0:
                        self.regs[rd] = val

                elif mnemonic == "sw":
                    # sw rs, offset(sp)
                    rs = self._get_reg_idx(ops[0])
                    m = re.match(r"(-?\d+)\(([a-z0-9]+)\)", ops[1].lower())
                    if not m:
                        raise ValueError(f"Malformed memory address '{ops[1]}'")
                    offset = int(m.group(1))
                    base_reg = self._get_reg_idx(m.group(2))
                    addr = self.regs[base_reg] + offset
                    self.memory[addr] = self.regs[rs]

                elif mnemonic == "ret":
                    # Return from function; terminate simulation
                    break

                else:
                    # Unrecognized instruction, skip
                    pass

            except Exception as e:
                return ExecutionResult(
                    return_code=self.regs[10],
                    cycles_executed=total_cycles,
                    instructions_executed=total_insts,
                    success=False,
                    error_message=f"Runtime error at line '{raw}': {e}",
                )

            pc = next_pc

        # Build final named register dictionary
        named_regs = {}
        for idx, val in enumerate(self.regs):
            name = self.REV_REG_MAP.get(idx, f"x{idx}")
            named_regs[name] = val

        return ExecutionResult(
            return_code=self.regs[10],  # a0
            cycles_executed=total_cycles,
            instructions_executed=total_insts,
            final_registers=named_regs,
            success=True,
        )
