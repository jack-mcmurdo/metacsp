"""Port of fuzzyAllenInterval/FuzzyAllenIntervalConstraint.java.

Each constraint is a fuzzy set of the 13 Allen temporal relations, where each
relation has an associated possibility degree. Possibility of relations not
explicitly given is computed via Freksa's conceptual neighborhood (the
``FREKSA_NEIGHBOR``/``DELTAS`` tables below).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.time.qualitative.qualitative_allen_interval_constraint import (
    QualitativeAllenIntervalConstraint,
)

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint

__all__ = ["FuzzyAllenIntervalConstraint"]

Type = QualitativeAllenIntervalConstraint.Type


class FuzzyAllenIntervalConstraint(QualitativeAllenIntervalConstraint):
    """A fuzzy set of Allen relations, each carrying a possibility degree."""

    Type = QualitativeAllenIntervalConstraint.Type

    # Transition table for Freksa's conceptual neighborhood: the neighborhood
    # "distance" between every pair of basic Allen relations.
    FREKSA_NEIGHBOR: list[list[int]] = [
        [0, 1, 2, 3, 4, 5, 6, 3, 4, 5, 6, 7, 8],  # Before
        [1, 0, 1, 2, 3, 4, 4, 2, 3, 4, 5, 6, 7],  # Meets
        [2, 1, 0, 1, 2, 3, 4, 1, 2, 3, 4, 5, 6],  # Overlaps
        [3, 2, 1, 0, 1, 2, 2, 2, 3, 4, 3, 4, 5],  # FinishedBy
        [4, 3, 2, 1, 0, 1, 1, 3, 2, 3, 2, 3, 4],  # Contains
        [5, 4, 3, 2, 1, 0, 2, 4, 3, 2, 1, 2, 3],  # StartedBy
        [5, 4, 3, 2, 1, 2, 0, 2, 1, 2, 3, 4, 5],  # Equals
        [3, 2, 1, 2, 3, 4, 2, 0, 1, 2, 3, 4, 5],  # Starts
        [4, 3, 2, 3, 2, 3, 1, 1, 0, 1, 2, 3, 4],  # During
        [5, 4, 3, 4, 3, 2, 2, 2, 1, 0, 1, 2, 3],  # Finishes
        [6, 5, 4, 3, 2, 1, 3, 3, 2, 1, 0, 1, 2],  # OverlappedBy
        [7, 6, 5, 4, 3, 2, 4, 4, 3, 2, 1, 0, 1],  # MetBy
        [8, 7, 6, 5, 4, 3, 5, 5, 4, 3, 2, 1, 0],  # After
    ]

    # How possibility decreases with distance in Freksa's neighborhood.
    DELTAS: list[float] = [1.0, 0.8, 0.6, 0.4, 0.2, 0.1, 0.0, 0.0, 0.0]

    def get_possibilities(self) -> dict[Type, float]:
        """Current possibilities of all 13 Allen relations."""
        fr = {t: 0.0 for t in Type}
        for type_ in self.types:
            row = FuzzyAllenIntervalConstraint.FREKSA_NEIGHBOR[type_.value]
            for t in range(len(row)):
                candidate = FuzzyAllenIntervalConstraint.lookup_type_by_int(t)
                fr[candidate] = max(
                    fr[candidate], FuzzyAllenIntervalConstraint.get_possibility_degree(row[t])
                )
        return fr

    def make_crisp_rel(self) -> dict[Type, float]:
        fr = {t: 0.0 for t in Type}
        for type_ in self.types:
            fr[type_] = 1.0
        return fr

    def get_inverse_possibilities(self) -> dict[Type, float]:
        """Possibilities of all inverse relations."""
        ret = {t: 0.0 for t in Type}
        for t in self.types:
            inverse_relation = FuzzyAllenIntervalConstraint.get_inverse_relation(t)
            possibilities = self.get_possibilities()
            ret[inverse_relation] = possibilities[t]

            row = FuzzyAllenIntervalConstraint.FREKSA_NEIGHBOR[inverse_relation.value]
            fr = {
                FuzzyAllenIntervalConstraint.lookup_type_by_int(
                    i
                ): FuzzyAllenIntervalConstraint.get_possibility_degree(row[i])
                for i in range(len(row))
            }
            for t1 in fr:
                ret[t1] = max(ret[t1], fr[t1])
        return ret

    def get_crisp_inverse(self) -> dict[Type, float]:
        ret = {t: 0.0 for t in Type}
        for t in self.types:
            inverse_relation = FuzzyAllenIntervalConstraint.get_inverse_relation(t)
            possibilities = self.get_possibilities()
            ret[inverse_relation] = possibilities[t]
        return ret

    def clone(self) -> FuzzyAllenIntervalConstraint:
        ret = FuzzyAllenIntervalConstraint()
        ret.types = self.types
        return ret

    @staticmethod
    def get_possibility_degree(distance: int) -> float:
        return FuzzyAllenIntervalConstraint.DELTAS[distance]

    def is_equivalent(self, c: Constraint) -> bool:
        fc = cast(FuzzyAllenIntervalConstraint, c)
        if not (fc.from_ == self.from_ and fc.to == self.to):
            return False
        for t in self.types:
            found = False
            for t1 in fc.types:
                if t == t1:
                    found = True
                    break
                if not found:
                    return False
        return True
