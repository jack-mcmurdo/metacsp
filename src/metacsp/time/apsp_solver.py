"""Port of time/APSPSolver.java.

Simple Temporal Problem solver using the Floyd-Warshall all-pairs
shortest-path algorithm for constraint propagation (D3): the distance matrix
is a single ``numpy.int64`` array, and the two hot propagation loops
(``_from_scratch_distance_matrix_computation``, the "cube" recomputation, and
``_incremental_distance_matrix_computation``, the "quad" single-edge update)
are vectorized over the "used" timepoints with ``numpy`` broadcasts, one pivot
per Python loop iteration.

Dead code not ported: Java's ``backupDMatrixSimple``/``doFromScratchInsteadOfIncremental``
flags default to ``false`` and have no setters anywhere in the class or its
callers, so the byte-serialization D-matrix backup path (``saveDMatrix``,
``restoreDMatrix``, ``saveDMatrixInternal``, ``restoreDMatrixInternal``,
``canRestoreDMatrix``, ``resetDMatrixBackups``, ``cCreateFromScratch``) is
unreachable in the original and is not ported here. Unlike Java,
``_incremental_distance_matrix_computation`` here never mutates the distance
matrix on failure (Java's leaves partial tentative updates in place when the
enclosing ``cCreate`` call is for a *single* constraint, since the dead
backup path was meant to undo them) -- this is a correctness improvement, not
a behavior change visible to callers: a failed add always leaves bounds/
consistency exactly as before the attempt.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, cast

import numpy as np

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.domain import Domain
from metacsp.framework.value_choice_function import ValueChoiceFunction
from metacsp.exceptions import ConstraintNotFound, MalformedSimpleDistanceConstraint
from metacsp.time.bounds import INF, Bounds, print_long
from metacsp.time.interval import Interval
from metacsp.time.simple_distance_constraint import SimpleDistanceConstraint
from metacsp.time.time_point import TimePoint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["APSPSolver"]


def _sum(a: int, b: int) -> int:
    if a == INF or b == INF:
        return INF
    if a == -INF or b == -INF:
        return -INF
    return a + b


def _clamp(arr: np.ndarray) -> np.ndarray:
    return np.clip(arr, -INF, INF)


class _StartValueChoiceFunction(ValueChoiceFunction):
    def get_value(self, dom: Domain) -> Any:
        return cast(Interval, dom).bounds.min


class _EndValueChoiceFunction(ValueChoiceFunction):
    def get_value(self, dom: Domain) -> Any:
        return cast(Interval, dom).bounds.max


class APSPSolver(ConstraintSolver):
    """Simple Temporal Problem solver using the Floyd-Warshall all-pairs
    shortest-path algorithm for constraint propagation."""

    INF = INF
    DEFAULT_MAX_TPS = 2000

    print_long = staticmethod(print_long)

    def __init__(self, origin: int, horizon: int, max_tps: int = DEFAULT_MAX_TPS) -> None:
        super().__init__([SimpleDistanceConstraint], TimePoint)
        self.set_options(ConstraintSolver.Options.MANUAL_PROPAGATE)

        self._adding_independent_constraints = False
        self._max_tps = max_tps + 2  # +2 to account for O and H
        self._max_used = 2
        self._distance = np.zeros((self._max_tps, self._max_tps), dtype=np.int64)
        self._distance_rollback: list[np.ndarray] = []
        self._tpoints_rollback: list[list[TimePoint]] = []
        self._max_used_rollback: list[int] = []

        self._h = horizon
        self._o = origin
        self._tp_counter = 0

        n = self._max_tps
        self._distance[0, 1:] = self._h
        if n > 1:
            self._distance[1, 0] = -self._h
        for i in range(2, n):
            self._distance[i, 1:] = self._h
            self._distance[i, i] = 0

        self._tpoints: list[TimePoint] = [None] * self._max_tps  # type: ignore[list-item]
        self._tpoints[0] = TimePoint(self._tp_counter, self._max_tps, self, self._o, self._h)
        self._tp_counter += 1
        self._tpoints[1] = TimePoint(self._tp_counter, self._max_tps, self, self._o, self._h)
        self._tp_counter += 1

        self.the_network.add_variable(self._tpoints[0])
        self.the_network.add_variable(self._tpoints[1])

        con = SimpleDistanceConstraint()
        self._horizon_constraint = con
        con.from_ = self.get_variable(0)
        con.to = self.get_variable(1)
        con.minimum = self._h - self._o
        con.maximum = self._h - self._o
        con.add_interval(Bounds(self._h - self._o, self._h - self._o))

        self._tpoints[0].used = True
        self._tpoints[0].lower_bound = self._o
        self._tpoints[0].upper_bound = self._o
        self._tpoints[1].used = True
        self._tpoints[1].lower_bound = self._h
        self._tpoints[1].upper_bound = self._h

        self._tpoints[0].set_out(1, con)

        for i in range(2, self._max_tps):
            tp = TimePoint(self._tp_counter, self._max_tps, self)
            self._tpoints[i] = tp
            self._tp_counter += 1

            con_o = SimpleDistanceConstraint()
            con_h = SimpleDistanceConstraint()
            con_o.from_ = self.get_variable(0)
            con_o.to = self.get_variable(i)
            con_h.from_ = self.get_variable(i)
            con_h.to = self.get_variable(1)

            con_o.minimum = 0
            con_o.maximum = self._h - self._o
            con_h.minimum = 0
            con_h.maximum = self._h - self._o

            con_o.add_interval(Bounds(0, self._h - self._o))
            con_h.add_interval(Bounds(0, self._h - self._o))

            self._tpoints[i].lower_bound = self._o
            self._tpoints[i].upper_bound = self._h

            self._tpoints[0].set_out(i, con_o)
            self._tpoints[i].set_out(1, con_h)

    # --- timepoint (de)allocation ---

    def _tp_create(self) -> int:
        i = 2
        found = False
        while i < self._max_tps and not found:
            if not self._tpoints[i].used:
                self._tpoints[i].used = True
                found = True
                if i == self._max_used + 1:
                    self._max_used = i
            else:
                i += 1
        for l in range(2, self._max_used + 1):
            self._distance[i, l] = self._h
            self._distance[l, i] = self._h
        self._distance[i, i] = 0
        self._distance[i, 0] = 0
        self._distance[i, 1] = self._h
        self._distance[0, i] = self._h
        self._distance[1, i] = 0
        return i

    def _tp_create_batch(self, n: int) -> list[int] | None:
        if n > self._max_tps:
            return None
        return [self._tp_create() for _ in range(n)]

    def _tp_delete(self, id_time_point: list[int]) -> None:
        for i in id_time_point:
            self._tpoints[i].used = False
            if i == self._max_used:
                self._max_used -= 1

            con_o = SimpleDistanceConstraint()
            con_h = SimpleDistanceConstraint()
            con_o.from_ = self.get_variable(0)
            con_o.to = self.get_variable(i)
            con_h.from_ = self.get_variable(i)
            con_h.to = self.get_variable(1)

            con_o.minimum = 0
            con_o.maximum = self._h - self._o
            con_h.minimum = 0
            con_h.maximum = self._h - self._o

            con_o.add_interval(Bounds(0, self._h - self._o))
            con_h.add_interval(Bounds(0, self._h - self._o))

            self._tpoints[i].lower_bound = self._o
            self._tpoints[i].upper_bound = self._h
            self._tpoints[0].set_out(i, con_o)
            self._tpoints[i].set_out(1, con_h)

        self._from_scratch_distance_matrix_computation()

    def _refresh_bounds(self) -> None:
        for j in range(self._max_used + 1):
            tp = self._tpoints[j]
            if tp.used:
                tp.lower_bound = _sum(int(-self._distance[j, 0]), self._o)
                tp.upper_bound = _sum(int(self._distance[0, j]), self._o)

    # --- constraint (de)creation ---

    def _c_create(self, i: Bounds, from_: int, to: int, no_propagation: bool) -> bool:
        max_ = i.max
        min_ = i.min
        if i.max == INF:
            max_ = self._h - self._o
        if i.min == -INF:
            min_ = -(self._h - self._o)
        i = Bounds(min_, max_)

        if i.min > i.max:
            return False
        if from_ == to:
            return False
        if self._tpoints[from_] is None:
            return False

        if no_propagation:
            self._distance[from_, to] = max_
            self._distance[to, from_] = -min_

        con = self._tpoints[from_].get_out(to)
        if con is not None:
            if con.minimum > i.max or con.maximum < i.min:
                return False
            if con.minimum > i.min and con.maximum < i.max:
                return con.add_interval(i)

            old_d, old_dd = con.minimum, con.maximum
            if con.minimum < i.min:
                con.minimum = i.min
            if con.maximum > i.max:
                con.maximum = i.max

            if not no_propagation and not self._incremental_distance_matrix_computation(
                from_, to, i
            ):
                con.minimum, con.maximum = old_d, old_dd
                return False
            if not con.add_interval(i):
                return False
            self._refresh_bounds()
        else:
            if not no_propagation and not self._incremental_distance_matrix_computation(
                from_, to, i
            ):
                return False
            con = SimpleDistanceConstraint()
            con.from_ = self.get_variable(from_)
            con.to = self.get_variable(to)
            con.minimum = i.min
            con.maximum = i.max
            con.add_interval(Bounds(i.min, i.max))
            self._tpoints[from_].set_out(to, con)
            self._refresh_bounds()
        return True

    def _c_create_batch(self, in_: list[Bounds], from_: list[int], to: list[int]) -> bool:
        old_d = [0] * len(in_)
        old_dd = [0] * len(in_)
        added = [False] * len(in_)
        rollback = False
        rollback_point = -1

        for idx in range(len(in_)):
            min_ = in_[idx].min
            max_ = in_[idx].max
            if in_[idx].max == INF:
                max_ = self._h - self._o
            if in_[idx].min == -INF:
                min_ = -(self._h - self._o)
            in_[idx] = Bounds(min_, max_)

            if in_[idx].min > in_[idx].max or from_[idx] == to[idx]:
                rollback = True
                rollback_point = idx
                break

            con = self._tpoints[from_[idx]].get_out(to[idx])
            if con is not None:
                if con.minimum > in_[idx].max or con.maximum < in_[idx].min:
                    rollback = True
                    rollback_point = idx
                    break
                old_d[idx] = con.minimum
                old_dd[idx] = con.maximum
                if con.minimum < in_[idx].min:
                    con.minimum = in_[idx].min
                if con.maximum > in_[idx].max:
                    con.maximum = in_[idx].max
            else:
                added[idx] = True
                con = SimpleDistanceConstraint()
                con.from_ = self.get_variable(from_[idx])
                con.to = self.get_variable(to[idx])
                con.minimum = in_[idx].min
                con.maximum = in_[idx].max
                con.add_interval(Bounds(in_[idx].min, in_[idx].max))
                self._tpoints[from_[idx]].set_out(to[idx], con)

        if rollback:
            for idx in range(rollback_point - 1, -1, -1):
                con = self._tpoints[from_[idx]].get_out(to[idx])
                assert con is not None
                if not added[idx]:
                    con.minimum, con.maximum = old_d[idx], old_dd[idx]
                else:
                    con.remove_interval(in_[idx])
                    self._tpoints[from_[idx]].set_out(to[idx], None)
            return False

        if not self._from_scratch_distance_matrix_computation():
            return False

        for idx in range(len(in_) - 1, -1, -1):
            if not added[idx]:
                con = self._tpoints[from_[idx]].get_out(to[idx])
                assert con is not None
                con.add_interval(in_[idx])

        self._refresh_bounds()
        return True

    def _c_delete(
        self, in_: list[Bounds], from_: list[int], to: list[int], can_restore: bool
    ) -> bool:
        for idx in range(len(in_)):
            min_ = in_[idx].min
            max_ = in_[idx].max
            if in_[idx].max == INF:
                max_ = self._h - self._o
            if in_[idx].min == -INF:
                min_ = -(self._h - self._o)
            in_[idx] = Bounds(min_, max_)

            con = self._tpoints[from_[idx]].get_out(to[idx])
            if con is None:
                raise ConstraintNotFound(f"Interval {in_[idx]}, from {from_[idx]}, to {to[idx]}")
            if con.counter == 1:
                if con.remove_interval(in_[idx]):
                    self._tpoints[from_[idx]].set_out(to[idx], None)
                else:
                    raise MalformedSimpleDistanceConstraint(con, 1)
            elif not con.remove_interval(in_[idx]):
                raise MalformedSimpleDistanceConstraint(con, 2)

        if not can_restore:
            self._from_scratch_distance_matrix_computation()

        self._refresh_bounds()
        return True

    # --- propagation ---

    def _from_scratch_distance_matrix_computation(self) -> bool:
        n = self._max_used + 1
        dist = self._distance
        tp = self._tpoints
        for i in range(n):
            for j in range(i, n):
                if i != j:
                    dij = self._h
                    dji = self._h
                    out_ij = tp[i].get_out(j)
                    if out_ij is not None:
                        dij = min(dij, out_ij.maximum)
                        dji = min(dji, -out_ij.minimum)
                    out_ji = tp[j].get_out(i)
                    if out_ji is not None:
                        dij = min(dij, -out_ji.minimum)
                        dji = min(dji, out_ji.maximum)
                    if -dji > dij:
                        return False
                    dist[i, j] = dij
                    dist[j, i] = dji
                else:
                    dist[i, j] = 0

        used_idx = [k for k in range(n) if tp[k].used]
        if not used_idx:
            return True
        idx = np.array(used_idx)
        sub = dist[np.ix_(idx, idx)]
        for k_pos in range(len(idx)):
            col_k = sub[:, k_pos : k_pos + 1]
            row_k = sub[k_pos : k_pos + 1, :]
            candidate = _clamp(col_k + row_k)
            sub = np.minimum(sub, candidate)
            if np.any(np.diagonal(sub) < 0):
                return False
        dist[np.ix_(idx, idx)] = sub
        return True

    def _incremental_distance_matrix_computation(self, from_: int, to: int, i: Bounds) -> bool:
        dist = self._distance
        if dist[to, from_] != INF and _sum(i.max, int(dist[to, from_])) < 0:
            return False
        if dist[from_, to] != INF and _sum(-i.min, int(dist[from_, to])) < 0:
            return False

        used_idx = [k for k in range(self._max_used + 1) if self._tpoints[k].used]
        idx = np.array(used_idx)
        sub = dist[np.ix_(idx, idx)]
        to_pos = used_idx.index(to)
        from_pos = used_idx.index(from_)

        col_to = sub[:, to_pos]
        row_from = sub[from_pos, :]
        col_from = sub[:, from_pos]
        row_to = sub[to_pos, :]

        path1 = _clamp(col_to[:, None] + (-i.min) + row_from[None, :])
        path2 = _clamp(col_from[:, None] + i.max + row_to[None, :])
        candidate = np.minimum(path1, path2)
        new_sub = np.minimum(sub, candidate)

        if np.any(np.diagonal(new_sub) < 0):
            return False
        dist[np.ix_(idx, idx)] = new_sub
        return True

    # --- framework interface ---

    def create_variables_sub(self, num: int) -> list[Variable] | None:
        tp = self._tp_create_batch(num)
        if tp is None:
            return None
        return [self._tpoints[t] for t in tp]

    def remove_variables_sub(self, v: list[Variable]) -> None:
        ids = [tp.id for tp in v if isinstance(tp, TimePoint)]
        self._tp_delete(ids)

    def set_adding_independent_constraints(self) -> None:
        self._adding_independent_constraints = True

    def add_constraints_sub(self, con: list[Constraint]) -> bool:
        if not con:
            return True
        tot: list[Bounds] = []
        from_: list[int] = []
        to: list[int] = []
        for c in con:
            if isinstance(c, SimpleDistanceConstraint):
                tot.append(Bounds(c.minimum, c.maximum))
                from_.append(c.from_.id)
                to.append(c.to.id)

        if self._adding_independent_constraints:
            self._adding_independent_constraints = False
            for idx in range(len(con)):
                if not self._c_create(tot[idx], from_[idx], to[idx], True):
                    self.logger.info("Critical error in new constraint propagation!")
                    return False
            return True

        if len(con) > self._max_used:
            return self._c_create_batch(tot, from_, to)

        added: list[SimpleDistanceConstraint] = []
        for idx in range(len(con)):
            if self._c_create(tot[idx], from_[idx], to[idx], False):
                added.append(cast(SimpleDistanceConstraint, con[idx]))
            else:
                to_delete_bounds = [Bounds(c.minimum, c.maximum) for c in added]
                to_delete_from = [c.from_.id for c in added]
                to_delete_to = [c.to.id for c in added]
                self._c_delete(to_delete_bounds, to_delete_from, to_delete_to, True)
                return False
        return True

    def remove_constraints_sub(self, con: list[Constraint]) -> None:
        if not con:
            return
        tot: list[Bounds] = []
        from_: list[int] = []
        to: list[int] = []
        for c in con:
            if isinstance(c, SimpleDistanceConstraint):
                tot.append(Bounds(c.minimum, c.maximum))
                from_.append(c.from_.id)
                to.append(c.to.id)
        self._c_delete(tot, from_, to, False)

    def propagate(self) -> bool:
        return self._from_scratch_distance_matrix_computation()

    def register_value_choice_functions(self) -> None:
        Domain.register_value_choice_function(Interval, _StartValueChoiceFunction(), "ET")
        Domain.register_value_choice_function(Interval, _EndValueChoiceFunction(), "LT")

    # --- access methods ---

    @property
    def o(self) -> int:
        return self._o

    @property
    def h(self) -> int:
        return self._h

    def change_horizon(self, val: int) -> bool:
        self.remove_constraint(self._horizon_constraint)
        sdc = SimpleDistanceConstraint()
        sdc.from_ = self.get_variable(0)
        sdc.to = self.get_variable(1)
        sdc.minimum = val
        sdc.maximum = val
        if self.add_constraint(sdc):
            self._h = val
            self._horizon_constraint = sdc
            return True
        return False

    @property
    def source(self) -> TimePoint:
        return self._tpoints[0]

    @property
    def sink(self) -> TimePoint:
        return self._tpoints[1]

    def get_time_point(self, id: int) -> TimePoint | None:
        if id >= self._max_tps:
            return None
        if self._tpoints[id] is None:
            return None
        if not self._tpoints[id].used:
            return None
        return self._tpoints[id]

    def get_constraint(
        self, tp_from: TimePoint, tp_to: TimePoint
    ) -> SimpleDistanceConstraint | None:
        if self._distance[tp_from.id, tp_to.id] != INF:
            return self._tpoints[tp_from.id].get_out(tp_to.id)
        return None

    def get_distance_bounds(self, tp_from: TimePoint, tp_to: TimePoint) -> Bounds:
        max_ = int(self._distance[tp_from.id, tp_to.id])
        min_ = int(-self._distance[tp_to.id, tp_from.id])
        return Bounds(min_, max_)

    @property
    def max_tps(self) -> int:
        """Maximum number of timepoints that can be added to this STP
        network (excluding the Origin (O) and Horizon (H) timepoint)."""
        return self._max_tps - 2

    def draw(self) -> None:
        """Draw a graph of this APSPSolver's ConstraintNetwork.

        The Java implementation depends on the Prefuse/Swing UI (skip list);
        not ported. See D10.
        """
        raise NotImplementedError("the Prefuse/Swing STP viewer is not ported; see D10")

    def get_rms_rigidity(self) -> float:
        """Root mean square rigidity of a consistent STN (the inverse of
        flexibility): 1 if completely rigid, 0 if unconstrained."""
        vars_ = self.get_variables()
        rigidity = [0.0] * len(vars_)
        for idx, v in enumerate(vars_):
            tp = cast(TimePoint, v)
            if tp.used:
                rigidity[idx] = 1.0 / (1 + tp.upper_bound - tp.lower_bound)
        sigma = sum(r * r for r in rigidity)
        n = len(vars_)
        return math.sqrt(sigma * (2.0 / (n * (n + 1))))

    def bookmark(self) -> int:
        tp_snapshot = [tp.clone() for tp in self._tpoints]
        self._distance_rollback.append(self._distance.copy())
        self._tpoints_rollback.append(tp_snapshot)
        self._max_used_rollback.append(self._max_used)
        return len(self._distance_rollback) - 1

    def remove_bookmark(self, i: int) -> None:
        del self._distance_rollback[i]
        del self._tpoints_rollback[i]
        del self._max_used_rollback[i]

    def revert(self, i: int) -> None:
        self._distance = self._distance_rollback[i]
        self._tpoints = self._tpoints_rollback[i]
        self._max_used = self._max_used_rollback[i]
        for j in range(len(self._distance_rollback) - 1, i - 1, -1):
            del self._distance_rollback[j]
            del self._tpoints_rollback[j]
            del self._max_used_rollback[j]

    @property
    def num_bookmarks(self) -> int:
        return len(self._distance_rollback)

    def get_equal_time_point(self, query_tp: TimePoint) -> TimePoint | None:
        for tp in self._tpoints:
            if tp == query_tp:
                return tp
        return None

    def print_dist(self) -> str:
        s = ""
        for i in range(self._max_used + 1):
            for j in range(self._max_used + 1):
                s += print_long(int(self._distance[i, j])) + " "
            s += "\n"
        return s

    def print_dist_hist(self) -> str:
        s = ""
        for ci, dist in enumerate(self._distance_rollback):
            s += "=============================\n"
            s += f"= {ci}\n"
            s += "=============================\n"
            for i in range(self._max_used + 1):
                for j in range(self._max_used + 1):
                    s += print_long(int(dist[i, j])) + " "
                s += "\n"
        return s

    def __str__(self) -> str:
        lines = [f"Temporal Network ({self._max_tps} time points): "]
        for tp in self._tpoints:
            if tp.used:
                lines.append(str(tp))
        return "\n".join(lines) + "\n"
