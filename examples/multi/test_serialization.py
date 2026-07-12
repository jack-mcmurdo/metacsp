"""Port of examples/multi/TestSerialization.java.

Java object serialization (``ObjectOutputStream``/``ObjectInputStream``) is
not ported; per C10, ``ConstraintNetwork.save``/``.load`` use ``pickle``
instead -- same round trip, different wire format. The Java original also
draws each reloaded network (``ConstraintNetwork.draw``, Swing -- not
ported, see D10); dropped here. Output files are written to a temporary
directory rather than the Java original's cwd-relative ``*.out`` files, so
running this example doesn't litter the repo.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.time.bounds import Bounds


def main() -> None:
    solver = ActivityNetworkSolver(0, 100, ["A", "B", "C", "D"])
    act1 = solver.create_variable()
    assert isinstance(act1, SymbolicVariableActivity)
    act1.set_symbolic_domain("A", "B", "C")
    act2 = solver.create_variable()
    assert isinstance(act2, SymbolicVariableActivity)
    act2.set_symbolic_domain("B", "C")

    con1 = SymbolicValueConstraint(SymbolicValueConstraint.Type.EQUALS)
    con1.set_from(act1)
    con1.set_to(act2)

    con2 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Before, Bounds(10, 20))
    con2.from_ = act1
    con2.to = act2

    solver.add_constraints(con1, con2)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        activity_network_path = tmp_path / "ActivityNetwork.pickle"
        solver.constraint_network.save(activity_network_path)
        an = ConstraintNetwork.load(activity_network_path)
        print(an)

        allen_interval_network_path = tmp_path / "AllenIntervalNetwork.pickle"
        solver.constraint_solvers[0].constraint_network.save(allen_interval_network_path)
        ain = ConstraintNetwork.load(allen_interval_network_path)
        print(ain)

        simple_temporal_network_path = tmp_path / "SimpleTemporalNetwork.pickle"
        temporal_solver = solver.constraint_solvers[0]
        assert isinstance(temporal_solver, MultiConstraintSolver)
        temporal_solver.constraint_solvers[0].constraint_network.save(simple_temporal_network_path)
        apspn = ConstraintNetwork.load(simple_temporal_network_path)
        print(apspn)


if __name__ == "__main__":
    main()
