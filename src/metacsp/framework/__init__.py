"""Port of the ``framework/`` package: the core Meta-CSP variable/constraint/
solver abstractions (M2)."""

from metacsp.framework.binary_constraint import BinaryConstraint
from metacsp.framework.constraint import Constraint
from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.constraint_network_change_event import (
    ChangeKind,
    ConstraintNetworkChangeEvent,
)
from metacsp.framework.constraint_network_marking import ConstraintNetworkMarking
from metacsp.framework.constraint_ordering_h import ConstraintOrderingH
from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.domain import Domain
from metacsp.framework.dummy_constraint import DummyConstraint
from metacsp.framework.dummy_variable import DummyVariable
from metacsp.framework.value_choice_function import ValueChoiceFunction
from metacsp.framework.value_ordering_h import ValueOrderingH
from metacsp.framework.variable import Variable
from metacsp.framework.variable_ordering_h import VariableOrderingH
from metacsp.framework.variable_prototype import VariablePrototype

__all__ = [
    "BinaryConstraint",
    "ChangeKind",
    "Constraint",
    "ConstraintNetwork",
    "ConstraintNetworkChangeEvent",
    "ConstraintNetworkMarking",
    "ConstraintOrderingH",
    "ConstraintSolver",
    "Domain",
    "DummyConstraint",
    "DummyVariable",
    "ValueChoiceFunction",
    "ValueOrderingH",
    "Variable",
    "VariableOrderingH",
    "VariablePrototype",
]
