"""Port of multi/allenInterval/AllenIntervalConstraint.java.

Implements Allen's Interval Algebra: the 13 basic qualitative relations plus
several tractable disjunctions, each optionally carrying metric bounds (see
``Type`` for details).
"""

from __future__ import annotations

import itertools
from enum import Enum
from typing import TYPE_CHECKING, cast

from metacsp.exceptions import MalformedBoundsException
from metacsp.framework.multi.multi_binary_constraint import MultiBinaryConstraint
from metacsp.time.bounds import INF, Bounds
from metacsp.time.simple_distance_constraint import SimpleDistanceConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable
    from metacsp.multi.allen_interval.allen_interval import AllenInterval
    from metacsp.time.apsp_solver import APSPSolver

__all__ = ["AllenIntervalConstraint"]

_type_id_counter = itertools.count(1)


class AllenIntervalConstraint(MultiBinaryConstraint):
    """A constraint between two AllenIntervals: one or a disjunction of
    Allen's Interval Algebra relations, optionally with metric bounds."""

    class Type(Enum):
        """The 13 basic qualitative relations in Allen's Interval Algebra,
        plus several tractable disjunctions. Metric bounds can be specified
        on basic relations."""

        def __new__(cls, *bound_values: int):
            obj = object.__new__(cls)
            obj._value_ = next(_type_id_counter)
            pairs = [
                Bounds(bound_values[i], bound_values[i + 1]) for i in range(0, len(bound_values), 2)
            ]
            obj.num_params = len(pairs)
            obj.default_interval_bounds = pairs
            return obj

        Before = (1, INF)
        Meets = ()
        Overlaps = (1, INF, 1, INF, 1, INF)
        FinishedBy = (1, INF)
        Contains = (1, INF, 1, INF)
        StartedBy = (1, INF)
        Equals = ()
        Starts = (1, INF)
        During = (1, INF, 1, INF)
        Finishes = (1, INF)
        OverlappedBy = (1, INF, 1, INF, 1, INF)
        After = (1, INF)
        MetBy = ()
        Release = (0, INF)
        Deadline = (0, INF)
        BeforeOrMeets = (0, INF)
        MetByOrAfter = (0, INF)
        MetByOrOverlappedBy = (0, INF)
        MetByOrOverlappedByOrAfter = ()
        MetByOrOverlappedByOrIsFinishedByOrDuring = (0, INF)
        MeetsOrOverlapsOrBefore = ()
        DuringOrEquals = (0, INF, 0, INF)
        DuringOrEqualsOrStartsOrFinishes = (0, INF, 0, INF)
        MeetsOrOverlapsOrFinishedByOrContains = (0, INF)  # PDDL at start
        ContainsOrStartedByOrOverlappedByOrMetBy = (0, INF)  # PDDL at end
        EndsDuring = ()
        EndEnd = (0, INF)  # deprecated
        EndsOrEndedBy = (0, INF)
        At = (0, INF, 0, INF)
        StartStart = (0, INF)  # deprecated
        StartsOrStartedBy = (0, INF)
        Duration = (0, INF)
        Forever = ()
        NotBeforeAndNotAfter = ()
        DisjunctionRelation = ()

        def get_default_bounds(self) -> list[Bounds]:
            return self.default_interval_bounds

        @staticmethod
        def from_string(name: str) -> AllenIntervalConstraint.Type | None:
            """The Type with the given name (non case-sensitive), or None."""
            for t in AllenIntervalConstraint.Type:
                if t.name.lower() == name.lower():
                    return t
            return None

    def __init__(self, *args: Type | Bounds) -> None:
        super().__init__()
        if (
            len(args) >= 2
            and isinstance(args[0], AllenIntervalConstraint.Type)
            and all(isinstance(a, Bounds) for a in args[1:])
        ):
            type_ = cast("AllenIntervalConstraint.Type", args[0])
            bounds = list(cast("tuple[Bounds, ...]", args[1:]))
            self.types: list[AllenIntervalConstraint.Type] = [type_]
            self.bounds: list[Bounds | None] = bounds
            if type_.num_params != len(bounds):
                raise ValueError(
                    f"Invalid numer of parameters for constraint {type_}, "
                    f"expected: {type_.num_params} got {len(bounds)}"
                )
            return

        types = list(cast("tuple[AllenIntervalConstraint.Type, ...]", args))
        if len(types) == 1:
            self.types = types
            self.bounds = list(types[0].get_default_bounds())
        else:
            # Assumed convexity was ensured one step before this constructor is called.
            self.types = types
            fs_ts = [_quantitative_translation_of_allen(t)[0] for t in types]
            fs_te = [_quantitative_translation_of_allen(t)[1] for t in types]
            fe_ts = [_quantitative_translation_of_allen(t)[2] for t in types]
            fe_te = [_quantitative_translation_of_allen(t)[3] for t in types]
            self.bounds = [
                Bounds.union(*fs_ts),
                Bounds.union(*fs_te),
                Bounds.union(*fe_ts),
                Bounds.union(*fe_te),
            ]

    def create_internal_constraints_from_to(
        self, from_: Variable, to: Variable
    ) -> list[Constraint] | None:
        from metacsp.multi.allen_interval.allen_interval import AllenInterval

        if not (isinstance(from_, AllenInterval) and isinstance(to, AllenInterval)):
            return None
        Type = AllenIntervalConstraint.Type

        # The quantitative constraint between two bounds in the translation of R is
        # the union of quantitative constraints between these two bounds which are
        # in the translations of the atomic relations forming R.
        if len(self.types) > 1:
            fs, ts, fe, te = from_.start, to.start, from_.end, to.end
            bounds = self.bounds
            assert bounds[0] is not None and bounds[1] is not None
            assert bounds[2] is not None and bounds[3] is not None

            first: SimpleDistanceConstraint | None = SimpleDistanceConstraint()
            second: SimpleDistanceConstraint | None = SimpleDistanceConstraint()
            third: SimpleDistanceConstraint | None = SimpleDistanceConstraint()
            fourth: SimpleDistanceConstraint | None = SimpleDistanceConstraint()

            if bounds[0].min == -INF and bounds[0].max == INF:
                first = None
            elif bounds[0].min == -INF:
                first.minimum, first.maximum = 0, INF
                first.from_, first.to = ts, fs
            else:
                first.minimum, first.maximum = bounds[0].min, bounds[0].max
                first.from_, first.to = fs, ts

            if bounds[1].min == -INF and bounds[1].max == INF:
                second = None
            elif bounds[1].min == -INF:
                second.minimum, second.maximum = 0, INF
                second.from_, second.to = te, fs
            else:
                second.minimum, second.maximum = bounds[1].min, bounds[1].max
                second.from_, second.to = fs, te

            if bounds[2].min == -INF and bounds[2].max == INF:
                third = None
            elif bounds[2].min == -INF:
                third.minimum, third.maximum = 0, INF
                third.from_, third.to = ts, fe
            else:
                third.minimum, third.maximum = bounds[2].min, bounds[2].max
                third.from_, third.to = fe, ts

            if bounds[3].min == -INF and bounds[3].max == INF:
                fourth = None
            elif bounds[3].min == -INF:
                fourth.minimum, fourth.maximum = 0, INF
                fourth.from_, fourth.to = te, fe
            else:
                fourth.minimum, fourth.maximum = bounds[3].min, bounds[3].max
                fourth.from_, fourth.to = fe, te

            return [sdc for sdc in (first, second, third, fourth) if sdc is not None]

        type_ = self.types[0]
        bounds = self.bounds
        fs, ts, fe, te = from_.start, to.start, from_.end, to.end

        def sdc(
            min_: int, max_: int, from_tp: Variable, to_tp: Variable
        ) -> SimpleDistanceConstraint:
            c = SimpleDistanceConstraint()
            c.minimum, c.maximum = min_, max_
            c.from_, c.to = from_tp, to_tp
            return c

        if type_ is Type.Equals:
            return [sdc(0, 0, fs, ts), sdc(0, 0, te, fe)]

        if type_ is Type.Before:
            assert bounds[0] is not None
            if bounds[0].min == 0:
                raise MalformedBoundsException(Type.Before, bounds[0])
            return [sdc(bounds[0].min, bounds[0].max, fe, ts)]

        if type_ is Type.After:
            assert bounds[0] is not None
            if bounds[0].min == 0:
                raise MalformedBoundsException(Type.After, bounds[0])
            return [sdc(bounds[0].min, bounds[0].max, te, fs)]

        if type_ is Type.Meets:
            return [sdc(0, 0, fe, ts)]

        if type_ is Type.MetBy:
            return [sdc(0, 0, te, fs)]

        if type_ is Type.Starts:
            assert bounds[0] is not None
            if bounds[0].min == 0:
                raise MalformedBoundsException(Type.Starts, bounds[0])
            return [sdc(0, 0, fs, ts), sdc(bounds[0].min, bounds[0].max, fe, te)]

        if type_ is Type.StartedBy:
            assert bounds[0] is not None
            if bounds[0].min == 0:
                raise MalformedBoundsException(Type.StartedBy, bounds[0])
            return [sdc(0, 0, fs, ts), sdc(bounds[0].min, bounds[0].max, te, fe)]

        if type_ is Type.During:
            assert bounds[0] is not None and bounds[1] is not None
            if bounds[0].min == 0:
                raise MalformedBoundsException(Type.During, bounds[0])
            if bounds[1].min == 0:
                raise MalformedBoundsException(Type.During, bounds[1])
            return [
                sdc(bounds[0].min, bounds[0].max, ts, fs),
                sdc(bounds[1].min, bounds[1].max, fe, te),
            ]

        if type_ is Type.Contains:
            assert bounds[0] is not None and bounds[1] is not None
            if bounds[0].min == 0:
                raise MalformedBoundsException(Type.Contains, bounds[0])
            if bounds[1].min == 0:
                raise MalformedBoundsException(Type.Contains, bounds[1])
            return [
                sdc(bounds[0].min, bounds[0].max, fs, ts),
                sdc(bounds[1].min, bounds[1].max, te, fe),
            ]

        if type_ is Type.Finishes:
            assert bounds[0] is not None
            if bounds[0].min == 0:
                raise MalformedBoundsException(Type.Finishes, bounds[0])
            return [sdc(bounds[0].min, bounds[0].max, ts, fs), sdc(0, 0, fe, te)]

        if type_ is Type.FinishedBy:
            assert bounds[0] is not None
            if bounds[0].min == 0:
                raise MalformedBoundsException(Type.FinishedBy, bounds[0])
            return [sdc(bounds[0].min, bounds[0].max, fs, ts), sdc(0, 0, fe, te)]

        if type_ is Type.Overlaps:
            assert bounds[0] is not None and bounds[1] is not None and bounds[2] is not None
            if bounds[0].min == 0:
                raise MalformedBoundsException(Type.Overlaps, bounds[0])
            if bounds[1].min == 0:
                raise MalformedBoundsException(Type.Overlaps, bounds[1])
            if bounds[2].min == 0:
                raise MalformedBoundsException(Type.Overlaps, bounds[2])
            return [
                sdc(bounds[0].min, bounds[0].max, fs, ts),
                sdc(bounds[1].min, bounds[1].max, ts, fe),
                sdc(bounds[2].min, bounds[2].max, fe, te),
            ]

        if type_ is Type.OverlappedBy:
            assert bounds[0] is not None and bounds[1] is not None and bounds[2] is not None
            if bounds[0].min == 0:
                raise MalformedBoundsException(Type.Overlaps, bounds[0])
            if bounds[1].min == 0:
                raise MalformedBoundsException(Type.Overlaps, bounds[1])
            if bounds[2].min == 0:
                raise MalformedBoundsException(Type.Overlaps, bounds[2])
            return [
                sdc(bounds[0].min, bounds[0].max, ts, fs),
                sdc(bounds[1].min, bounds[1].max, fs, te),
                sdc(bounds[2].min, bounds[2].max, te, fe),
            ]

        if type_ is Type.At:
            assert bounds[0] is not None and bounds[1] is not None
            stp_solver = cast("APSPSolver", from_.internal_constraint_solvers[0])
            return [
                sdc(
                    bounds[0].min - stp_solver.o,
                    bounds[0].max - stp_solver.o,
                    stp_solver.source,
                    fs,
                ),
                sdc(
                    bounds[1].min - stp_solver.o,
                    bounds[1].max - stp_solver.o,
                    stp_solver.source,
                    fe,
                ),
            ]

        if type_ is Type.Duration:
            assert bounds[0] is not None
            return [sdc(bounds[0].min, bounds[0].max, fs, fe)]

        if type_ is Type.Release:
            assert bounds[0] is not None
            stp_solver = cast("APSPSolver", from_.internal_constraint_solvers[0])
            b = bounds[0]
            max_ = stp_solver.h if b.max == INF else b.max
            return [sdc(b.min - stp_solver.o, max_ - stp_solver.o, stp_solver.source, fs)]

        if type_ is Type.Deadline:
            assert bounds[0] is not None
            stp_solver = cast("APSPSolver", from_.internal_constraint_solvers[0])
            b = bounds[0]
            max_ = stp_solver.h if b.max == INF else b.max
            return [sdc(b.min - stp_solver.o, max_ - stp_solver.o, stp_solver.source, fe)]

        if type_ is Type.Forever:
            stp_solver = cast("APSPSolver", from_.internal_constraint_solvers[0])
            return [sdc(0, 0, fe, stp_solver.sink)]

        if type_ is Type.BeforeOrMeets:
            assert bounds[0] is not None
            return [sdc(bounds[0].min, bounds[0].max, fe, ts)]

        if type_ is Type.MetByOrAfter:
            assert bounds[0] is not None
            return [sdc(bounds[0].min, bounds[0].max, te, fs)]

        if type_ is Type.MetByOrOverlappedBy:
            assert bounds[0] is not None
            return [
                sdc(1, INF, ts, fs),
                sdc(bounds[0].min, bounds[0].max, fs, te),
                sdc(1, INF, te, fe),
            ]

        if type_ is Type.MetByOrOverlappedByOrAfter:
            return [sdc(1, INF, ts, fs), sdc(1, INF, te, fe)]

        if type_ is Type.MetByOrOverlappedByOrIsFinishedByOrDuring:
            return [sdc(1, INF, ts, fs), sdc(0, INF, fs, te)]

        if type_ is Type.MeetsOrOverlapsOrBefore:
            # Note the Java source swaps its local names here relative to the
            # fs/ts/fe/te convention used elsewhere in this method; this is a
            # literal translation of that same (from.start,to.start,...) wiring.
            return [
                sdc(1, INF, to.start, from_.start),
                sdc(1, INF, to.end, from_.end),
            ]

        if type_ is Type.DuringOrEquals:
            assert bounds[0] is not None and bounds[1] is not None
            return [
                sdc(bounds[0].min, bounds[0].max, ts, fs),
                sdc(bounds[1].min, bounds[1].max, fe, te),
            ]

        if type_ is Type.DuringOrEqualsOrStartsOrFinishes:
            assert bounds[0] is not None and bounds[1] is not None
            return [
                sdc(bounds[0].min, bounds[0].max, ts, fs),
                sdc(bounds[1].min, bounds[1].max, fe, te),
            ]

        if type_ is Type.MeetsOrOverlapsOrFinishedByOrContains:
            assert bounds[0] is not None
            return [sdc(1, INF, fs, ts), sdc(bounds[0].min, bounds[0].max, ts, fe)]

        if type_ is Type.ContainsOrStartedByOrOverlappedByOrMetBy:
            assert bounds[0] is not None
            return [sdc(1, INF, te, fe), sdc(bounds[0].min, bounds[0].max, fs, te)]

        if type_ is Type.StartStart:
            assert bounds[0] is not None
            return [sdc(bounds[0].min, bounds[0].max, fs, ts)]

        if type_ is Type.StartsOrStartedBy:
            assert bounds[0] is not None
            return [sdc(bounds[0].min, bounds[0].max, fs, ts)]

        if type_ is Type.EndEnd:
            assert bounds[0] is not None
            return [sdc(bounds[0].min, bounds[0].max, fe, te)]

        if type_ is Type.EndsOrEndedBy:
            assert bounds[0] is not None
            return [sdc(bounds[0].min, bounds[0].max, fe, te)]

        if type_ is Type.NotBeforeAndNotAfter:
            return [sdc(0, INF, fs, te), sdc(0, INF, ts, fe)]

        return None

    @property
    def edge_label(self) -> str:
        ret = "[" + ", ".join(t.name for t in self.types) + "]"
        if len(self.types) == 1:
            for b in self.bounds:
                if b is not None:
                    ret += f" {b}"
        ret += f" AR {self.auto_removable} "
        ret += f" ID {self.id} "
        return ret

    def clone(self) -> AllenIntervalConstraint:
        if len(self.types) > 1:
            r = AllenIntervalConstraint(*self.types)
        else:
            r = AllenIntervalConstraint(self.types[0], *self.bounds)
        r.auto_removable = self.auto_removable
        return r

    def is_equivalent(self, c: Constraint) -> bool:
        ac = cast(AllenIntervalConstraint, c)
        if len(self.types) > 1:
            return all(t in ac.types for t in self.types)
        return ac.types[0] == self.types[0] and ac.from_ == self.from_ and ac.to == self.to

    @staticmethod
    def get_relation(i1: AllenInterval, i2: AllenInterval) -> AllenIntervalConstraint.Type:
        """The qualitative relation between two AllenIntervals, under the
        earliest-time assumption."""
        Type = AllenIntervalConstraint.Type
        if i1.eet == i2.est:
            return Type.Meets
        if i2.eet == i1.est:
            return Type.MetBy
        if i1.est == i2.est and i1.eet == i2.eet:
            return Type.Equals
        if i1.eet < i2.est:
            return Type.Before
        if i2.eet < i1.est:
            return Type.After
        if i1.est < i2.est and i1.eet > i2.est and i1.eet < i2.eet:
            return Type.Overlaps
        if i2.est < i1.est and i2.eet > i1.est and i2.eet < i1.eet:
            return Type.OverlappedBy
        if i1.est == i2.est and i1.eet < i2.eet:
            return Type.Starts
        if i1.est == i2.est and i1.eet > i2.eet:
            return Type.StartedBy
        if i2.est < i1.est and i2.eet > i1.eet:
            return Type.During
        if i1.est < i2.est and i1.eet > i2.eet:
            return Type.Contains
        if i1.est > i2.est and i1.eet == i2.eet:
            return Type.Finishes
        return Type.FinishedBy


