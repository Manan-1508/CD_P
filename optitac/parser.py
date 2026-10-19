"""
OptiTAC: Dynamic Three-Address Code (TAC) Parser & Diagnostics
Parses TAC source strings and input files into Quadruple sequences.
Supports labels, arithmetic, logical, branching, function calls, and array operations.
Includes comprehensive syntactic and semantic error diagnostics with actionable error hints.
"""

import re
from typing import List, Optional, Tuple, Dict, Set
from dataclasses import dataclass
from optitac.ir import Quadruple


@dataclass
class Diagnostic:
    """Represents a compiler error or warning with source context and helpful hints."""
    severity: str  # 'ERROR' or 'WARNING'
    line_no: int
    raw_line: str
    message: str
    suggestion: str = ""

    def format(self) -> str:
        tag = "[COMPILER ERROR]" if self.severity == "ERROR" else "[COMPILER WARNING]"
        out = f"  {tag} Line {self.line_no}: {self.message}\n         Source : {self.raw_line}"
        if self.suggestion:
            out += f"\n         Hint   : {self.suggestion}"
        return out


class ParseDiagnosticError(Exception):
    """Raised when strict parsing fails due to compiler errors."""
    def __init__(self, diagnostics: List[Diagnostic]):
        self.diagnostics = diagnostics
        msg = f"Compilation halted with {len(diagnostics)} diagnostic error(s):\n" + "\n".join(d.format() for d in diagnostics)
        super().__init__(msg)


