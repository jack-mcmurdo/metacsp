"""Port of examples/meta/TestStateVariableScheduler.java.

The Java original interactively re-solves on a Swing button click
(``ConstraintNetwork.draw`` + ``Callback``) and publishes a live timeline
(``TimelinePublisher``/``TimelineVisualizer``); none of that Swing/viz
machinery is ported yet (see D10, M21) -- this example just solves once and
prints the result.
"""

from __future__ import annotations

from typing import Sequence

from metacsp.framework.value_ordering_h import ValueOrderingH
from metacsp.framework.variable_ordering_h import VariableOrderingH
from metacsp.meta.symbols_and_time import Scheduler, StateVariable
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.bounds import Bounds

Type = AllenIntervalConstraint.Type


class _MostActivitiesVarOH(VariableOrderingH):
    """Most critical conflict is the one with most activities (largest peak)."""

    def compare(self, n1, n2) -> int:
        return len(n2.get_variables()) - len(n1.get_variables())

    def collect_data(self, all_meta_variables: Sequence) -> None:
        pass


class _NoOpValOH(ValueOrderingH):
    def compare(self, n1, n2) -> int:
        return 0


def main() -> None:
    meta_solver = Scheduler(0, 600, 0)
    ground_solver = meta_solver.constraint_solvers[0]
    assert isinstance(ground_solver, ActivityNetworkSolver)

    one = ground_solver.create_variable("comp1")
    one.set_symbolic_domain("F", "G")
    one_a = ground_solver.create_variable("comp1")
    one_a.set_symbolic_domain("A", "B", "C")
    one_b = ground_solver.create_variable("comp1")
    one_b.set_symbolic_domain("D", "E")

    one_aa = ground_solver.create_variable("comp1")
    one_aa.set_symbolic_domain("A", "G")
    one_ab = ground_solver.create_variable("comp1")
    one_ab.set_symbolic_domain("B", "F")
    one_ac = ground_solver.create_variable("comp1")
    one_ac.set_symbolic_domain("C", "E")

    dur1 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
    dur1.from_ = one_a
    dur1.to = one_a
    dur2 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
    dur2.from_ = one_b
    dur2.to = one_b
    dur3 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
    dur3.from_ = one
    dur3.to = one
    dur4 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
    dur4.from_ = one_aa
    dur4.to = one_aa
    dur5 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
    dur5.from_ = one_ab
    dur5.to = one_ab
    dur6 = AllenIntervalConstraint(Type.Duration, Bounds(10, 25))
    dur6.from_ = one_ac
    dur6.to = one_ac

    con1 = AllenIntervalConstraint(Type.Before, *Type.Before.get_default_bounds())
    con1.from_ = one
    con1.to = one_a
    con2 = AllenIntervalConstraint(Type.Before, *Type.Before.get_default_bounds())
    con2.from_ = one
    con2.to = one_b
    con3 = AllenIntervalConstraint(Type.Before, *Type.Before.get_default_bounds())
    con3.from_ = one_a
    con3.to = one_aa
    con4 = AllenIntervalConstraint(Type.Before, *Type.Before.get_default_bounds())
    con4.from_ = one_a
    con4.to = one_ab
    con5 = AllenIntervalConstraint(Type.Before, *Type.Before.get_default_bounds())
    con5.from_ = one_a
    con5.to = one_ac

    ground_solver.add_constraints(dur1, dur2, dur3, dur4, dur5, dur6, con1, con2, con3, con4, con5)

    var_oh = _MostActivitiesVarOH()
    val_oh = _NoOpValOH()

    sv = StateVariable(var_oh, val_oh, meta_solver, ["A", "B", "C", "D", "E", "F", "G"])
    sv.set_usage(one, one_a, one_b, one_aa, one_ab, one_ac)
    meta_solver.add_meta_constraint(sv)

    print("SOLVED?", meta_solver.backtrack())


if __name__ == "__main__":
    main()