def _quantitative_translation_of_allen(a_type: AllenIntervalConstraint.Type) -> list[Bounds]:
    """The translation of a qualitative Allen relation to quantitative bounds
    over [fs-ts, fs-te, fe-ts, fe-te]."""
    Type = AllenIntervalConstraint.Type
    table: dict[AllenIntervalConstraint.Type, list[Bounds]] = {
        Type.OverlappedBy: [Bounds(-INF, 0), Bounds(0, INF), Bounds(-INF, 0), Bounds(-INF, 0)],
        Type.Meets: [Bounds(0, INF), Bounds(0, INF), Bounds(0, 0), Bounds(0, INF)],
        Type.MetBy: [Bounds(-INF, 0), Bounds(0, 0), Bounds(-INF, 0), Bounds(-INF, 0)],
        Type.Starts: [Bounds(0, 0), Bounds(0, INF), Bounds(-INF, 0), Bounds(0, INF)],
        Type.StartedBy: [Bounds(0, 0), Bounds(0, INF), Bounds(-INF, 0), Bounds(-INF, 0)],
        Type.Finishes: [Bounds(-INF, 0), Bounds(0, INF), Bounds(-INF, 0), Bounds(0, 0)],
        Type.Equals: [Bounds(0, 0), Bounds(0, INF), Bounds(-INF, 0), Bounds(0, 0)],
        Type.Before: [Bounds(0, INF), Bounds(0, INF), Bounds(0, INF), Bounds(0, INF)],
        Type.After: [Bounds(-INF, 0), Bounds(-INF, 0), Bounds(-INF, 0), Bounds(-INF, 0)],
        Type.During: [Bounds(-INF, 0), Bounds(0, INF), Bounds(-INF, 0), Bounds(0, INF)],
        Type.Contains: [Bounds(0, INF), Bounds(0, INF), Bounds(-INF, 0), Bounds(-INF, 0)],
        Type.Overlaps: [Bounds(0, INF), Bounds(0, INF), Bounds(-INF, 0), Bounds(0, INF)],
        Type.FinishedBy: [Bounds(0, INF), Bounds(0, INF), Bounds(-INF, 0), Bounds(0, 0)],
    }
    return table[a_type]
