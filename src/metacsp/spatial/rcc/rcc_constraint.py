"""Port of spatial/RCC/RCCConstraint.java."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from metacsp.framework.binary_constraint import BinaryConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint

__all__ = ["RCCConstraint"]


class RCCConstraint(BinaryConstraint):
    """Implementation of RCC-8 (Region Connection Calculus) constraints."""

    class Type(Enum):
        # Explicit 0-based values matching Java's ordinal() indexing into
        # TRANSITION_TABLE.
        DC = 0  # DisConnected
        EC = 1  # Externally Connected
        PO = 2  # Partially Overlapping
        TPP = 3  # Tangential Proper Part
        NTPP = 4  # Non-Tangential Proper Part
        TPPI = 5  # Inverse of Tangential Proper Part
        NTPPI = 6  # Inverse of Non-Tangential Proper Part
        EQ = 7  # Equal

    def __init__(self, *types: Type) -> None:
        super().__init__()
        self._types: list[RCCConstraint.Type] = list(types)

    @property
    def types(self) -> list[Type]:
        return self._types

    @types.setter
    def types(self, types: list[Type]) -> None:
        self._types = types

    @property
    def edge_label(self) -> str:
        return "[" + ", ".join(t.name for t in self._types) + "]"

    def clone(self) -> RCCConstraint:
        return RCCConstraint(*self._types)

    def is_equivalent(self, c: Constraint) -> bool:
        return False

    def __str__(self) -> str:
        ret = "["
        for t in self._types:
            ret += f"({self.from_}) --{t.name}--> ({self.to})"
        ret += "]"
        return ret

    @staticmethod
    def get_inverse_relation(t: Type) -> Type:
        if t is RCCConstraint.Type.TPP:
            return RCCConstraint.Type.TPPI
        if t is RCCConstraint.Type.NTPP:
            return RCCConstraint.Type.NTPPI
        return t


Type = RCCConstraint.Type

# 8x8 composition table indexed [relation1.value][relation2.value].
TRANSITION_TABLE: list[list[list[Type]]] = [
    [
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP, Type.TPPI, Type.NTPPI, Type.EQ],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP],
        [Type.DC],
        [Type.DC],
        [Type.DC],
    ],
    [
        [Type.DC, Type.EC, Type.PO, Type.TPPI, Type.NTPPI],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.TPPI, Type.EQ],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP],
        [Type.EC, Type.PO, Type.TPP, Type.NTPP],
        [Type.PO, Type.TPP, Type.NTPP],
        [Type.DC, Type.EC],
        [Type.DC],
        [Type.EC],
    ],
    [
        [Type.DC, Type.EC, Type.PO, Type.TPPI, Type.NTPPI],
        [Type.DC, Type.EC, Type.PO, Type.TPPI, Type.NTPPI],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP, Type.TPPI, Type.NTPPI, Type.EQ],
        [Type.PO, Type.TPP, Type.NTPP],
        [Type.PO, Type.TPP, Type.NTPP],
        [Type.DC, Type.EC, Type.PO, Type.TPPI, Type.NTPPI],
        [Type.DC, Type.EC, Type.PO, Type.TPPI, Type.NTPPI],
        [Type.PO],
    ],
    [
        [Type.DC],
        [Type.DC, Type.EC],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP],
        [Type.TPP, Type.NTPP],
        [Type.NTPP],
        [Type.DC, Type.EC, Type.PO, Type.TPPI, Type.NTPPI, Type.EQ],
        [Type.DC, Type.EC, Type.PO, Type.TPPI, Type.NTPPI],
        [Type.TPP],
    ],
    [
        [Type.DC],
        [Type.DC],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP],
        [Type.NTPP],
        [Type.NTPP],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP],
        [Type.DC, Type.EC, Type.PO, Type.TPP, Type.NTPP, Type.TPPI, Type.NTPPI, Type.EQ],
        [Type.NTPP],
    ],
    [
        [Type.DC, Type.EC, Type.PO, Type.TPPI, Type.NTPPI],
        [Type.EC, Type.PO, Type.TPPI, Type.NTPPI],
        [Type.PO, Type.TPPI, Type.NTPPI],
        [Type.PO, Type.EQ, Type.TPP, Type.TPPI],
        [Type.PO, Type.TPP, Type.NTPP],
        [Type.TPPI, Type.NTPPI],
        [Type.NTPPI],
        [Type.TPPI],
    ],
    [
        [Type.DC, Type.EC, Type.PO, Type.TPPI, Type.NTPPI],
        [Type.PO, Type.TPPI, Type.NTPPI],
        [Type.PO, Type.TPPI, Type.NTPPI],
        [Type.PO, Type.TPPI, Type.NTPPI],
        [Type.PO, Type.TPPI, Type.TPP, Type.NTPP, Type.NTPPI, Type.EQ],
        [Type.NTPPI],
        [Type.NTPPI],
        [Type.NTPPI],
    ],
    [
        [Type.DC],
        [Type.EC],
        [Type.PO],
        [Type.TPP],
        [Type.NTPP],
        [Type.TPPI],
        [Type.NTPPI],
        [Type.EQ],
    ],
]

RCCConstraint.TRANSITION_TABLE = TRANSITION_TABLE
