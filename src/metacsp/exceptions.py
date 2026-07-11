"""Port of the ``throwables/`` package (one exception class per Java file).

Java sources: throwables/*.java and throwables/time/*.java. Java distinguishes
``Error``, ``Exception`` and ``RuntimeException``; in Python they all derive
from :class:`Exception`. Constructors take the same arguments as their Java
counterparts (objects from later milestones are accepted duck-typed and only
stringified), and produce the same messages.
"""

from __future__ import annotations

from typing import Any, Sequence

__all__ = [
    "ConstraintNotFound",
    "IllegalValueChoiceFunction",
    "IllegalVariableRemoval",
    "InvalidActivityException",
    "NoFocusDefinedException",
    "NoFootprintException",
    "NonInstantiatedDomain",
    "NoSymbolsException",
    "PossibilityDegreeMismathcException",
    "StateNotFound",
    "SymbolNotFoundException",
    "UnimplementedSubVariableException",
    "VariableNotFound",
    "WrongSymbolListException",
    "MalformedBoundsException",
    "MalformedSimpleDistanceConstraint",
]


def _java_array_str(items: Sequence[Any]) -> str:
    """Render a sequence like Java's ``Arrays.toString`` (``[a, b, c]``)."""
    return "[" + ", ".join(str(item) for item in items) + "]"


class ConstraintNotFound(Exception):
    """Port of throwables/ConstraintNotFound.java."""

    def __init__(self, constraint_or_message: Any):
        if isinstance(constraint_or_message, str):
            super().__init__(f"Constraint not found: {constraint_or_message}")
        else:
            super().__init__(f"Constraint {constraint_or_message} not found")


class IllegalValueChoiceFunction(Exception):
    """Port of throwables/IllegalValueChoiceFunction.java."""

    def __init__(self, vcf: str, domain_name: str):
        super().__init__(f"ValueFunction {vcf} not defined for domain {domain_name}")


class IllegalVariableRemoval(Exception):
    """Port of throwables/IllegalVariableRemoval.java."""

    def __init__(self, v: Any, constraints: Sequence[Any]):
        owner = "" if v.owner is None else f" (belonging to {v.owner})"
        super().__init__(
            f"Cannot remove {v}{owner} as it is involved in {_java_array_str(constraints)}"
        )


class InvalidActivityException(Exception):
    """Port of throwables/InvalidActivityException.java."""

    def __init__(self, a: str):
        super().__init__(f"Cannot state head of rule ({a}) as required activity")


class NoFocusDefinedException(Exception):
    """Port of throwables/NoFocusDefinedException.java."""

    def __init__(self, *vars: Any):
        super().__init__(_java_array_str(vars))


class NoFootprintException(Exception):
    """Port of throwables/NoFootprintException.java."""

    def __init__(self, msg: str):
        super().__init__(msg)


class NonInstantiatedDomain(Exception):
    """Port of throwables/NonInstantiatedDomain.java."""

    def __init__(self, v: Any):
        super().__init__(f"Domain of variable {v.id} is empty")


class NoSymbolsException(Exception):
    """Port of throwables/NoSymbolsException.java."""

    def __init__(self, var: Any):
        super().__init__(
            f"The solver of {var} has no registered symbols it can reason upon"
            " - please provide vocabulary in call to solver constructor"
        )


class PossibilityDegreeMismathcException(Exception):
    """Port of throwables/PossibilityDegreeMismathcException.java (sic)."""

    def __init__(self, v: Any, vals: Sequence[float]):
        super().__init__(
            f"Symbols  {_java_array_str(v.symbols)} do not match possibility degrees"
            f" {_java_array_str(vals)}"
        )


class StateNotFound(Exception):
    """Port of throwables/StateNotFound.java."""

    def __init__(self, s: str, fsa: Any):
        super().__init__(f"State {s} not found in FSA {fsa}")


class SymbolNotFoundException(Exception):
    """Port of throwables/SymbolNotFoundException.java."""

    def __init__(self, v: Any, val: str):
        super().__init__(f"Symbol {val} not found in domain {_java_array_str(v.symbols)}")


class UnimplementedSubVariableException(Exception):
    """Port of throwables/UnimplementedSubVariableException.java."""

    def __init__(self, cs: Any):
        super().__init__(f"Solver {cs} has empty implementation of createVariablesSub().")


class VariableNotFound(Exception):
    """Port of throwables/VariableNotFound.java."""

    def __init__(self, v: Any):
        super().__init__(f"Variable {v} not found")


class WrongSymbolListException(Exception):
    """Port of throwables/WrongSymbolListException.java."""

    def __init__(self, length_seen: int, length_expected: int):
        super().__init__(
            f"Cannot impose unary value for {length_seen} symbols"
            f" (expecting {length_expected} symbols)"
        )


class MalformedBoundsException(Exception):
    """Port of throwables/time/MalformedBoundsException.java."""

    def __init__(self, t: Any, b: Any):
        super().__init__(f"Cannot make {t} constraints with bounds {b}")


class MalformedSimpleDistanceConstraint(Exception):
    """Port of throwables/time/MalformedSimpleDistanceConstraint.java."""

    def __init__(self, c: Any, bug_id: int):
        super().__init__(
            f"SimpleDistanceConstraint {c} is malformed"
            f" (this is a BUG (ref #{bug_id}) -- please notify maintainer(s))"
        )
