"""Port of meta/symbolsAndTime/Floor2D.java."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, cast

from metacsp.meta.symbols_and_time.schedulable import Schedulable
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH
    from metacsp.multi.activity.activity import Activity

__all__ = ["Floor2D"]


class Floor2D(Schedulable):
    """A Schedulable representing a 2D floor: Activities whose symbolic
    values encode "xNyM" coordinates conflict when they are within
    ``distance_threshold`` of each other."""

    def __init__(
        self,
        var_oh: VariableOrderingH | None,
        val_oh: ValueOrderingH | None,
        distance_threshold: float,
    ) -> None:
        super().__init__(var_oh, val_oh)
        self.distance_threshold = distance_threshold

    def is_conflicting(self, peak: list[Activity]) -> bool:
        """True iff the peak's two Activities' 2D coordinates are within the distance threshold."""
        if len(peak) == 1:
            return False
        sva0 = cast(SymbolicVariableActivity, peak[0].variable)
        sva1 = cast(SymbolicVariableActivity, peak[1].variable)
        coords1 = self._parse_coordinates(sva0.symbolic_variable.symbols[0])
        coords2 = self._parse_coordinates(sva1.symbolic_variable.symbols[0])
        return self._eucledian_distance(coords1, coords2) <= self.distance_threshold

    def draw(self, network: ConstraintNetwork) -> None:
        """Draw a top-down 2D plot of the floor with resource conflicts.

        The Java Swing ``JFrame``/``JPanel`` renderer is not ported (skip
        list); a browser-based view is future work (D10).
        """
        raise NotImplementedError("the Swing 2D floor renderer is not ported; see D10")

    def _parse_coordinates(self, coords: str) -> tuple[float, float]:
        x_string = coords[1 : coords.index("y")]
        y_string = coords[coords.index("y") + 1 :]
        return float(x_string), float(y_string)

    def _eucledian_distance(
        self, point1: tuple[float, float], point2: tuple[float, float]
    ) -> float:
        return math.sqrt((point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2)

    def __str__(self) -> str:
        # Java's toString() is an unfinished "TODO Auto-generated method
        # stub" that returns null; Python's __str__ must return str, so this
        # substitutes the sibling ReusableResource's finished implementation.
        return type(self).__name__

    @property
    def edge_label(self) -> str | None:
        """Always None: Floor2D is not drawn as a graph edge."""
        return None

    def clone(self) -> Floor2D | None:
        """Always None: Floor2D does not support cloning."""
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        """Always False: Floor2D has no notion of equivalence."""
        return False

    def get_ground_solver(self) -> ConstraintSolver | None:
        """Always None: Floor2D has no single ground solver of its own."""
        return None

    def get_meta_values(self, meta_variable: MetaVariable) -> list[ConstraintNetwork] | None:
        """Always None: Floor2D conflicts are never resolvable (unfinished upstream)."""
        # Java overrides Schedulable's getMetaValues() with an unfinished
        # "TODO Auto-generated method stub" that always returns null --
        # reproduced verbatim: Floor2D conflicts are never resolvable.
        return None