class TACParser:
    """Robust dynamic parser and semantic validator for Three-Address Code."""

    # Regular Expressions for TAC Grammar
    LABEL_RE = re.compile(r"^([a-zA-Z_]\w*)\s*:$")
    ASSIGN_BIN_RE = re.compile(
        r"^([a-zA-Z_]\w*)\s*=\s*([a-zA-Z0-9_\-\.]+)\s*([\+\-\*/%&\|\^<>!=]=?|==|!=|<<|>>)\s*([a-zA-Z0-9_\-\.]+)$"
    )
    ASSIGN_UNARY_RE = re.compile(r"^([a-zA-Z_]\w*)\s*=\s*([\+\-!~])\s*([a-zA-Z0-9_\-\.]+)$")
    ARRAY_READ_RE = re.compile(r"^([a-zA-Z_]\w*)\s*=\s*([a-zA-Z_]\w*)\[\s*([a-zA-Z0-9_\-\.]+)\s*\]$")
    ARRAY_WRITE_RE = re.compile(r"^([a-zA-Z_]\w*)\[\s*([a-zA-Z0-9_\-\.]+)\s*\]\s*=\s*([a-zA-Z0-9_\-\.]+)$")
    CALL_ASSIGN_RE = re.compile(r"^([a-zA-Z_]\w*)\s*=\s*call\s+([a-zA-Z_]\w*)\s*,\s*(\d+)$")
    CALL_VOID_RE = re.compile(r"^call\s+([a-zA-Z_]\w*)\s*,\s*(\d+)$")
    PARAM_RE = re.compile(r"^param\s+([a-zA-Z0-9_\-\.]+)$")
    ASSIGN_COPY_RE = re.compile(r"^([a-zA-Z_]\w*)\s*=\s*([a-zA-Z0-9_\-\.]+)$")
    IF_RELOP_GOTO_RE = re.compile(
        r"^if\s+([a-zA-Z0-9_\-\.]+)\s*([<>=!]+)\s*([a-zA-Z0-9_\-\.]+)\s+goto\s+([a-zA-Z_]\w*)$"
    )
    IF_FALSE_GOTO_RE = re.compile(r"^ifFalse\s+([a-zA-Z0-9_\-\.]+)\s+goto\s+([a-zA-Z_]\w*)$")
    IF_TRUE_GOTO_RE = re.compile(r"^if\s+([a-zA-Z0-9_\-\.]+)\s+goto\s+([a-zA-Z_]\w*)$")
    GOTO_RE = re.compile(r"^goto\s+([a-zA-Z_]\w*)$")
    RETURN_RE = re.compile(r"^return(?:\s+([a-zA-Z0-9_\-\.]+))?$")

    @classmethod
    def parse_line(cls, line: str, line_no: int) -> Optional[Quadruple]:
        """Parses a single line of TAC into a Quadruple object."""
        cleaned = line.split("//")[0].split("#")[0].strip()
        if not cleaned:
            return None

        # 1. Label definition (e.g., L1:, loop_start:)
        m = cls.LABEL_RE.match(cleaned)
        if m:
            return Quadruple(op="LABEL", arg1=m.group(1), arg2=None, res="", raw=cleaned, line_no=line_no)

        # 2. Binary Arithmetic / Comparison / Logical (e.g., t1 = a + b)
        m = cls.ASSIGN_BIN_RE.match(cleaned)
        if m:
            res, arg1, op, arg2 = m.groups()
            return Quadruple(op=op, arg1=arg1, arg2=arg2, res=res, raw=cleaned, line_no=line_no)

        # 3. Unary Operation (e.g., t1 = - a)
        m = cls.ASSIGN_UNARY_RE.match(cleaned)
        if m:
            res, op, arg1 = m.groups()
            return Quadruple(op=f"u{op}", arg1=arg1, arg2=None, res=res, raw=cleaned, line_no=line_no)

        # 4. Array Read (e.g., t1 = a[i])
        m = cls.ARRAY_READ_RE.match(cleaned)
        if m:
            res, arr, idx = m.groups()
            return Quadruple(op="[]_read", arg1=arr, arg2=idx, res=res, raw=cleaned, line_no=line_no)

        # 5. Array Write (e.g., a[i] = t1)
        m = cls.ARRAY_WRITE_RE.match(cleaned)
        if m:
            arr, idx, val = m.groups()
            return Quadruple(op="[]_write", arg1=idx, arg2=val, res=arr, raw=cleaned, line_no=line_no)

        # 6. Function Call with Assignment (e.g., t1 = call func, 2)
        m = cls.CALL_ASSIGN_RE.match(cleaned)
        if m:
            res, func, num_args = m.groups()
            return Quadruple(op="call", arg1=func, arg2=num_args, res=res, raw=cleaned, line_no=line_no)

        # 7. Void Function Call (e.g., call print, 1)
        m = cls.CALL_VOID_RE.match(cleaned)
        if m:
            func, num_args = m.groups()
            return Quadruple(op="call", arg1=func, arg2=num_args, res="", raw=cleaned, line_no=line_no)

        # 8. Function Parameter (e.g., param x)
        m = cls.PARAM_RE.match(cleaned)
        if m:
            arg = m.group(1)
            return Quadruple(op="param", arg1=arg, arg2=None, res="", raw=cleaned, line_no=line_no)

        # 9. Return Statement (e.g., return y or return)
        m = cls.RETURN_RE.match(cleaned)
        if m:
            ret_val = m.group(1) or None
            return Quadruple(op="return", arg1=ret_val, arg2=None, res="", raw=cleaned, line_no=line_no)

        # 10. Copy / Constant Assignment (e.g., x = 10, y = x)
        m = cls.ASSIGN_COPY_RE.match(cleaned)
        if m:
            res, arg1 = m.groups()
            return Quadruple(op="=", arg1=arg1, arg2=None, res=res, raw=cleaned, line_no=line_no)

        # 11. Conditional Relational Jump (e.g., if a > b goto L1)
        m = cls.IF_RELOP_GOTO_RE.match(cleaned)
        if m:
            arg1, relop, arg2, target = m.groups()
            return Quadruple(op=f"if_{relop}", arg1=arg1, arg2=arg2, res=target, raw=cleaned, line_no=line_no)

        # 12. Conditional False Jump (e.g., ifFalse flag goto L1)
        m = cls.IF_FALSE_GOTO_RE.match(cleaned)
        if m:
            arg1, target = m.groups()
            return Quadruple(op="if_false", arg1=arg1, arg2=None, res=target, raw=cleaned, line_no=line_no)

        # 13. Conditional True / Single Boolean Jump (e.g., if cond goto L1)
        m = cls.IF_TRUE_GOTO_RE.match(cleaned)
        if m:
            arg1, target = m.groups()
            return Quadruple(op="if_true", arg1=arg1, arg2=None, res=target, raw=cleaned, line_no=line_no)

        # 14. Unconditional Jump (e.g., goto L2)
        m = cls.GOTO_RE.match(cleaned)
        if m:
            target = m.group(1)
            return Quadruple(op="goto", arg1=target, arg2=None, res="", raw=cleaned, line_no=line_no)

        # Fallback to RAW instruction (Unmatched grammar)
        return Quadruple(op="RAW", arg1=cleaned, arg2=None, res="", raw=cleaned, line_no=line_no)

    @classmethod
    def validate_program(cls, quads: List[Quadruple]) -> List[Diagnostic]:
        """
        Runs syntactic and semantic diagnostics on parsed Quadruples.
        Identifies unparsed syntax, undefined jump labels, duplicate labels, and division by zero.
        """
        diagnostics: List[Diagnostic] = []
        defined_labels: Dict[str, int] = {}

        # First pass: collect label definitions and detect duplicates
        for q in quads:
            if q.op == "LABEL":
                lbl = q.arg1 or ""
                if lbl in defined_labels:
                    diagnostics.append(
                        Diagnostic(
                            severity="ERROR",
                            line_no=q.line_no,
                            raw_line=q.raw,
                            message=f"Duplicate label definition '{lbl}'.",
                            suggestion=f"Label '{lbl}' was already defined at line {defined_labels[lbl]}. Rename this label.",
                        )
                    )
                else:
                    defined_labels[lbl] = q.line_no

        # Second pass: check syntax errors, undefined jump targets, division by zero
        has_return = False
        for q in quads:
            # 1. Unrecognized grammar
            if q.op == "RAW":
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        line_no=q.line_no,
                        raw_line=q.raw,
                        message="Invalid Three-Address Code (TAC) syntax.",
                        suggestion="Check operand spacing or operators. Expected format: 'dest = arg1 op arg2' or 'goto L'.",
                    )
                )

            # 2. Undefined Branch Labels
            elif q.is_branch():
                target = q.res if q.op.startswith("if_") else q.arg1
                if target and target not in defined_labels:
                    diagnostics.append(
                        Diagnostic(
                            severity="ERROR",
                            line_no=q.line_no,
                            raw_line=q.raw,
                            message=f"Branch target label '{target}' is undefined in the program.",
                            suggestion=f"Define the target label '{target}:' before jumping to it.",
                        )
                    )

            # 3. Compile-time Division by Zero
            elif q.op in {"/", "%"} and q.arg2 == "0":
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        line_no=q.line_no,
                        raw_line=q.raw,
                        message="Compile-time division or modulo by zero detected.",
                        suggestion="Ensure divisor constant is non-zero to avoid hardware traps.",
                    )
                )

            if q.is_return():
                has_return = True

        if not has_return and quads:
            diagnostics.append(
                Diagnostic(
                    severity="WARNING",
                    line_no=quads[-1].line_no,
                    raw_line=quads[-1].raw,
                    message="Missing explicit 'return' statement in program.",
                    suggestion="Add 'return <variable>' or 'return' at the end of the entry procedure.",
                )
            )

        return diagnostics

    @classmethod
    def parse_program(cls, tac_text: str) -> List[Quadruple]:
        """Parses a multi-line TAC string into a list of Quadruples."""
        quads: List[Quadruple] = []
        clean_text = re.sub(r"/\*.*?\*/", "", tac_text, flags=re.DOTALL)
        line_counter = 1
        for raw_line in clean_text.splitlines():
            # Strip comments before splitting on semicolons
            stripped_line = raw_line.split("//")[0].split("#")[0].strip()
            sublines = [s.strip() for s in stripped_line.split(";") if s.strip()]
            if not sublines:
                line_counter += 1
                continue
            for sub in sublines:
                q = cls.parse_line(sub, line_counter)
                if q is not None:
                    quads.append(q)
            line_counter += 1
        return quads

    @classmethod
    def parse_with_diagnostics(cls, tac_text: str, strict: bool = False) -> Tuple[List[Quadruple], List[Diagnostic]]:
        """Parses TAC text and returns both quadruples and diagnostics list."""
        quads = cls.parse_program(tac_text)
        diagnostics = cls.validate_program(quads)
        errors = [d for d in diagnostics if d.severity == "ERROR"]
        if strict and errors:
            raise ParseDiagnosticError(errors)
        return quads, diagnostics

    @classmethod
    def parse_file(cls, filepath: str) -> List[Quadruple]:
        """Reads a .tac file from disk and parses it into Quadruples."""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return cls.parse_program(content)
