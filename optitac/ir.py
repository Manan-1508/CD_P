"""
OptiTAC: Intermediate Representation (IR) Data Structures
Defines Quadruple representation, instruction classification, and operand utilities.
"""

from dataclasses import dataclass
from typing import Optional, Set, List


@dataclass
class Quadruple:
    op: str
    arg1: Optional[str]
    arg2: Optional[str]
    res: str
    raw: str = ""
    line_no: int = 0

    def to_tac(self) -> str:
        if self.op == "LABEL":
            return f"{self.arg1}:"
        elif self.op == "goto":
            return f"goto {self.arg1}"
        elif self.op.startswith("if_"):
            relop = self.op.replace("if_", "")
            if relop == "true":
                return f"if {self.arg1} goto {self.res}"
            elif relop == "false":
                return f"ifFalse {self.arg1} goto {self.res}"
            return f"if {self.arg1} {relop} {self.arg2} goto {self.res}"
        elif self.op == "=":
            return f"{self.res} = {self.arg1}"
        elif self.op == "return":
            return f"return {self.arg1}".strip() if self.arg1 else "return"
        elif self.op == "param":
            return f"param {self.arg1}"
        elif self.op == "call":
            if self.res:
                return f"{self.res} = call {self.arg1}, {self.arg2}"
            return f"call {self.arg1}, {self.arg2}"
        elif self.op.startswith("u"):
            return f"{self.res} = {self.op[1:]}{self.arg1}"
        elif self.op == "[]_read":
            return f"{self.res} = {self.arg1}[{self.arg2}]"
        elif self.op == "[]_write":
            return f"{self.res}[{self.arg1}] = {self.arg2}"
        elif self.op == "RAW":
            return self.raw or self.arg1 or ""
        else:
            return f"{self.res} = {self.arg1} {self.op} {self.arg2}"

    def is_label(self) -> bool:
        return self.op == "LABEL"

    def is_branch(self) -> bool:
        return self.op.startswith("if_") or self.op == "goto"

    def is_conditional_branch(self) -> bool:
        return self.op.startswith("if_")

    def is_unconditional_jump(self) -> bool:
        return self.op == "goto"

    def is_return(self) -> bool:
        return self.op == "return"

    def is_assignment(self) -> bool:
        return bool(self.res and self.op not in {"LABEL", "goto", "return", "param"} and not self.op.startswith("if_"))

    @staticmethod
    def is_constant(val: Optional[str]) -> bool:
        if val is None:
            return False
        return val.lstrip("-").isdigit()

    def defined_var(self) -> Optional[str]:
        """Returns the variable defined by this instruction, if any."""
        if self.is_assignment() and not self.op == "[]_write":
            return self.res
        return None

    def used_vars(self) -> Set[str]:
        """Returns variables read/used by this instruction (excluding literals)."""
        used = set()
        if self.op == "LABEL" or self.op == "goto":
            return used

        if self.op.startswith("if_"):
            if self.arg1 and not self.is_constant(self.arg1):
                used.add(self.arg1)
            if self.arg2 and not self.is_constant(self.arg2):
                used.add(self.arg2)
            return used

        if self.op == "[]_write":
            if self.res and not self.is_constant(self.res):
                used.add(self.res)
            if self.arg1 and not self.is_constant(self.arg1):
                used.add(self.arg1)
            if self.arg2 and not self.is_constant(self.arg2):
                used.add(self.arg2)
            return used

        if self.arg1 and not self.is_constant(self.arg1):
            used.add(self.arg1)
        if self.arg2 and not self.is_constant(self.arg2):
            used.add(self.arg2)
        return used

    def get_expression_key(self) -> Optional[tuple]:
        """Returns canonical (op, arg1, arg2) key for CSE, normalizing commutative ops."""
        if self.op in {"+", "-", "*", "/", "%", "&", "|", "^"}:
            a1, a2 = self.arg1, self.arg2
            if self.op in {"+", "*", "&", "|", "^"} and a2 and a1 > a2:
                a1, a2 = a2, a1
            return (self.op, a1, a2)
        return None
