"""Port of examples/meta/TestStateVariableSchedulerSimple.java.

The Java original interactively re-solves on a Swing button click
(``ConstraintNetwork.draw`` + ``Callback``) and publishes a live timeline
(``TimelinePublisher``/``TimelineVisualizer``, ``metaSolver.draw()``); none
of that Swing/viz machinery is ported yet (see D10, M21) -- this example
just solves once and prints the result.
"""

from __future__ import annotations

from typing import Sequence

from metacsp.framework.value_ordering_h import ValueOrderingH
from metacsp.framework.variable_ordering_h import VariableOrderingH
from metacsp.meta.symbols_and_time import Scheduler, StateVariable
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.apsp_solver import APSPSolver
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
    one.set_symbolic_domain("A", "B")
    two = ground_solver.create_variable("comp1")
    two.set_symbolic_domain("A", "B", "C")
    three = ground_solver.create_variable("comp1")
    three.set_symbolic_domain("D", "E")

    dur1 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
    dur1.from_ = one
    dur1.to = one
    dur2 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
    dur2.from_ = two
    dur2.to = two
    dur3 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
    dur3.from_ = three
    dur3.to = three

    con1 = AllenIntervalConstraint(
        Type.Overlaps, Bounds(1, APSPSolver.INF), Bounds(5, 10), Bounds(1, APSPSolver.INF)
    )
    con1.from_ = one
    con1.to = two

    ground_solver.add_constraints(dur1, dur2, dur3, con1)

    var_oh = _MostActivitiesVarOH()
    val_oh = _NoOpValOH()

    sv = StateVariable(var_oh, val_oh, meta_solver, ["A", "B", "C", "D", "E"])
    sv.set_usage(one, two, three)
    meta_solver.add_meta_constraint(sv)

    print("SOLVED?", meta_solver.backtrack())


if __name__ == "__main__":
    main()
