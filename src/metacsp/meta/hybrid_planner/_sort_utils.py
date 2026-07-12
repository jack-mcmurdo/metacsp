"""Shared helper for a private static ``sortHashMapByValues``/
``sortHashMapByValuesD`` method that Java duplicates near-identically across
``FluentBasedSimpleDomain``, ``MetaSpatialAdherenceConstraint``,
``SimpleHybridPlannerInferenceCallback`` and the example
``TestSimpleHybridPlanner`` (each just walks the key/value ``ArrayList``
copies to bubble matching entries into a ``LinkedHashMap`` in sorted-by-value
order -- some ascending, one descending via ``Collections.reverseOrder()``).
Not a Java class of its own; collapsing the duplication is a pure
simplification (C7: Java's HashMap-keyed intermediate makes tie-breaking
among equal values unspecified there too, so a stable Python sort is exactly
as valid an "observable behavior" as the original).
"""

from __future__ import annotations

from typing import TypeVar

_K = TypeVar("_K")
_V = TypeVar("_V")


def sort_dict_by_value(passed_map: dict[_K, _V], *, reverse: bool = False) -> dict[_K, _V]:
    """A new dict with ``passed_map``'s entries in ascending (or, if
    ``reverse``, descending) order of value; ties keep ``passed_map``'s
    insertion order (stable sort)."""
    return dict(sorted(passed_map.items(), key=lambda kv: kv[1], reverse=reverse))
