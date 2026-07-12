# Skipped examples (M22)

Every `examples/**/*.java` in the pinned `meta-csp-framework` commit not listed here has been
ported to `examples/*.py`. These could not be meaningfully ported; each entry is one Java source
file and a one-line reason.

- `examples/CopyOfTestGeometricConstraintSolver2.java`,
  `examples/meta/CopyOfTestTrajectoryEnvelopeAnimator.java` — editor copies (`CopyOf*`), already
  excluded by PLAN.md's own Skip list.
- `examples/multi/MeltYourCPUTestCaseActivityNetworkSolver.java` — an intentionally infinite
  `while (true)` soak/stress test (random variable/constraint churn) with no natural
  termination; not meaningful as a bounded runnable demo.
- `examples/multi/TestTimelinePlottingBig.java` — same category as the above: an intentionally
  infinite `while (true)` loop stress-testing timeline-plotting performance under
  ever-growing activity counts.
- `examples/meta/TestHybridPlanningWithSensingAndDispatching.java` — imports
  `org.metacsp.multi.spatial.rectangleAlgebraNew.toRemove.OntologicalSpatialProperty`, which
  PLAN.md's own Skip list excludes as dead code marked for removal upstream; cannot be ported
  without resurrecting code this plan deliberately does not port.
- `examples/meta/TestLogBrowsing.java` — calls `MetaCSPLogging.showLogs(...)`, backed by
  `utility/logging/LogBrowser.java` (Swing), which PLAN.md's own Skip list excludes.
- `examples/meta/TestTrajectoryEnvelopeDebug3.java` — reads every `*.path` file under
  `paths/debugPaths/npe/`, a directory that does not exist anywhere in the pinned commit of the
  Java oracle repo (confirmed absent from both `/paths/debugPaths/` and the separate
  meta-csp-tutorial repo) -- a debug scratch fixture that was apparently never checked in, so
  even the Java original cannot run.
- `examples/meta/TestTrajectoryEnvelopeFileChooser.java` — its entire body is
  `new TrajectoryEnvelopeAnimator("Untitled")`, i.e. opening an empty Swing file-picker dialog;
  no non-UI logic to port.
- `examples/meta/TestTrajectoryEnvelopeLoadingFromFile.java` — its only fixture,
  `savedConstraintNetworks/example.cn`, is Java-native `ObjectOutputStream` serialization, not
  the `pickle` format C10 uses, so it cannot be loaded by the Python port. The save+load round
  trip itself is already demonstrated by `test_trajectory_envelope_saving_to_file.py` and
  `test_trajectory_envelope_serialization.py`, both of which save their own pickle files first.

## Notable fix made while porting

`TestTrajectoryEnvelopeDebug.java`, `TestTrajectoryEnvelopeDebug2.java`,
`TestTrajectoryEnvelopeSavingToFile.java`, and `TestTrajectoryEnvelopeSerialization.java` all
call `setFootprint(backLeft, backRight, frontLeft, frontRight)` in the Java original. Passed
straight through to a polygon ring in that order, that traces a self-intersecting "bowtie" (the
diagonals backRight-frontLeft and frontRight-backLeft cross) -- invalid input to the union
operation `TrajectoryEnvelope.trajectory`'s setter performs when sweeping the footprint along a
path. Older JTS apparently tolerated the invalid ring; GEOS (via shapely, see D4) raises
`TopologyException: side location conflict` on it. Their Python ports pass
`(back_left, back_right, front_right, front_left)` instead -- a valid simple polygon with the
same four corners, tracing the rectangle's boundary consistently rather than crossing it.

## Bug found and fixed while porting (not an example)

Pickling a `ConstraintNetwork` built on a `MultiVariable` hierarchy (e.g. any
`ActivityNetworkSolver` network) used to raise `AttributeError: '...' object has no attribute
'id'` on load -- `Variable.__hash__` reads `self.id`, and pickle's default reconstruction
(`cls.__new__(cls)` then populate `__dict__`) leaves `id` unset while resolving the reference
cycle every `MultiVariable`'s internal solver forms with its own constraint network (whose graph
stores that same variable as a dict key). Fixed in `framework/variable.py` with a custom
`Variable.__reduce__` that passes `id` as a constructor argument, set immediately on
reconstruction before any such cycle is unpickled. Regression test:
`tests/test_framework.py::TestConstraintNetwork::test_save_load_round_trips_cyclic_multi_variable_network`.
Also added `SimplePlannerInferenceCallback.__call__` (delegating to the existing
`do_inference`), matching that class's own docstring claim of being directly usable as an
`InferenceCallback` -- needed by `test_context_inference.py`,
`test_proactive_planning.py`, and `test_proactive_planning_and_dispatching.py`.
