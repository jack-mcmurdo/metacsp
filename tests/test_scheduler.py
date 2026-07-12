"""Port of tests/TestReusableResourceScheduler.java (every JUnit assertion)."""

from __future__ import annotations

from typing import Sequence

from metacsp.framework.value_ordering_h import ValueOrderingH
from metacsp.framework.variable_ordering_h import VariableOrderingH
from metacsp.meta.symbols_and_time import ReusableResource, Scheduler
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


def _var_oh() -> VariableOrderingH:
    return _MostActivitiesVarOH()


def _val_oh() -> ValueOrderingH:
    return _NoOpValOH()


class TestReusableResourceScheduler:
    def test_scheduling_conflict_resolution(self) -> None:
        meta_solver = Scheduler(0, 600, 0)
        ground_solver = meta_solver.constraint_solvers[0]
        assert isinstance(ground_solver, ActivityNetworkSolver)

        one = ground_solver.create_variable("comp1")
        one.set_symbolic_domain("2")
        two = ground_solver.create_variable("comp1")
        two.set_symbolic_domain("1")
        three = ground_solver.create_variable("comp1")
        three.set_symbolic_domain("3")

        dur1 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
        dur1.from_ = one
        dur1.to = one
        dur2 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
        dur2.from_ = two
        dur2.to = two
        dur3 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
        dur3.from_ = three
        dur3.to = three

        con1 = AllenIntervalConstraint(Type.Before, *Type.Before.get_default_bounds())
        con1.from_ = one
        con1.to = two

        assert ground_solver.add_constraints(dur1, dur2, dur3, con1)

        rr1 = ReusableResource(_var_oh(), _val_oh(), 4)
        rr2 = ReusableResource(_var_oh(), _val_oh(), 3)
        rr1.set_usage(one, two, three)
        rr2.set_usage(two, three)
        meta_solver.add_meta_constraint(rr1)
        meta_solver.add_meta_constraint(rr2)

        assert one.temporal_variable.est == three.temporal_variable.est
        assert meta_solver.backtrack()
        assert one.temporal_variable.est != three.temporal_variable.est

    def test_basic_state_variable_scheduling(self) -> None:
        """Bug: when two activities meet they create a peak and scheduling fails."""
        meta_solver = Scheduler(0, 600, 0)
        ground_solver = meta_solver.constraint_solvers[0]
        assert isinstance(ground_solver, ActivityNetworkSolver)

        one = ground_solver.create_variable("comp1")
        one.set_symbolic_domain("1")
        two = ground_solver.create_variable("comp1")
        two.set_symbolic_domain("1")
        three = ground_solver.create_variable("comp1")
        three.set_symbolic_domain("1")
        four = ground_solver.create_variable("comp1")
        four.set_symbolic_domain("1")

        con1 = AllenIntervalConstraint(Type.Meets)
        con1.from_ = one
        con1.to = two
        con2 = AllenIntervalConstraint(Type.Meets)
        con2.from_ = two
        con2.to = three
        con3 = AllenIntervalConstraint(Type.Meets)
        con3.from_ = three
        con3.to = four

        assert ground_solver.add_constraints(con1, con2, con3)

        rr1 = ReusableResource(_var_oh(), _val_oh(), 1)
        rr1.set_usage(one, two, three, four)
        meta_solver.add_meta_constraint(rr1)

        assert meta_solver.backtrack()

    def test_meets_causes_over_usage(self) -> None:
        """Bug: when two activities meet they create a peak and scheduling fails."""
        meta_solver = Scheduler(0, 600, 0)
        ground_solver = meta_solver.constraint_solvers[0]
        assert isinstance(ground_solver, ActivityNetworkSolver)

        one = ground_solver.create_variable("comp1")
        one.set_symbolic_domain("1")
        two = ground_solver.create_variable("comp1")
        two.set_symbolic_domain("1")

        dur1 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
        dur1.from_ = one
        dur1.to = one
        dur2 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
        dur2.from_ = two
        dur2.to = two

        con1 = AllenIntervalConstraint(Type.Meets)
        con1.from_ = one
        con1.to = two

        assert ground_solver.add_constraints(dur1, dur2, con1)

        rr1 = ReusableResource(_var_oh(), _val_oh(), 1)
        rr1.set_usage(one, two)
        meta_solver.add_meta_constraint(rr1)

        assert meta_solver.backtrack()

    def test_resources_orig(self) -> None:
        meta_solver = Scheduler(0, 600, 0)
        ground_solver = meta_solver.constraint_solvers[0]
        assert isinstance(ground_solver, ActivityNetworkSolver)

        one = ground_solver.create_variable("comp1")
        one.set_symbolic_domain("2")
        two = ground_solver.create_variable("comp1")
        two.set_symbolic_domain("1")
        three = ground_solver.create_variable("comp1")
        three.set_symbolic_domain("3")

        dur1 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
        dur1.from_ = one
        dur1.to = one
        dur2 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
        dur2.from_ = two
        dur2.to = two
        dur3 = AllenIntervalConstraint(Type.Duration, Bounds(35, 55))
        dur3.from_ = three
        dur3.to = three

        con1 = AllenIntervalConstraint(Type.Before, *Type.Before.get_default_bounds())
        con1.from_ = one
        con1.to = two

        assert ground_solver.add_constraints(dur1, dur2, dur3, con1)

        rr1 = ReusableResource(_var_oh(), _val_oh(), 4)
        rr2 = ReusableResource(_var_oh(), _val_oh(), 3)
        rr1.set_usage(one, two, three)
        rr2.set_usage(two, three)
        meta_solver.add_meta_constraint(rr1)
        meta_solver.add_meta_constraint(rr2)

        assert meta_solver.backtrack()

    def test_peak_collection_sampling_bug(self) -> None:
        """Sampling peak collection misses this conflict. The problem
        disappears when removing Activities a1 and a3 (see the next test)."""
        meta_solver = Scheduler(0, 5000, 0)
        ground_solver = meta_solver.constraint_solvers[0]
        assert isinstance(ground_solver, ActivityNetworkSolver)

        a1 = ground_solver.create_variable("comp1")
        a1.set_symbolic_domain("1")
        a2 = ground_solver.create_variable("comp1")
        a2.set_symbolic_domain("1")
        a3 = ground_solver.create_variable("comp1")
        a3.set_symbolic_domain("1")
        a4 = ground_solver.create_variable("comp1")
        a4.set_symbolic_domain("1")
        a5 = ground_solver.create_variable("comp1")
        a5.set_symbolic_domain("1")

        rel1 = AllenIntervalConstraint(Type.Release, Bounds(39, 4799))
        dead1 = AllenIntervalConstraint(Type.Deadline, Bounds(97, 4857))
        rel1.from_ = a1
        rel1.to = a1
        dead1.from_ = a1
        dead1.to = a1

        rel2 = AllenIntervalConstraint(Type.Release, Bounds(39, 4799))
        dead2 = AllenIntervalConstraint(Type.Deadline, Bounds(5000, 5000))
        rel2.from_ = a2
        rel2.to = a2
        dead2.from_ = a2
        dead2.to = a2

        rel3 = AllenIntervalConstraint(Type.Release, Bounds(137, 4897))
        dead3 = AllenIntervalConstraint(Type.Deadline, Bounds(191, 4951))
        rel3.from_ = a3
        rel3.to = a3
        dead3.from_ = a3
        dead3.to = a3

        rel4 = AllenIntervalConstraint(Type.Release, Bounds(192, 4952))
        dead4 = AllenIntervalConstraint(Type.Deadline, Bounds(5000, 5000))
        rel4.from_ = a4
        rel4.to = a4
        dead4.from_ = a4
        dead4.to = a4

        rel5 = AllenIntervalConstraint(Type.Release, Bounds(239, 4999))
        dead5 = AllenIntervalConstraint(Type.Deadline, Bounds(5000, 5000))
        rel5.from_ = a5
        rel5.to = a5
        dead5.from_ = a5
        dead5.to = a5

        assert ground_solver.add_constraints(
            rel1, rel2, rel3, rel4, rel5, dead1, dead2, dead3, dead4, dead5
        )

        rr1 = ReusableResource(_var_oh(), _val_oh(), 2)
        rr1.peak_collection_strategy = rr1.PEAKCOLLECTION.SAMPLING
        rr1.set_usage(a1, a2, a3, a4, a5)
        meta_solver.add_meta_constraint(rr1)

        assert not meta_solver.backtrack()

    def test_peak_collection_sampling_bug_disappears(self) -> None:
        """Same as the previous test with two Activities removed; now the
        conflict is found and backtrack() returns False."""
        meta_solver = Scheduler(0, 5000, 0)
        ground_solver = meta_solver.constraint_solvers[0]
        assert isinstance(ground_solver, ActivityNetworkSolver)

        a2 = ground_solver.create_variable("comp1")
        a2.set_symbolic_domain("1")
        a4 = ground_solver.create_variable("comp1")
        a4.set_symbolic_domain("1")
        a5 = ground_solver.create_variable("comp1")
        a5.set_symbolic_domain("1")

        rel2 = AllenIntervalConstraint(Type.Release, Bounds(39, 4799))
        dead2 = AllenIntervalConstraint(Type.Deadline, Bounds(5000, 5000))
        rel2.from_ = a2
        rel2.to = a2
        dead2.from_ = a2
        dead2.to = a2

        rel4 = AllenIntervalConstraint(Type.Release, Bounds(192, 4952))
        dead4 = AllenIntervalConstraint(Type.Deadline, Bounds(5000, 5000))
        rel4.from_ = a4
        rel4.to = a4
        dead4.from_ = a4
        dead4.to = a4

        rel5 = AllenIntervalConstraint(Type.Release, Bounds(239, 4999))
        dead5 = AllenIntervalConstraint(Type.Deadline, Bounds(5000, 5000))
        rel5.from_ = a5
        rel5.to = a5
        dead5.from_ = a5
        dead5.to = a5

        assert ground_solver.add_constraints(rel2, rel4, rel5, dead2, dead4, dead5)

        rr1 = ReusableResource(_var_oh(), _val_oh(), 2)
        rr1.peak_collection_strategy = rr1.PEAKCOLLECTION.SAMPLING
        rr1.set_usage(a2, a4, a5)
        meta_solver.add_meta_constraint(rr1)

        assert not meta_solver.backtrack()

    def test_three_usages_of_binary_resource_fail(self) -> None:
        meta_solver = Scheduler(0, 5000, 0)
        ground_solver = meta_solver.constraint_solvers[0]
        assert isinstance(ground_solver, ActivityNetworkSolver)

        a1 = ground_solver.create_variable("comp1")
        a1.set_symbolic_domain("1")
        a2 = ground_solver.create_variable("comp1")
        a2.set_symbolic_domain("1")
        a3 = ground_solver.create_variable("comp1")
        a3.set_symbolic_domain("1")

        rel1 = AllenIntervalConstraint(Type.Release, Bounds(4994, 4997))
        dead1 = AllenIntervalConstraint(Type.Deadline, Bounds(4996, 4999))
        rel1.from_ = a1
        rel1.to = a1
        dead1.from_ = a1
        dead1.to = a1

        rel2 = AllenIntervalConstraint(Type.Release, Bounds(4994, 4997))
        dead2 = AllenIntervalConstraint(Type.Deadline, Bounds(4996, 4999))
        rel2.from_ = a2
        rel2.to = a2
        dead2.from_ = a2
        dead2.to = a2

        rel3 = AllenIntervalConstraint(Type.Release, Bounds(4994, 4997))
        dead3 = AllenIntervalConstraint(Type.Deadline, Bounds(4996, 4999))
        rel3.from_ = a3
        rel3.to = a3
        dead3.from_ = a3
        dead3.to = a3

        assert ground_solver.add_constraints(rel1, rel2, rel3, dead1, dead2, dead3)

        rr1 = ReusableResource(_var_oh(), _val_oh(), 2)
        rr1.peak_collection_strategy = rr1.PEAKCOLLECTION.SAMPLING
        rr1.set_usage(a1, a2, a3)
        meta_solver.add_meta_constraint(rr1)

        assert meta_solver.backtrack()
